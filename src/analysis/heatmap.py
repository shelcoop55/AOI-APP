import streamlit as st
import pandas as pd
from src.analysis.base import AnalysisTool
from src.plotting import create_density_contour_map
from src.config import PANEL_WIDTH, PANEL_HEIGHT, GAP_SIZE

@st.cache_data
def get_filtered_heatmap_data(
    _panel_data,
    panel_data_id: str,
    selected_layer_nums: list,
    side_selection: list,
    selected_verifs: list,
    selected_quadrant: str
) -> pd.DataFrame:
    """
    Cached helper to filter and aggregate heatmap data.
    """
    dfs_to_concat = []

    # Optimize: Iterate only selected layers
    for layer_num in selected_layer_nums:
        # Access internal storage directly if possible or use get_layer
        # Using public API:
        sides_to_process = []
        if "Front" in side_selection: sides_to_process.append('F')
        if "Back" in side_selection: sides_to_process.append('B')

        for side in sides_to_process:
            layer = _panel_data.get_layer(layer_num, side)
            if layer and not layer.data.empty:
                df = layer.data

                # Apply Filters
                if 'Verification' in df.columns and selected_verifs:
                     df = df[df['Verification'].astype(str).isin(selected_verifs)]

                if selected_quadrant != "All" and 'QUADRANT' in df.columns:
                     df = df[df['QUADRANT'] == selected_quadrant]

                if not df.empty:
                     dfs_to_concat.append(df)

    if dfs_to_concat:
        return pd.concat(dfs_to_concat, ignore_index=True)
    return pd.DataFrame()


class HeatmapTool(AnalysisTool):
    @property
    def name(self) -> str:
        return "Heatmap Analysis"

    def render_sidebar(self):
        pass

    def render_main(self):
        params = self.store.analysis_params
        panel_rows, panel_cols = params.get("panel_rows", 7), params.get("panel_cols", 7)

        # READ INPUTS FROM UNIFIED FILTER STATE
        selected_layer_nums = self.store.multi_layer_selection or self.store.layer_data.get_all_layer_nums()
        side_selection = st.session_state.get("analysis_side_pills", ["Front", "Back"])
        selected_verifs = st.session_state.get("multi_verification_selection", [])
        smoothing = st.session_state.get("heatmap_sigma", 5)
        saturation = 0
        view_mode = "Continuous"
        selected_quadrant = st.session_state.get("analysis_quadrant_selection", "All")

        offset_x = params.get("offset_x", 0.0)
        offset_y = params.get("offset_y", 0.0)
        gap_x = params.get("gap_x", GAP_SIZE)
        gap_y = params.get("gap_y", GAP_SIZE)
        gap_size = gap_x

        visual_origin_x = params.get("visual_origin_x", 0.0)
        visual_origin_y = params.get("visual_origin_y", 0.0)
        fixed_offset_x = params.get("fixed_offset_x", 0.0)
        fixed_offset_y = params.get("fixed_offset_y", 0.0)

        panel_width = params.get("panel_width", PANEL_WIDTH)
        panel_height = params.get("panel_height", PANEL_HEIGHT)

        quad_width = panel_width / 2
        quad_height = panel_height / 2

        # --- DATA PREPARATION (CACHED) ---
        panel_id = getattr(self.store.layer_data, "id", "static")

        combined_heatmap_df = get_filtered_heatmap_data(
            self.store.layer_data,
            panel_id,
            selected_layer_nums,
            side_selection,
            selected_verifs,
            selected_quadrant
        )

        if not combined_heatmap_df.empty:
            flip_back = st.session_state.get("flip_back_side", True)
            contour_fig = create_density_contour_map(
                combined_heatmap_df, panel_rows, panel_cols,
                show_points=False,
                smoothing_factor=smoothing * 5,
                saturation_cap=saturation,
                show_grid=False,
                view_mode=view_mode,
                flip_back=flip_back,
                quadrant_selection=selected_quadrant,
                offset_x=offset_x,
                offset_y=offset_y,
                gap_x=gap_x,
                gap_y=gap_y,
                panel_width=panel_width,
                panel_height=panel_height,
                visual_origin_x=visual_origin_x,
                visual_origin_y=visual_origin_y,
                fixed_offset_x=fixed_offset_x,
                fixed_offset_y=fixed_offset_y
            )

            # --- INTERACTIVITY: CLICK TO ZOOM ---
            selection = st.plotly_chart(contour_fig, use_container_width=True, on_select="rerun", selection_mode="points")

            if selection and selection.selection and selection.selection["points"]:
                if selected_quadrant == "All":
                    point = selection.selection["points"][0]
                    click_x = point.get("x")
                    click_y = point.get("y")

                    if click_x is not None and click_y is not None:
                        clicked_quad = None
                        is_left = (click_x >= offset_x) and (click_x < offset_x + quad_width)
                        is_right = (click_x > offset_x + quad_width + gap_size)

                        is_bottom = (click_y >= offset_y) and (click_y < offset_y + quad_height)
                        is_top = (click_y > offset_y + quad_height + gap_size)

                        if is_left and is_bottom: clicked_quad = "Q1"
                        elif is_right and is_bottom: clicked_quad = "Q2"
                        elif is_left and is_top: clicked_quad = "Q3"
                        elif is_right and is_top: clicked_quad = "Q4"

                        if clicked_quad:
                            st.session_state["analysis_quadrant_selection"] = clicked_quad
                            st.rerun()

        else:
            st.warning("No data available for the selected filters.")
