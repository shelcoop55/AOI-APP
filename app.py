import streamlit as st
import pandas as pd
from src.config import GAP_SIZE, BACKGROUND_COLOR, TEXT_COLOR, PANEL_COLOR
from src.data_handler import load_data, get_true_defect_coordinates
from src.reporting import generate_zip_package
from src.enums import ViewMode, Quadrant
from src.state import SessionStore
from src.views.manager import ViewManager
from src.analysis import get_analysis_tool

def load_css(file_path: str) -> None:
    """Loads a CSS file and injects it into the Streamlit app."""
    try:
        with open(file_path) as f:
            css = f.read()
            css_variables = f'''
            <style>
                :root {{
                    --background-color: {BACKGROUND_COLOR};
                    --text-color: {TEXT_COLOR};
                    --panel-color: {PANEL_COLOR};
                    --panel-hover-color: #d48c46;
                }}
                {css}
            </style>
            '''
            st.markdown(css_variables, unsafe_allow_html=True)
    except FileNotFoundError:
        pass # Handle missing CSS safely

def main() -> None:
    """Main function to configure and run the Streamlit application."""
    st.set_page_config(layout="wide", page_title="Panel Defect Analysis")
    load_css("assets/styles.css")

    # --- Initialize Session State & View Manager ---
    store = SessionStore()
    view_manager = ViewManager(store)

    # --- Sidebar Control Panel ---
    with st.sidebar:
        st.title("🎛️ Control Panel")

        # --- 1. Analysis Configuration Form ---
        # Note: We use st.form to group inputs, but use on_click for the submit
        # to handle state updates efficiently.
        with st.form(key="analysis_form"):
            with st.expander("📁 Data Source & Configuration", expanded=True):
                st.file_uploader(
                    "Upload Build-Up Layers (e.g., BU-01-...)",
                    type=["xlsx", "xls"],
                    accept_multiple_files=True,
                    key="uploaded_files"
                )
                st.number_input(
                    "Panel Rows", min_value=1, value=7,
                    help="Number of vertical units in a single quadrant.",
                    key="panel_rows"
                )
                st.number_input(
                    "Panel Columns", min_value=1, value=7,
                    help="Number of horizontal units in a single quadrant.",
                    key="panel_cols"
                )
                st.text_input(
                    "Lot Number (Optional)",
                    help="Enter the Lot Number to display it on the defect map.",
                    key="lot_number"
                )

            # Callback for Analysis
            def on_run_analysis():
                files = st.session_state.uploaded_files
                rows = st.session_state.panel_rows
                cols = st.session_state.panel_cols
                lot = st.session_state.lot_number

                # Load Data
                data = load_data(files, rows, cols)
                if data:
                    store.layer_data = data
                    store.selected_layer = max(data.keys())
                    store.active_view = 'layer'

                    # Auto-select side
                    layer_info = data.get(store.selected_layer, {})
                    if 'F' in layer_info:
                        store.selected_side = 'F'
                    elif 'B' in layer_info:
                        store.selected_side = 'B'
                    elif layer_info:
                        store.selected_side = next(iter(layer_info.keys()))

                    # Initialize Multi-Layer Selection defaults
                    store.multi_layer_selection = sorted(data.keys())
                    all_sides = set()
                    for l_data in data.values():
                        all_sides.update(l_data.keys())
                    store.multi_side_selection = sorted(list(all_sides))
                else:
                    store.selected_layer = None

                store.analysis_params = {
                    "panel_rows": rows,
                    "panel_cols": cols,
                    "gap_size": GAP_SIZE,
                    "lot_number": lot
                }
                store.report_bytes = None

            st.form_submit_button("🚀 Run Analysis", on_click=on_run_analysis)

        st.divider()

        # --- Sidebar State Logic ---

        # Only show advanced controls if data is loaded
        if store.layer_data:
            if st.button("🔄 Reset Analysis", type="secondary", help="Clears all loaded data and resets the tool."):
                store.clear_all()
                st.rerun()

            # --- Analysis Tools (Strategy Pattern) ---
            with st.expander("🔍 Analysis Tools", expanded=True):
                st.caption("Select Analysis View")
                # Extended Options including Still Alive and Multi-Layer
                analysis_options = [
                    ViewMode.HEATMAP.value,
                    ViewMode.STRESS.value,
                    ViewMode.ROOT_CAUSE.value,
                    ViewMode.INSIGHTS.value,
                    ViewMode.STILL_ALIVE.value,
                    ViewMode.MULTI_LAYER.value
                ]

                # We need to sync `store.active_view` and `store.analysis_subview`
                # If active_view is 'layer', we might want to unselect the radio or show a "Layer View" option?
                # For simplicity, let's treat "Layer View" as the default state when NOT in Analysis Dashboard.
                # However, the user wants Still Alive/Multi-Layer reachable from here.
                # Let's add "Layer Inspection" as the first option to allow returning to it.

                # NOTE: ViewMode.DEFECT is "Defect View", which is a sub-view of Layer Inspection.
                # We'll use a custom string "Layer Inspection" to represent the main view.
                LAYER_INSPECTION_LABEL = "Layer Inspection"
                full_options = [LAYER_INSPECTION_LABEL] + analysis_options

                # Determine current selection based on store state
                current_selection = LAYER_INSPECTION_LABEL
                if store.active_view == 'layer':
                    current_selection = LAYER_INSPECTION_LABEL
                elif store.active_view == 'still_alive':
                    current_selection = ViewMode.STILL_ALIVE.value
                elif store.active_view == 'multi_layer_defects':
                    current_selection = ViewMode.MULTI_LAYER.value
                elif store.active_view == 'analysis_dashboard':
                    current_selection = store.analysis_subview

                def on_view_change():
                    selection = st.session_state.main_view_selector
                    if selection == LAYER_INSPECTION_LABEL:
                        store.active_view = 'layer'
                    elif selection == ViewMode.STILL_ALIVE.value:
                        store.active_view = 'still_alive'
                    elif selection == ViewMode.MULTI_LAYER.value:
                        store.active_view = 'multi_layer_defects'
                    else:
                        store.active_view = 'analysis_dashboard'
                        store.analysis_subview = selection

                st.radio(
                    "Go to:",
                    full_options,
                    index=full_options.index(current_selection) if current_selection in full_options else 0,
                    key="main_view_selector",
                    on_change=on_view_change
                )

                st.divider()

                # Render Sub-controls for specific analysis tools if active
                if store.active_view == 'analysis_dashboard':
                    tool_instance = get_analysis_tool(store.analysis_subview, store)
                    if tool_instance:
                        tool_instance.render_sidebar()

                # Render Still Alive Sidebar controls if active
                if store.active_view == 'still_alive':
                     from src.views.still_alive import render_still_alive_sidebar
                     render_still_alive_sidebar(store)

                # Render Multi-Layer Sidebar controls if active
                if store.active_view == 'multi_layer_defects':
                    with st.expander("🛠️ Multi-Layer Filters", expanded=True):
                        all_layers = sorted(store.layer_data.keys())
                        all_sides = set()
                        for l_data in store.layer_data.values():
                            all_sides.update(l_data.keys())

                        side_map = {'F': 'Front', 'B': 'Back'}
                        side_map_rev = {'Front': 'F', 'Back': 'B'}
                        available_side_labels = sorted([side_map.get(s, s) for s in all_sides])

                        st.multiselect(
                            "Select Layers",
                            options=all_layers,
                            default=all_layers,
                            key="multi_layer_selection"
                        )

                        sel_sides_labels = st.multiselect(
                             "Select Sides",
                             options=available_side_labels,
                             default=available_side_labels,
                             key="multi_side_selection_widget"
                        )
                        store.multi_side_selection = [side_map_rev.get(label, label) for label in sel_sides_labels]

            st.divider()

            # --- Reporting ---
            with st.expander("📥 Reporting", expanded=True):
                st.subheader("Generate Report")
                col_rep1, col_rep2 = st.columns(2)
                with col_rep1:
                    include_excel = st.checkbox("Excel Report", value=True)
                    include_coords = st.checkbox("Coordinate List", value=True)
                with col_rep2:
                    include_map = st.checkbox("Defect Map (HTML)", value=True)
                    include_insights = st.checkbox("Insights Charts", value=True)

                st.markdown("**Export Images (All Layers):**")
                col_img1, col_img2 = st.columns(2)
                with col_img1:
                    include_png_all = st.checkbox("Defect Maps (PNG)", value=False)
                with col_img2:
                    include_pareto_png = st.checkbox("Pareto Charts (PNG)", value=False)

                # Disable if in analysis view? Or keep enabled?
                # Original logic disabled it for some views. Let's keep it generally enabled but maybe warn?
                # We'll stick to original logic: Layer Data is always source of truth.
                # disable_layer_controls was previously used.

                if st.button("Generate Download Package"):
                    with st.spinner("Generating Package..."):
                        full_df = store.layer_data.get_combined_dataframe()
                        true_defect_coords = get_true_defect_coordinates(store.layer_data)

                        store.report_bytes = generate_zip_package(
                            full_df=full_df,
                            panel_rows=store.analysis_params.get('panel_rows', 7),
                            panel_cols=store.analysis_params.get('panel_cols', 7),
                            quadrant_selection=store.quadrant_selection,
                            verification_selection=store.verification_selection,
                            source_filename="Multiple Files",
                            true_defect_coords=true_defect_coords,
                            include_excel=include_excel,
                            include_coords=include_coords,
                            include_map=include_map,
                            include_insights=include_insights,
                            include_png_all_layers=include_png_all,
                            include_pareto_png=include_pareto_png,
                            layer_data=store.layer_data
                        )
                        st.success("Package generated successfully!")

                params_local = store.analysis_params
                lot_num_str = f"_{params_local.get('lot_number', '')}" if params_local.get('lot_number') else ""
                zip_filename = f"defect_package_layer_{store.selected_layer}{lot_num_str}.zip"
                st.download_button(
                    "Download Package (ZIP)",
                    data=store.report_bytes or b"",
                    file_name=zip_filename,
                    mime="application/zip",
                    disabled=store.report_bytes is None
                )

    # --- Main Content Area ---
    st.title("📊 Panel Defect Analysis Tool")

    # Render Navigation (Triggers full rerun to update Sidebar context)
    view_manager.render_navigation()

    @st.fragment
    def render_chart_area():
        # Render Main View (Chart Area) - Isolated updates
        view_manager.render_main_view()

    render_chart_area()

if __name__ == '__main__':
    main()
