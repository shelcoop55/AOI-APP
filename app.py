import streamlit as st
from src.config import DEFAULT_PANEL_ROWS, DEFAULT_PANEL_COLS, DYNAMIC_GAP_X, DYNAMIC_GAP_Y, DEFAULT_THEME, PlotTheme
from src.state import SessionStore
from src.views.manager import ViewManager
from src.utils import load_css

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
        with st.form(key="analysis_form", clear_on_submit=False):
            with st.expander("📁 Data Source & Configuration", expanded=True):
                # Use dynamic key to allow resetting the widget
                uploader_key = f"uploaded_files_{st.session_state['uploader_key']}"
                files = st.file_uploader(
                    "Upload Build-Up Layers (e.g., BU-01-...)",
                    type=["xlsx", "xls"],
                    accept_multiple_files=True,
                    key=uploader_key
                )

                # Store inputs in session state automatically via keys, or read them in callback
                # We need them in session state for persistence.
                # If we use key="panel_rows", they are in session state.

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

                st.markdown("---")
                st.markdown("##### Plot Origin Configuration")
                c_origin1, c_origin2 = st.columns(2)
                with c_origin1:
                    st.number_input("X Origin (mm)", value=0.0, step=1.0, key="plot_origin_x", help="Shift the visual coordinate system X origin.")
                with c_origin2:
                    st.number_input("Y Origin (mm)", value=0.0, step=1.0, key="plot_origin_y", help="Shift the visual coordinate system Y origin.")


            with st.expander("⚙️ Advanced Configuration", expanded=False):
                c_gap1, c_gap2 = st.columns(2)
                with c_gap1:
                    st.number_input("Dynamic Gap X (mm)", value=float(DYNAMIC_GAP_X), step=1.0, min_value=0.0, key="dyn_gap_x", help="Dynamic Horizontal Gap.")
                with c_gap2:
                    st.number_input("Dynamic Gap Y (mm)", value=float(DYNAMIC_GAP_Y), step=1.0, min_value=0.0, key="dyn_gap_y", help="Dynamic Vertical Gap.")

            # Callback for Analysis
            def on_run_analysis():
                # Read from dynamic key
                current_uploader_key = f"uploaded_files_{st.session_state['uploader_key']}"
                uploaded_files = st.session_state.get(current_uploader_key, [])
                view_manager.run_analysis(uploaded_files)

            c1, c2 = st.columns(2)
            with c1:
                st.form_submit_button("🚀 Run", on_click=on_run_analysis)

            with c2:
                def on_reset():
                    store.clear_all()
                    if "uploader_key" not in st.session_state:
                        st.session_state["uploader_key"] = 0
                    st.session_state["uploader_key"] += 1

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

            current_theme = PlotTheme(
                background_color=bg_color,
                plot_area_color=plot_color,
                panel_background_color=panel_color,
                axis_color=axis_color,
                text_color=text_color,
                unit_face_color=unit_color,
                unit_edge_color=axis_color,
                inner_gap_color=gap_color
            )
            st.session_state['plot_theme'] = current_theme

    # --- Main Content Area ---
    # Render Navigation (Triggers full rerun to update Sidebar context)
    view_manager.render_navigation()

    @st.fragment
    def render_chart_area():
        view_manager.render_main_view()

    render_chart_area()

if __name__ == '__main__':
    main()
