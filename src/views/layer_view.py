import streamlit as st
import pandas as pd
import matplotlib.colors as mcolors
from src.state import SessionStore
from src.enums import ViewMode, Quadrant
from src.plotting import create_defect_map_figure, create_pareto_figure
from src.config import SAFE_VERIFICATION_VALUES, PLOT_AREA_COLOR, PANEL_COLOR, GAP_SIZE, PANEL_WIDTH, PANEL_HEIGHT, PlotTheme
from src.analysis.calculations import calculate_layer_summary

def render_layer_view(store: SessionStore, view_mode: str, quadrant_selection: str, verification_selection: any, theme_config: PlotTheme = None):
    params = store.analysis_params
    panel_rows, panel_cols = params.get("panel_rows", 7), params.get("panel_cols", 7)
    lot_number = params.get("lot_number")

    selected_layer_num = store.selected_layer
    if selected_layer_num:
        layer_info = store.layer_data.get(selected_layer_num, {})
        side_df = layer_info.get(store.selected_side)

        if side_df is not None and not side_df.empty:
            # Filter Efficiency: Local filter (not heavy enough to cache separately in st.session_state usually, but good practice)
            # We can rely on pandas speed here.

            if isinstance(verification_selection, list):
                if not verification_selection:
                    filtered_df = side_df.iloc[0:0]
                else:
                    filtered_df = side_df[side_df['Verification'].isin(verification_selection)]
            else:
                 filtered_df = side_df[side_df['Verification'] == verification_selection] if verification_selection != 'All' else side_df

            display_df = filtered_df[filtered_df['QUADRANT'] == quadrant_selection] if quadrant_selection != Quadrant.ALL.value else filtered_df

            if view_mode == ViewMode.DEFECT.value:
                # Retrieve layout params
                offset_x = params.get("offset_x", 0.0)
                offset_y = params.get("offset_y", 0.0)
                gap_x = params.get("gap_x", GAP_SIZE)
                gap_y = params.get("gap_y", GAP_SIZE)
                panel_width = params.get("panel_width", PANEL_WIDTH)
                panel_height = params.get("panel_height", PANEL_HEIGHT)
                visual_origin_x = params.get("visual_origin_x", 0.0)
                visual_origin_y = params.get("visual_origin_y", 0.0)
                fixed_offset_x = params.get("fixed_offset_x", 0.0)
                fixed_offset_y = params.get("fixed_offset_y", 0.0)

                fig = create_defect_map_figure(
                    display_df, panel_rows, panel_cols, quadrant_selection, lot_number,
                    offset_x=offset_x, offset_y=offset_y,
                    gap_x=gap_x, gap_y=gap_y,
                    panel_width=panel_width, panel_height=panel_height,
                    theme_config=theme_config,
                    visual_origin_x=visual_origin_x,
                    visual_origin_y=visual_origin_y,
                    fixed_offset_x=fixed_offset_x,
                    fixed_offset_y=fixed_offset_y
                )
                st.plotly_chart(fig, use_container_width=True)
            elif view_mode == ViewMode.PARETO.value:
                fig = create_pareto_figure(display_df, quadrant_selection, theme_config=theme_config)
                st.plotly_chart(fig, use_container_width=True)
            elif view_mode == ViewMode.SUMMARY.value:
                render_summary_view(
                    display_df=display_df,
                    quadrant_selection=quadrant_selection,
                    panel_rows=panel_rows,
                    panel_cols=panel_cols,
                    layer_info=layer_info, # Dict of dfs
                    selected_layer_num=selected_layer_num,
                    filtered_df=filtered_df,
                    theme_config=theme_config
                )

def render_summary_view(
    display_df: pd.DataFrame,
    quadrant_selection: str,
    panel_rows: int,
    panel_cols: int,
    layer_info: dict,
    selected_layer_num: int,
    filtered_df: pd.DataFrame,
    theme_config: PlotTheme = None
):
    st.header(f"Statistical Summary for Layer {selected_layer_num}, Quadrant: {quadrant_selection}")

    if display_df.empty:
        st.info("No defects to summarize in the selected quadrant.")
        return

    # Use cached calculation
    # We pass the raw layer info to the cached function
    # Note: layer_info contains BuildUpLayer objects or DFs.
    # calculations.py expects {side: df}.
    # Ensure transformation
    layer_data_dict = {}
    for side, val in layer_info.items():
        if hasattr(val, 'data'):
            layer_data_dict[side] = val.data
        else:
            layer_data_dict[side] = val

    summary_data = calculate_layer_summary(layer_data_dict, panel_rows, panel_cols, quadrant_selection)

    # Determine colors
    plot_col = theme_config.plot_area_color if theme_config else PLOT_AREA_COLOR
    panel_col = theme_config.panel_background_color if theme_config else PANEL_COLOR

    if quadrant_selection != Quadrant.ALL.value:
        total_defects = len(display_df)
        total_cells = panel_rows * panel_cols
        defect_density = total_defects / total_cells if total_cells > 0 else 0

        yield_estimate = summary_data.get('yield_quad', 0)
        defective_cells = summary_data.get('defective_cells_quad', 0)

        st.markdown("### Key Performance Indicators (KPIs)")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Defect Count", f"{total_defects:,}")
        col2.metric("True Defective Cells", f"{defective_cells:,}")
        col3.metric("Defect Density", f"{defect_density:.2f} defects/cell")
        col4.metric("Yield Estimate", f"{yield_estimate:.2%}")

        st.divider()
        st.markdown("### Top Defect Types")

        has_verification = display_df['HAS_VERIFICATION_DATA'].iloc[0] if 'HAS_VERIFICATION_DATA' in display_df.columns else False

        if has_verification:
            top_offenders = display_df.groupby(['DEFECT_TYPE', 'Verification']).size().reset_index(name='Count')
            top_offenders.rename(columns={'DEFECT_TYPE': 'Defect Type'}, inplace=True)
            top_offenders = top_offenders.sort_values(by='Count', ascending=False).reset_index(drop=True)
        else:
            top_offenders = display_df['DEFECT_TYPE'].value_counts().reset_index()
            top_offenders.columns = ['Defect Type', 'Count']

        top_offenders['Percentage'] = (top_offenders['Count'] / total_defects) * 100
        theme_cmap = mcolors.LinearSegmentedColormap.from_list("theme_cmap", [plot_col, panel_col])
        st.dataframe(
            top_offenders.style.format({'Percentage': '{:.2f}%'}).background_gradient(cmap=theme_cmap, subset=['Count']),
            use_container_width=True
        )
    else:
        st.markdown("### Panel-Wide KPIs (Filtered)")
        total_defects = len(display_df)
        total_cells = (panel_rows * panel_cols) * 4
        defect_density = total_defects / total_cells if total_cells > 0 else 0

        yield_estimate = summary_data.get('yield_board', 0)

        # Count true defects in display_df
        safe_upper = {v.upper() for v in SAFE_VERIFICATION_VALUES}
        true_defects_selected_side = display_df[~display_df['Verification'].str.upper().isin(safe_upper)]
        defective_cells_selected_side = len(true_defects_selected_side[['UNIT_INDEX_X', 'UNIT_INDEX_Y']].drop_duplicates())

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Filtered Defect Count", f"{total_defects:,}")
        col2.metric("True Defective Cells", f"{defective_cells_selected_side:,}")
        col3.metric("Filtered Defect Density", f"{defect_density:.2f} defects/cell")
        col4.metric("Filtered Yield Estimate", f"{yield_estimate:.2%}")

        st.divider()
        st.markdown("### Quarterly KPI Breakdown")

        # Calculation logic for breakdown (kept local as it depends on filtered_df view)
        kpi_data = []
        quadrants = ['Q1', 'Q2', 'Q3', 'Q4']
        total_cells_per_quad = panel_rows * panel_cols

        # Re-construct full layer df for Yield calculation per quad
        dfs = list(layer_data_dict.values())
        full_layer_df_static = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

        for quad in quadrants:
            quad_view_df = filtered_df[filtered_df['QUADRANT'] == quad]
            total_quad_defects = len(quad_view_df)

            # Yield
            if not full_layer_df_static.empty:
                yield_df = full_layer_df_static[full_layer_df_static['QUADRANT'] == quad]
                true_yield_defects = yield_df[~yield_df['Verification'].str.upper().isin(safe_upper)]
                combined_defective_cells = len(true_yield_defects[['UNIT_INDEX_X', 'UNIT_INDEX_Y']].drop_duplicates())
                yield_est = (total_cells_per_quad - combined_defective_cells) / total_cells_per_quad if total_cells_per_quad > 0 else 0
            else:
                yield_est = 0

            # Selected Side True Defects
            selected_side_yield_df = quad_view_df[~quad_view_df['Verification'].str.upper().isin(safe_upper)]
            defective_cells_selected_side = len(selected_side_yield_df[['UNIT_INDEX_X', 'UNIT_INDEX_Y']].drop_duplicates())

            safe_count = len(quad_view_df[quad_view_df['Verification'].str.upper().isin(safe_upper)])
            true_count = total_quad_defects - safe_count
            safe_ratio = safe_count / total_quad_defects if total_quad_defects > 0 else 0.0

            kpi_data.append({
                "Quadrant": quad,
                "Total Defects": total_quad_defects,
                "True Defects": true_count,
                "Non-Detects (Safe)": safe_count,
                "True Defective Cells": defective_cells_selected_side,
                "Safe Ratio": f"{safe_ratio:.2%}",
                "Yield": f"{yield_est:.2%}"
            })

        if kpi_data:
            kpi_df = pd.DataFrame(kpi_data)
            st.dataframe(
                kpi_df.style
                .background_gradient(cmap='Reds', subset=['Total Defects', 'True Defects', 'Non-Detects (Safe)'])
                .format({'Safe Ratio': '{:>8}', 'Yield': '{:>8}'}),
                use_container_width=True
            )
        else:
            st.info("No data to display for the quarterly breakdown based on current filters.")
