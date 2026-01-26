import streamlit as st
import pandas as pd
import matplotlib.colors as mcolors

# Import our modularized functions
from src.config import BACKGROUND_COLOR, PLOT_AREA_COLOR, GRID_COLOR, TEXT_COLOR, PANEL_COLOR, GAP_SIZE
from src.data_handler import load_data, calculate_yield_metrics, QUADRANT_WIDTH, QUADRANT_HEIGHT, PANEL_WIDTH, PANEL_HEIGHT
from src.plotting import (
    create_grid_shapes, create_defect_traces, get_color_map_for_defects,
    create_pareto_trace, create_grouped_pareto_trace, create_verification_status_chart
)
from src.reporting import generate_excel_report
from src.enums import ViewMode, Quadrant
from src.state import SessionStore
from src.views.manager import ViewManager
from src.analysis import get_analysis_tool

@st.cache_data
def load_css(file_path: str) -> str:
    """Loads a CSS file and returns its content with injected variables."""
    with open(file_path) as f:
        css = f.read()
    # Define CSS variables from Python config
    css_variables = f"""
    <style>
        :root {{
            --background-color: {BACKGROUND_COLOR};
            --text-color: {TEXT_COLOR};
            --panel-color: {PANEL_COLOR};
            --panel-hover-color: #d48c46;
        }}
        {css}
    </style>
    """
    return css_variables

# ==============================================================================
# --- STREAMLIT APP MAIN LOGIC ---
# ==============================================================================

def main() -> None:
    """
    Main function to configure and run the Streamlit application.
    """
    # --- App Configuration ---
    st.set_page_config(layout="wide", page_title="Panel Defect Analysis")

    # --- Apply Custom CSS for a Professional UI ---
    custom_css = load_css("assets/styles.css")
    st.markdown(custom_css, unsafe_allow_html=True)

    # --- Initialize Session State & View Manager ---
    store = SessionStore()
    view_manager = ViewManager(store)

    if "uploader_key" not in st.session_state:
        st.session_state["uploader_key"] = 0

    # --- Sidebar Control Panel ---
    with st.sidebar:
        st.title("🎛️ Control Panel")

        # --- 1. Analysis Configuration Form ---
        with st.form(key="analysis_form"):
            with st.expander("📁 Data Source & Configuration", expanded=True):
                # Use dynamic key to allow resetting the widget
                uploader_key = f"uploaded_files_{st.session_state['uploader_key']}"
                st.file_uploader(
                    "Upload Build-Up Layers (e.g., BU-01-...)",
                    type=["xlsx", "xls"],
                    accept_multiple_files=True,
                    key=uploader_key
                )
                st.number_input(
                    "Panel Rows", min_value=1, value=DEFAULT_PANEL_ROWS,
                    help="Number of vertical units in a single quadrant.",
                    key="panel_rows"
                )
                st.number_input(
                    "Panel Columns", min_value=1, value=DEFAULT_PANEL_COLS,
                    help="Number of horizontal units in a single quadrant.",
                    key="panel_cols"
                )

                fig.add_annotation(
                    text=annotation_text,
                    align='left',
                    showarrow=False,
                    xref='paper',
                    yref='paper',
                    x=0.88, # Position slightly to the right of the plot
                    y=0.99,  # Position below the legend
                    xanchor='left',
                    yanchor='top',
                    bordercolor=TEXT_COLOR,
                    borderwidth=1,
                    bgcolor='rgba(40,40,40,0.8)',
                    font=dict(color=TEXT_COLOR, size=12)
                )

            st.plotly_chart(fig, use_container_width=True)

        # --- VIEW 2: PARETO CHART ---
        elif view_mode == ViewMode.PARETO.value:
            st.subheader(f"Defect Pareto - Quadrant: {quadrant_selection}")
            fig = go.Figure()

            # Generate the dynamic color map based on all defects in the filtered view
            all_defect_types = display_df['DEFECT_TYPE'].unique()
            color_map = get_color_map_for_defects(all_defect_types)
            
            if quadrant_selection == Quadrant.ALL.value:
                # Show grouped pareto for the full panel view
                pareto_traces = create_grouped_pareto_trace(display_df, color_map)
                for trace in pareto_traces:
                    fig.add_trace(trace)
                fig.update_layout(barmode='group', xaxis_title="Quadrant")
            else:
                # Show a simple pareto for a single quadrant
                pareto_trace = create_pareto_trace(display_df, color_map)
                fig.add_trace(pareto_trace)
                fig.update_layout(xaxis_title="Defect Type")

            fig.update_layout(
                xaxis=dict(categoryorder='total descending', title_font=dict(color=TEXT_COLOR), tickfont=dict(color=TEXT_COLOR)),
                yaxis=dict(title="Count", title_font=dict(color=TEXT_COLOR), tickfont=dict(color=TEXT_COLOR)),
                plot_bgcolor=PLOT_AREA_COLOR, paper_bgcolor=BACKGROUND_COLOR,
                legend=dict(title_font=dict(color=TEXT_COLOR), font=dict(color=TEXT_COLOR)),
                height=600
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # --- VIEW 3: SUMMARY ---
        elif view_mode == ViewMode.SUMMARY.value:
            # Replaced with the provided Summary View block (clean)
            st.header(f"Statistical Summary for Quadrant: {quadrant_selection}")

            if display_df.empty:
                st.info("No defects to summarize in the selected quadrant.")
                return

            if quadrant_selection != Quadrant.ALL.value:
                # Use display_df for view-specific counts
                total_defects = len(display_df)
                total_cells = panel_rows * panel_cols
                defect_density = total_defects / total_cells if total_cells > 0 else 0

                # ** Yield calculation is now handled by the tested function **
                # It should be based on the full data for the selected quadrant.
                quad_yield_df = full_df[full_df['QUADRANT'] == quadrant_selection]
                defective_cells, yield_estimate = calculate_yield_metrics(quad_yield_df, total_cells)

                st.markdown("### Key Performance Indicators (KPIs)")
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Total Defect Count", f"{total_defects:,}")
                col2.metric("True Defective Cells", f"{defective_cells:,}")
                col3.metric("Defect Density", f"{defect_density:.2f} defects/cell")
                col4.metric("Yield Estimate", f"{yield_estimate:.2%}")

                st.divider()
                st.markdown("### Top Defect Types")
                top_offenders = display_df['DEFECT_TYPE'].value_counts().reset_index()
                top_offenders.columns = ['Defect Type', 'Count']
                top_offenders['Percentage'] = (top_offenders['Count'] / total_defects) * 100

                theme_cmap = mcolors.LinearSegmentedColormap.from_list("theme_cmap", [PLOT_AREA_COLOR, PANEL_COLOR])

                st.dataframe(
                    top_offenders.style.format({'Percentage': '{:.2f}%'}).background_gradient(cmap=theme_cmap, subset=['Count']),
                    width='stretch'
                )

            else:
                # --- NEW: Panel-Wide KPIs ---
                st.markdown("### Panel-Wide KPIs (Filtered)")
                # Use display_df for view-specific counts
                total_defects = len(display_df)
                total_cells = (panel_rows * panel_cols) * 4
                defect_density = total_defects / total_cells if total_cells > 0 else 0

                # ** Yield calculation is now handled by the tested function **
                # It should be based on the full data for the entire panel.
                defective_cells, yield_estimate = calculate_yield_metrics(full_df, total_cells)

                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Filtered Defect Count", f"{total_defects:,}")
                col2.metric("True Defective Cells", f"{defective_cells:,}")
                col3.metric("Filtered Defect Density", f"{defect_density:.2f} defects/cell")
                col4.metric("Filtered Yield Estimate", f"{yield_estimate:.2%}")
                st.divider()
                # --- END NEW ---

                st.markdown("### Quarterly KPI Breakdown")

                kpi_data = []
                quadrants = ['Q1', 'Q2', 'Q3', 'Q4']
                total_cells_per_quad = panel_rows * panel_cols

                # Note: For the breakdown, we use the 'filtered_df' which is only filtered by
                # verification, not by quadrant, to get accurate per-quadrant counts.
                for quad in quadrants:
                    # Filtered data for T/F/TA counts
                    quad_view_df = filtered_df[filtered_df['QUADRANT'] == quad]
                    total_quad_defects = len(quad_view_df)

                    # ** Yield calculation is now handled by the tested function **
                    # Use the full dataset, filtered only by the current quadrant
                    quad_yield_df = full_df[full_df['QUADRANT'] == quad]
                    defective_cells, yield_estimate = calculate_yield_metrics(quad_yield_df, total_cells_per_quad)

                    # Get verification counts from the view-specific dataframe
                    verification_counts = quad_view_df['Verification'].value_counts()
                    true_count = int(verification_counts.get('T', 0))
                    false_count = int(verification_counts.get('F', 0))
                    ta_count = int(verification_counts.get('TA', 0))

                    kpi_data.append({
                        "Quadrant": quad,
                        "Total Defects": total_quad_defects,
                        "True (T)": true_count,
                        "False (F)": false_count,
                        "Acceptable (TA)": ta_count,
                        "True Defective Cells": defective_cells,
                        "Yield": f"{yield_estimate:.2%}"
                    })

                if kpi_data:
                    kpi_df = pd.DataFrame(kpi_data)
                    # Reorder columns for logical presentation
                    kpi_df = kpi_df[['Quadrant', 'Total Defects', 'True (T)', 'False (F)', 'Acceptable (TA)', 'True Defective Cells', 'Yield']]
                    st.dataframe(kpi_df, width='stretch')
                else:
                    store.selected_layer = None

                # Calculate TOTAL OFFSET for Plotting
                # Symmetrical Logic: Start Position of Q1 = FixedOffset + DynGap (Left of Q1)
                total_off_x_struct = off_x_struct + dyn_gap_x
                total_off_y_struct = off_y_struct + dyn_gap_y

                store.analysis_params = {
                    "panel_rows": rows,
                    "panel_cols": cols,
                    "panel_width": p_width,
                    "panel_height": p_height,
                    "gap_x": effective_gap_x, # Use effective gap for plotting logic
                    "gap_y": effective_gap_y,
                    "gap_size": effective_gap_x, # Backwards compatibility
                    "lot_number": lot,
                    "process_comment": comment,
                    # IMPORTANT: Use Structural Offset for drawing the grid in the Frame
                    "offset_x": total_off_x_struct,
                    "offset_y": total_off_y_struct,

                    # Store Visual Origins for Axis Correction
                    "visual_origin_x": visual_origin_x,
                    "visual_origin_y": visual_origin_y,

                    "dyn_gap_x": dyn_gap_x,
                    "dyn_gap_y": dyn_gap_y,

                    # Store Structural Fixed Offsets for Inner Border Drawing
                    "fixed_offset_x": off_x_struct,
                    "fixed_offset_y": off_y_struct
                }
                store.report_bytes = None

            c1, c2 = st.columns(2)
            with c1:
                st.form_submit_button("🚀 Run", on_click=on_run_analysis)

            with c2:
                # Reset Button logic integrated into the form area (but form_submit_button is primary action)
                # Since we cannot put a standard button inside a form that triggers a rerun cleanly without submitting the form,
                # we will use another form_submit_button or place it outside if strictly required.
                # However, user asked "inside Data Source & Configuration".
                # Standard st.button inside a form behaves as a submit button.

                def on_reset():
                    store.clear_all()
                    # Re-initialize uploader_key immediately after clearing state
                    # to prevent KeyError on rerun or subsequent access
                    if "uploader_key" not in st.session_state:
                        st.session_state["uploader_key"] = 0

                    # Increment key to recreate file uploader widget (effectively clearing it)
                    st.session_state["uploader_key"] += 1
                    # Rerun will happen automatically after callback

                st.form_submit_button("🔄 Reset", on_click=on_reset, type="secondary")

        # --- 2. Appearance & Style (Expander) ---
        with st.expander("🎨 Appearance & Style", expanded=False):
            # Create PlotTheme inputs and update session state immediately
            bg_color = st.color_picker("Background Color", value=DEFAULT_THEME.background_color, key="style_bg")
            plot_color = st.color_picker("Plot Area Color", value=DEFAULT_THEME.plot_area_color, key="style_plot")
            panel_color = st.color_picker("Panel Color", value=DEFAULT_THEME.panel_background_color, key="style_panel")
            axis_color = st.color_picker("Axis Color", value=DEFAULT_THEME.axis_color, key="style_axis")
            text_color = st.color_picker("Text Color", value=DEFAULT_THEME.text_color, key="style_text")
            unit_color = st.color_picker("Unit Color", value=DEFAULT_THEME.unit_face_color, key="style_unit")
            gap_color = st.color_picker("Gap Color", value=DEFAULT_THEME.inner_gap_color, key="style_gap")

            # Construct Theme Object
            current_theme = PlotTheme(
                background_color=bg_color,
                plot_area_color=plot_color,
                panel_background_color=panel_color,
                axis_color=axis_color,
                text_color=text_color,
                # Use user selection
                unit_face_color=unit_color,
                unit_edge_color=axis_color, # Match axis for grid edges
                inner_gap_color=gap_color
            )

            # Store in session state for Views to access
            st.session_state['plot_theme'] = current_theme

    # --- Main Content Area ---
    # Header removed to save space
    # st.title("📊 Panel Defect Analysis Tool")

    # Render Navigation (Triggers full rerun to update Sidebar context)
    view_manager.render_navigation()

    @st.fragment
    def render_chart_area():
        # Render Main View (Chart Area) - Isolated updates
        view_manager.render_main_view()

    render_chart_area()

if __name__ == '__main__':
    main()
