import streamlit as st
import pandas as pd
from src.config import (
    GAP_SIZE, BACKGROUND_COLOR, TEXT_COLOR, PANEL_COLOR,
    DEFAULT_QUAD_WIDTH, DEFAULT_QUAD_HEIGHT, DEFAULT_MARGIN_X, DEFAULT_MARGIN_Y,
    DEFAULT_GAP_MID, DEFAULT_GAP_UNIT
)
from src.data_handler import load_data, get_true_defect_coordinates
from src.reporting import generate_zip_package
from src.layout import LayoutParams
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
    st.set_page_config(layout="wide", page_title="Panel Defect Analysis", initial_sidebar_state="expanded")
    load_css("assets/styles.css")

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
                st.text_input(
                    "Process Step / Comment",
                    help="Enter a comment (e.g., Post Etching) to tag these layers.",
                    key="process_comment"
                )

            with st.expander("⚙️ Advanced Configuration (Layout)", expanded=False):
                # 1. Quadrant Dimensions (Spec Driven)
                c_dim1, c_dim2 = st.columns(2)
                with c_dim1:
                    st.number_input("Quadrant Width (mm)", value=float(DEFAULT_QUAD_WIDTH), step=1.0, key="quad_width", help="Width of a single quadrant.")
                with c_dim2:
                    st.number_input("Quadrant Height (mm)", value=float(DEFAULT_QUAD_HEIGHT), step=1.0, key="quad_height", help="Height of a single quadrant.")

                # 2. Margins (Origins)
                c_mar1, c_mar2 = st.columns(2)
                with c_mar1:
                    st.number_input("Margin X (Left/Right)", value=float(DEFAULT_MARGIN_X), step=0.5, key="margin_x", help="Outer margin on X axis.")
                with c_mar2:
                    st.number_input("Margin Y (Top/Bottom)", value=float(DEFAULT_MARGIN_Y), step=0.5, key="margin_y", help="Outer margin on Y axis.")

                # 3. Gaps
                c_gap1, c_gap2 = st.columns(2)
                with c_gap1:
                    st.number_input("Central Gap (mm)", value=float(DEFAULT_GAP_MID), step=0.5, min_value=0.0, key="gap_mid", help="Gap between quadrants (X/Y).")
                with c_gap2:
                    st.number_input("Inter-Unit Gap (mm)", value=float(DEFAULT_GAP_UNIT), step=0.05, min_value=0.0, format="%.2f", key="gap_unit", help="Gap between small units inside a quadrant.")

            # Callback for Analysis
            def on_run_analysis():
                # Read from dynamic key
                current_uploader_key = f"uploaded_files_{st.session_state['uploader_key']}"
                files = st.session_state.get(current_uploader_key, [])

                rows = st.session_state.panel_rows
                cols = st.session_state.panel_cols
                lot = st.session_state.lot_number
                comment = st.session_state.process_comment

                # Retrieve Advanced Params
                quad_w = st.session_state.get("quad_width", DEFAULT_QUAD_WIDTH)
                quad_h = st.session_state.get("quad_height", DEFAULT_QUAD_HEIGHT)
                margin_x = st.session_state.get("margin_x", DEFAULT_MARGIN_X)
                margin_y = st.session_state.get("margin_y", DEFAULT_MARGIN_Y)
                gap_mid = st.session_state.get("gap_mid", DEFAULT_GAP_MID)
                gap_unit = st.session_state.get("gap_unit", DEFAULT_GAP_UNIT)

                # Create LayoutParams object
                layout = LayoutParams(
                    panel_cols=cols, panel_rows=rows,
                    quad_width=quad_w, quad_height=quad_h,
                    margin_x=margin_x, margin_y=margin_y,
                    gap_mid=gap_mid, gap_unit=gap_unit
                )

                # Load Data
                # load_data needs to know how to calculate coordinates.
                # We pass the LayoutParams object or just the dimensions?
                # load_data caching logic is strict on args.
                # Ideally, we pass the `layout` object.
                # Updating `load_data` signature in data_handler.py is next step.
                # For now, I will pass `layout`.

                data = load_data(files, layout)
                if data:
                    # UPDATE: Store ID and Metadata, NOT the object
                    if not files:
                        store.dataset_id = "sample_data"
                    else:
                        # Simple ID generation based on filenames for tracking
                        store.dataset_id = str(hash(tuple(f.name for f in files)))

                    # Store lightweight metadata for UI logic (keys only)
                    # We need a serializable dict structure: {layer_num: {side: True}}
                    meta = {}
                    for l_num, sides in data.items():
                        meta[l_num] = list(sides.keys())
                    store.layer_data_keys = meta

                    # Logic using the data object (which is local var here, safe)
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
                    "layout": layout, # Store the full layout object
                    "lot_number": lot,
                    "process_comment": comment
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
                    # Increment key to recreate file uploader widget (effectively clearing it)
                    st.session_state["uploader_key"] += 1
                    # Rerun will happen automatically after callback

                st.form_submit_button("🔄 Reset", on_click=on_reset, type="secondary")

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
