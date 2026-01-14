import streamlit as st
import pandas as pd
from src.analysis.base import AnalysisTool
from src.enums import ViewMode
from src.plotting import create_stress_heatmap, create_delta_heatmap
from src.data_handler import aggregate_stress_data

class StressMapTool(AnalysisTool):
    @property
    def name(self) -> str:
        return "Stress Map"

    def render_sidebar(self):
        st.markdown("**Stress Map Settings**")

        # Local state for mode (could be in store if persistence needed, keeping local for now)
        if 'stress_mode' not in st.session_state:
            st.session_state.stress_mode = "Cumulative"

        mode = st.radio("Analysis Mode", ["Cumulative", "Delta (Difference)"], key="stress_mode_radio")
        st.session_state.stress_mode = mode

        available_options = self._get_available_layer_options()
        option_map = {opt[0]: opt[1] for opt in available_options} # Label -> (Layer, Side)

        if mode == "Delta (Difference)":
            st.markdown("**Group A - Group B**")
            sel_a = st.multiselect("Group A (Ref)", options=list(option_map.keys()), default=list(option_map.keys()))
            sel_b = st.multiselect("Group B (Comp)", options=list(option_map.keys()), default=[])

            # Store in session state for render_main
            st.session_state.delta_group_a = [option_map[k] for k in sel_a]
            st.session_state.delta_group_b = [option_map[k] for k in sel_b]
        else:
            sel_cumulative = st.multiselect("Select Data", options=list(option_map.keys()), default=list(option_map.keys()))
            st.session_state.selected_keys_stress = [option_map[k] for k in sel_cumulative]

    def render_main(self):
        st.header("Cumulative Stress Map Analysis")
        st.info("Aggregates defects into a master grid. Includes Back-Side alignment.")

        params = self.store.analysis_params
        panel_rows, panel_cols = params.get("panel_rows", 7), params.get("panel_cols", 7)
        mode = st.session_state.get('stress_mode', 'Cumulative')

        if mode == "Cumulative":
            keys = st.session_state.get('selected_keys_stress', [])
            stress_data = aggregate_stress_data(self.store.layer_data, keys, panel_rows, panel_cols)
            fig = create_stress_heatmap(stress_data, panel_rows, panel_cols)
        else: # Delta
            keys_a = st.session_state.get('delta_group_a', [])
            keys_b = st.session_state.get('delta_group_b', [])
            stress_data_a = aggregate_stress_data(self.store.layer_data, keys_a, panel_rows, panel_cols)
            stress_data_b = aggregate_stress_data(self.store.layer_data, keys_b, panel_rows, panel_cols)
            fig = create_delta_heatmap(stress_data_a, stress_data_b, panel_rows, panel_cols)

        st.plotly_chart(fig, use_container_width=True)

    def _get_available_layer_options(self):
        """Helper to generate label -> key mapping from store data."""
        options = []
        for layer_num in self.store.layer_data.get_all_layer_nums():
            for side in self.store.layer_data.get_sides_for_layer(layer_num):
                side_label = "Front" if side == 'F' else "Back"
                label = f"Layer {layer_num} ({side_label})"
                options.append((label, (layer_num, side)))
        return options
