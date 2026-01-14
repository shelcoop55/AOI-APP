import streamlit as st
import pandas as pd
from src.analysis.base import AnalysisTool
from src.plotting import create_density_contour_map

class HeatmapTool(AnalysisTool):
    @property
    def name(self) -> str:
        return "Heatmap Analysis"

    def render_sidebar(self):
        st.markdown("**Heatmap Settings**")

        available_options = self._get_available_layer_options()
        option_map = {opt[0]: opt[1] for opt in available_options}

        sel_heatmap = st.multiselect("Select Data", options=list(option_map.keys()), default=list(option_map.keys()))
        st.session_state.heatmap_keys = [option_map[k] for k in sel_heatmap]

        # UI State
        if 'hm_smoothing' not in st.session_state: st.session_state.hm_smoothing = 30
        if 'hm_sat' not in st.session_state: st.session_state.hm_sat = 0

        st.session_state.hm_smoothing = st.slider("Smoothing", min_value=10, max_value=100, value=st.session_state.hm_smoothing)
        st.session_state.hm_sat = st.slider("Sat. Cap", min_value=0, max_value=100, value=st.session_state.hm_sat)

    def render_main(self):
        st.header("Heatmap Analysis")
        st.info("Visualizing smoothed defect density across selected layers.")

        params = self.store.analysis_params
        panel_rows, panel_cols = params.get("panel_rows", 7), params.get("panel_cols", 7)

        selected_keys = st.session_state.get('heatmap_keys', [])
        if not selected_keys:
             # Fallback to all if user unselects everything or init
             available_options = self._get_available_layer_options()
             selected_keys = [opt[1] for opt in available_options]

        combined_heatmap_df = pd.DataFrame()
        dfs_to_concat = []
        for layer_num, side in selected_keys:
            layer = self.store.layer_data.get_layer(layer_num, side)
            if layer and not layer.data.empty:
                dfs_to_concat.append(layer.data)

        if dfs_to_concat:
            combined_heatmap_df = pd.concat(dfs_to_concat, ignore_index=True)

        if not combined_heatmap_df.empty:
            contour_fig = create_density_contour_map(
                combined_heatmap_df, panel_rows, panel_cols,
                show_points=False,
                smoothing_factor=st.session_state.hm_smoothing,
                saturation_cap=st.session_state.hm_sat,
                show_grid=False
            )
            st.plotly_chart(contour_fig, use_container_width=True)
        else:
            st.warning("No data available for the selected layers.")

    def _get_available_layer_options(self):
        options = []
        for layer_num in self.store.layer_data.get_all_layer_nums():
            for side in self.store.layer_data.get_sides_for_layer(layer_num):
                side_label = "Front" if side == 'F' else "Back"
                label = f"Layer {layer_num} ({side_label})"
                options.append((label, (layer_num, side)))
        return options
