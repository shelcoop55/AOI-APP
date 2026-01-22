"""
Excel Reporting Module.

This module provides functions for generating professional, multi-sheet Excel
reports from the defect analysis data. It uses xlsxwriter to format the report
with headers, themed charts, and conditional formatting for enhanced readability
and analytical value.
"""
import pandas as pd
import io
import plotly.graph_objects as go
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable, Union
import zipfile
import json
import logging
from concurrent.futures import ThreadPoolExecutor

from src.config import (
    PANEL_COLOR, CRITICAL_DEFECT_TYPES, PLOT_AREA_COLOR, BACKGROUND_COLOR, PlotTheme,
    REPORT_HEADER_COLOR, CRITICAL_DEFECT_BG_COLOR, CRITICAL_DEFECT_FONT_COLOR, ExcelReportStyle
)
from src.plotting import (
    create_defect_traces, create_defect_sankey, create_defect_sunburst,
    create_grid_shapes, create_still_alive_figure, create_defect_map_figure,
    create_pareto_figure
)
from src.analysis.calculations import aggregate_stress_data_from_df
from src.enums import Quadrant
from src.models import PanelData

# ==============================================================================
# --- Private Helper Functions for Report Generation ---
# ==============================================================================

def _define_formats(workbook):
    """Defines all the custom formats used in the Excel report."""
    # Use centralized style definition
    return ExcelReportStyle.get_formats(workbook)

def _write_report_header(worksheet, formats, source_filename):
    """Writes the main header section to a worksheet."""
    worksheet.set_row(0, 30)
    worksheet.merge_range('A1:D1', 'Panel Defect Analysis Report', formats['title'])
    worksheet.write('A2', 'Source File:', formats['subtitle'])
    worksheet.write('B2', source_filename)
    worksheet.write('A3', 'Report Date:', formats['subtitle'])
    worksheet.write('B3', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

def _create_summary_sheet(writer, formats, full_df, panel_rows, panel_cols, source_filename, quadrant_selection, verification_selection):
    """Creates the 'Quarterly Summary' sheet with KPIs, parameters, and a chart."""
    workbook = writer.book
    worksheet = workbook.add_worksheet('Quarterly Summary')

    _write_report_header(worksheet, formats, source_filename)

    # --- Analysis Parameters Table ---
    param_data = {
        "Parameter": ["Panel Rows", "Panel Columns", "Quadrant Filter", "Verification Filter"],
        "Value": [panel_rows, panel_cols, quadrant_selection, verification_selection]
    }
    param_df = pd.DataFrame(param_data)

    param_start_row = 5
    worksheet.merge_range(f'A{param_start_row-1}:B{param_start_row-1}', 'Analysis Parameters', formats['subtitle'])
    param_df.to_excel(writer, sheet_name='Quarterly Summary', startrow=param_start_row, header=True, index=False)


    # --- KPI Summary Table ---
    kpi_start_row = param_start_row + len(param_df) + 3
    worksheet.merge_range(f'A{kpi_start_row-1}:C{kpi_start_row-1}', 'KPI Summary', formats['subtitle'])

    kpi_data = []
    quadrants = ['Q1', 'Q2', 'Q3', 'Q4']

    for quad in quadrants:
        quad_df = full_df[full_df['QUADRANT'] == quad]
        total_defects = len(quad_df)
        density = total_defects / (panel_rows * panel_cols) if (panel_rows * panel_cols) > 0 else 0
        kpi_data.append({"Quadrant": quad, "Total Defects": total_defects, "Defect Density": density})

    total_defects_all = len(full_df)
    density_all = total_defects_all / (4 * panel_rows * panel_cols) if (panel_rows * panel_cols) > 0 else 0
    kpi_data.append({"Quadrant": "Total", "Total Defects": total_defects_all, "Defect Density": density_all})

    summary_df = pd.DataFrame(kpi_data)

    summary_df.to_excel(writer, sheet_name='Quarterly Summary', startrow=kpi_start_row, header=False, index=False)

    for col_num, value in enumerate(summary_df.columns.values):
        worksheet.write(kpi_start_row - 1, col_num, value, formats['header'])
        
    for row_num in range(len(summary_df)):
        worksheet.write(row_num + kpi_start_row, 0, summary_df.iloc[row_num, 0], formats['cell'])
        worksheet.write(row_num + kpi_start_row, 1, summary_df.iloc[row_num, 1], formats['cell'])
        worksheet.write(row_num + kpi_start_row, 2, summary_df.iloc[row_num, 2], formats['density'])

    worksheet.autofit()

    chart = workbook.add_chart({'type': 'column'})
    chart.add_series({
        'name': 'Total Defects by Quadrant',
        'categories': ['Quarterly Summary', kpi_start_row, 0, kpi_start_row + len(quadrants) - 1, 0],
        'values': ['Quarterly Summary', kpi_start_row, 1, kpi_start_row + len(quadrants) - 1, 1],
        'fill': {'color': PANEL_COLOR},
        'border': {'color': '#000000'},
        'data_labels': {'value': True}
    })
    chart.set_title({'name': 'Defect Count Comparison by Quadrant'})
    chart.set_legend({'position': 'none'})
    chart.set_y_axis({'name': 'Count'})
    chart.set_style(10)
    worksheet.insert_chart('E2', chart, {'x_scale': 1.5, 'y_scale': 1.5})

def _create_panel_wide_top_defects_sheet(writer, formats, full_df):
    """Creates a sheet summarizing the top defects for the entire panel, with a chart."""
    if full_df.empty:
        return

    sheet_name = 'Panel-Wide Top Defects'

    top_offenders = full_df['DEFECT_TYPE'].value_counts().reset_index()
    top_offenders.columns = ['Defect Type', 'Count']
    top_offenders = top_offenders[top_offenders['Count'] > 0]
    top_offenders['Percentage'] = (top_offenders['Count'] / len(full_df))

    top_offenders.to_excel(writer, sheet_name=sheet_name, startrow=1, header=False, index=False)

    worksheet = writer.sheets[sheet_name]

    for col_num, value in enumerate(top_offenders.columns.values):
        worksheet.write(0, col_num, value, formats['header'])

    worksheet.set_column('A:A', 30)
    worksheet.set_column('B:B', 12)
    worksheet.set_column('C:C', 12, formats['percent'])

    # Add a chart for better visualization
    chart = writer.book.add_chart({'type': 'pie'})
    chart.add_series({
        'name':       'Panel-Wide Defect Distribution',
        'categories': [sheet_name, 1, 0, len(top_offenders), 0],
        'values':     [sheet_name, 1, 1, len(top_offenders), 1],
        'data_labels': {'percentage': True, 'leader_lines': True},
    })
    chart.set_title({'name': 'Panel-Wide Defect Distribution'})
    chart.set_style(10)
    worksheet.insert_chart('E2', chart, {'x_scale': 1.5, 'y_scale': 1.5})


def _create_per_quadrant_top_defects_sheets(writer, formats, full_df):
    """Creates a separate sheet for the top defects of each quadrant."""
    quadrants = ['Q1', 'Q2', 'Q3', 'Q4']
    for quad in quadrants:
        quad_df = full_df[full_df['QUADRANT'] == quad]
        if not quad_df.empty:
            sheet_name = f'{quad} Top Defects'

            top_offenders = quad_df['DEFECT_TYPE'].value_counts().reset_index()
            top_offenders.columns = ['Defect Type', 'Count']
            top_offenders = top_offenders[top_offenders['Count'] > 0]
            top_offenders['Percentage'] = (top_offenders['Count'] / len(quad_df))
            
            top_offenders.to_excel(writer, sheet_name=sheet_name, startrow=1, header=False, index=False)

            worksheet = writer.sheets[sheet_name]

            for col_num, value in enumerate(top_offenders.columns.values):
                worksheet.write(0, col_num, value, formats['header'])
            worksheet.set_column('C:C', 12, formats['percent'])
            worksheet.autofit()

def _create_full_defect_list_sheet(writer, formats, full_df):
    """Creates the sheet with a full list of all defects and conditional formatting."""
    workbook = writer.book

    # Add 'SIDE' to the report columns if it exists
    report_columns = ['UNIT_INDEX_X', 'UNIT_INDEX_Y', 'DEFECT_TYPE', 'QUADRANT', 'SIDE', 'SOURCE_FILE']
    final_df = full_df[[col for col in report_columns if col in full_df.columns]]

    worksheet = workbook.add_worksheet('Full Defect List')
    final_df.to_excel(writer, sheet_name='Full Defect List', startrow=1, header=False, index=False)

    for col_num, value in enumerate(final_df.columns.values):
        worksheet.write(0, col_num, value, formats['header'])

    # The column for DEFECT_TYPE might change if SIDE is present, so find it dynamically
    try:
        defect_type_col_index = final_df.columns.get_loc('DEFECT_TYPE')
        # Convert index to Excel column letter (A=1, B=2, ...)
        defect_type_col_letter = chr(ord('A') + defect_type_col_index)

        formula_parts = [f'${defect_type_col_letter}2="{defect_type}"' for defect_type in CRITICAL_DEFECT_TYPES]
        criteria_formula = f"=OR({', '.join(formula_parts)})"

        # Apply formatting to the entire row range
        worksheet.conditional_format(f'A2:{chr(ord("A") + len(final_df.columns)-1)}{len(final_df) + 1}', {
            'type': 'formula',
            'criteria': criteria_formula,
            'format': formats['critical']
        })
    except KeyError:
        # If DEFECT_TYPE column doesn't exist for some reason, skip formatting
        pass

    worksheet.autofit()

def _generate_and_save_image(
    zip_file: zipfile.ZipFile,
    image_path: str,
    fig_generator: Callable[[], go.Figure],
    logger: logging.Logger
) -> None:
    """
    Helper to generate a Plotly figure, convert it to PNG, and save it to the zip file.
    Handles exceptions and logging.
    """
    try:
        fig = fig_generator()
        img_bytes = fig.to_image(format="png", engine="kaleido", scale=2)
        # ZipFile is thread-safe for writing (but file ordering might vary)
        # To be safe, we acquire a lock if we were writing to disk, but writestr to a BytesIO-backed zip might need care
        # Python's zipfile docs say: "The ZipFile class is not thread-safe."
        # Ah! So parallel execution needs to return BYTES, and the main thread writes to ZIP.

        # NOTE: This function is called by the thread. Returning bytes is safer.
        return image_path, img_bytes

    except Exception as e:
        msg = f"Failed to generate {image_path}: {e}"
        logger.error(msg)
        return image_path, None

# ==============================================================================
# --- Public API Function ---
# ==============================================================================

def generate_coordinate_list_report(defective_coords: set) -> bytes:
    """
    Generates a simple Excel report of unique defective cell coordinates.

    Args:
        defective_coords (set): A set of tuples, where each tuple is a
                                (UNIT_INDEX_X, UNIT_INDEX_Y) coordinate.

    Returns:
        bytes: The content of the Excel file as a bytes object.
    """
    output = io.BytesIO()

    # Convert the set of tuples to a DataFrame
    if defective_coords:
        df = pd.DataFrame(list(defective_coords), columns=['UNIT_INDEX_X', 'UNIT_INDEX_Y'])
        df.sort_values(by=['UNIT_INDEX_Y', 'UNIT_INDEX_X'], inplace=True)
    else:
        df = pd.DataFrame(columns=['UNIT_INDEX_X', 'UNIT_INDEX_Y'])

    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Defective_Cell_Locations')

        # Auto-adjust column widths for better readability
        worksheet = writer.sheets['Defective_Cell_Locations']
        for i, col in enumerate(df.columns):
            width = max(df[col].astype(str).map(len).max(), len(col)) + 2
            worksheet.set_column(i, i, width)

    return output.getvalue()

def generate_excel_report(
    full_df: pd.DataFrame,
    panel_rows: int,
    panel_cols: int,
    source_filename: str = "Sample Data",
    quadrant_selection: str = "All",
    verification_selection: str = "All"
) -> bytes:
    """
    Generates a comprehensive, multi-sheet Excel report.

    This function orchestrates calls to private helpers to build the report.
    """
    output_buffer = io.BytesIO()

    with pd.ExcelWriter(output_buffer, engine='xlsxwriter') as writer:
        workbook = writer.book
        formats = _define_formats(workbook)

        _create_summary_sheet(writer, formats, full_df, panel_rows, panel_cols, source_filename, quadrant_selection, verification_selection)
        _create_panel_wide_top_defects_sheet(writer, formats, full_df)
        _create_per_quadrant_top_defects_sheets(writer, formats, full_df)
        _create_full_defect_list_sheet(writer, formats, full_df)

    excel_bytes = output_buffer.getvalue()
    return excel_bytes

def generate_zip_package(
    full_df: pd.DataFrame,
    panel_rows: int,
    panel_cols: int,
    quadrant_selection: str,
    verification_selection: str,
    source_filename: str,
    true_defect_coords: set,
    include_excel: bool = True,
    include_coords: bool = True,
    include_map: bool = True,
    include_insights: bool = True,
    include_png_all_layers: bool = False,
    include_pareto_png: bool = False,
    include_heatmap_png: bool = False,
    include_stress_png: bool = False,
    include_root_cause_png: bool = False,
    include_still_alive_png: bool = False,
    layer_data: Optional[PanelData] = None,
    process_comment: str = "",
    lot_number: str = "",
    theme_config: Optional[PlotTheme] = None
) -> bytes:
    """
    Generates a ZIP file containing selected report components.
    Includes Excel reports, coordinate lists, and interactive HTML charts.
    Also optionally includes PNG images for all layers/sides.
    """
    zip_buffer = io.BytesIO()

    # --- Logging Setup ---
    log_capture_string = io.StringIO()
    ch = logging.StreamHandler(log_capture_string)
    ch.setLevel(logging.INFO)
    logger = logging.getLogger('report_generator')
    logger.addHandler(ch)
    logger.setLevel(logging.INFO)

    def log(msg):
        logger.info(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    log("Starting generate_zip_package")
    log(f"Options: PNG_Maps={include_png_all_layers}, PNG_Pareto={include_pareto_png}")

    # Store futures for parallel execution
    image_tasks = []

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:

        # 1. Excel Report
        if include_excel:
            excel_bytes = generate_excel_report(
                full_df, panel_rows, panel_cols, source_filename, quadrant_selection, verification_selection
            )
            name_suffix = f"_{process_comment}" if process_comment else ""
            zip_file.writestr(f"Defect_Analysis_Report{name_suffix}.xlsx", excel_bytes)

        # 2. Coordinate List (CSV/Excel)
        if include_coords:
            coord_bytes = generate_coordinate_list_report(true_defect_coords)
            name_suffix = f"_{process_comment}" if process_comment else ""
            zip_file.writestr(f"Defective_Cell_Coordinates{name_suffix}.xlsx", coord_bytes)

        # 3. Defect Map (Interactive HTML) - CURRENT VIEW
        if include_map:
            fig = create_defect_map_figure(
                full_df, panel_rows, panel_cols, quadrant_selection,
                title=f"Panel Defect Map - {quadrant_selection}",
                theme_config=theme_config
            )
            html_content = fig.to_html(full_html=True, include_plotlyjs='cdn')
            zip_file.writestr("Defect_Map.html", html_content)

        # 4. Insights Charts (Interactive HTML) - CURRENT VIEW
        if include_insights:
            sunburst_fig = create_defect_sunburst(full_df, theme_config=theme_config)
            zip_file.writestr("Insights_Sunburst.html", sunburst_fig.to_html(full_html=True, include_plotlyjs='cdn'))

            sankey_fig = create_defect_sankey(full_df, theme_config=theme_config)
            if sankey_fig:
                zip_file.writestr("Insights_Sankey.html", sankey_fig.to_html(full_html=True, include_plotlyjs='cdn'))

        # Prepare for parallel image generation
        # We need a ThreadPoolExecutor.
        # Since Streamlit runs in threads, we must be careful with context, but kaleido usually runs as subprocess.

        # Only start executor if we have image tasks
        if (include_png_all_layers or include_pareto_png or include_heatmap_png or include_stress_png or include_still_alive_png):

            with ThreadPoolExecutor(max_workers=4) as executor:

                # 5. PNG Images (All Layers/Sides) - OPTIONAL
                if (include_png_all_layers or include_pareto_png) and layer_data:
                    log(f"Layer data found. Processing layers.")

                    # Use the new iterator method
                    for layer_num, side, layer_obj in layer_data.get_layers_for_reporting():
                        df = layer_obj.data
                        side_name = "Front" if side == 'F' else "Back"
                        log(f"Queueing Layer {layer_num} - {side_name}")

                        filtered_df = df
                        if verification_selection != 'All':
                            if isinstance(verification_selection, list):
                                if not verification_selection:
                                    filtered_df = filtered_df.iloc[0:0]
                                else:
                                    filtered_df = filtered_df[filtered_df['Verification'].isin(verification_selection)]
                            else:
                                filtered_df = filtered_df[filtered_df['Verification'] == verification_selection]

                        if filtered_df.empty:
                            log(f"  Skipped: DataFrame empty after filtering.")
                            continue

                        # Suffix
                        parts = []
                        if process_comment: parts.append(process_comment)
                        if lot_number: parts.append(lot_number)
                        img_suffix = "_" + "_".join(parts) if parts else ""

                        # Task: Defect Map
                        if include_png_all_layers:
                            task = executor.submit(
                                _generate_and_save_image,
                                None, # zip_file not used in thread
                                f"Images/Layer_{layer_num}_{side_name}_DefectMap{img_suffix}.png",
                                lambda d=filtered_df, ln=layer_num, sn=side_name: create_defect_map_figure(
                                    d, panel_rows, panel_cols, Quadrant.ALL.value,
                                    title=f"Layer {ln} - {sn} - Defect Map",
                                    theme_config=theme_config
                                ),
                                logger
                            )
                            image_tasks.append(task)

                        # Task: Pareto
                        if include_pareto_png:
                            def _make_pareto(d=filtered_df, ln=layer_num, sn=side_name):
                                f = create_pareto_figure(d, Quadrant.ALL.value, theme_config=theme_config)
                                f.update_layout(title=f"Layer {ln} - {sn} - Pareto")
                                return f

                            task = executor.submit(
                                _generate_and_save_image,
                                None,
                                f"Images/Layer_{layer_num}_{side_name}_Pareto{img_suffix}.png",
                                _make_pareto,
                                logger
                            )
                            image_tasks.append(task)

                # 6. Still Alive Map PNG
                if include_still_alive_png or include_png_all_layers:
                    if true_defect_coords:
                        log("Queueing Still Alive Map PNG...")
                        task = executor.submit(
                            _generate_and_save_image,
                            None,
                            "Images/Still_Alive_Map.png",
                            lambda: create_still_alive_figure(panel_rows, panel_cols, true_defect_coords, theme_config=theme_config),
                            logger
                        )
                        image_tasks.append(task)

                # 7. Additional Analysis Charts
                if include_heatmap_png:
                    log("Queueing Heatmap PNG...")
                    from src.plotting import create_unit_grid_heatmap
                    task = executor.submit(
                        _generate_and_save_image,
                        None,
                        "Images/Analysis_Heatmap.png",
                        lambda: create_unit_grid_heatmap(full_df, panel_rows, panel_cols, theme_config=theme_config),
                        logger
                    )
                    image_tasks.append(task)

                if include_stress_png:
                    log("Queueing Stress Map PNG...")
                    from src.plotting import create_stress_heatmap
                    def _make_stress():
                        stress_data = aggregate_stress_data_from_df(full_df, panel_rows, panel_cols)
                        return create_stress_heatmap(stress_data, panel_rows, panel_cols, view_mode="Continuous", theme_config=theme_config)

                    task = executor.submit(
                        _generate_and_save_image,
                        None,
                        "Images/Analysis_StressMap_Cumulative.png",
                        _make_stress,
                        logger
                    )
                    image_tasks.append(task)

            # Collect Results from Threads
            for task in image_tasks:
                path, data = task.result()
                if data:
                    zip_file.writestr(path, data)
                    log(f"Saved {path}")
                else:
                    log(f"Failed to save {path}")

        # Write Debug Log to ZIP
        log("Generation Complete.")
        zip_file.writestr("Debug_Log.txt", log_capture_string.getvalue())

    return zip_buffer.getvalue()
