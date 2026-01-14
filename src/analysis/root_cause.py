import streamlit as st
import pandas as pd
from src.analysis.base import AnalysisTool
from src.plotting import create_cross_section_heatmap
from src.data_handler import calculate_yield_killers, get_cross_section_matrix

class RootCauseTool(AnalysisTool):
    @property
    def name(self) -> str:
        return "Root Cause Analysis"

    def render_sidebar(self):
        with st.expander("Cross-Section Controls", expanded=True):
            st.markdown("Virtual Z-Axis Slicer")

            params = self.store.analysis_params
            panel_rows = params.get("panel_rows", 7)
            panel_cols = params.get("panel_cols", 7)

            max_x = (panel_cols * 2) - 1
            max_y = (panel_rows * 2) - 1

            # Persistent State
            if 'rc_slice_axis' not in st.session_state: st.session_state.rc_slice_axis = 'Y'
            if 'rc_slice_index' not in st.session_state: st.session_state.rc_slice_index = 0

            # Slice Axis Control
            axis_options = ["By Row (Y)", "By Column (X)"]
            current_index = 0 if st.session_state.rc_slice_axis == 'Y' else 1
            selected_axis = st.radio("Slice Axis", axis_options, index=current_index)

            # Update State
            new_axis = 'Y' if "Row" in selected_axis else 'X'
            if new_axis != st.session_state.rc_slice_axis:
                st.session_state.rc_slice_axis = new_axis
                st.session_state.rc_slice_index = 0 # Reset index on axis switch

            # Slice Index Control
            limit = max_y if st.session_state.rc_slice_axis == 'Y' else max_x
            label_char = "Y" if st.session_state.rc_slice_axis == 'Y' else "X"

            st.session_state.rc_slice_index = st.slider(
                f"Select {label_char} Index",
                min_value=0,
                max_value=limit,
                value=min(st.session_state.rc_slice_index, limit)
            )

    def render_main(self):
        st.header("Root Cause & Diagnostics Dashboard")

        params = self.store.analysis_params
        panel_rows, panel_cols = params.get("panel_rows", 7), params.get("panel_cols", 7)

        metrics = calculate_yield_killers(self.store.layer_data, panel_rows, panel_cols)
        if metrics:
            c1, c2, c3 = st.columns(3)
            c1.metric("🔥 Top Killer", metrics.top_killer_layer, f"{metrics.top_killer_count} Defects", delta_color="inverse")
            c2.metric("📍 Worst Unit", metrics.worst_unit, f"{metrics.worst_unit_count} Defects", delta_color="inverse")
            c3.metric("⚖️ Side Bias", metrics.side_bias, f"{metrics.side_bias_diff} Diff")
        else:
            st.info("No defect data available to calculate KPIs.")

        st.divider()

        slice_axis = st.session_state.rc_slice_axis
        slice_index = st.session_state.rc_slice_index

        axis_name = "Row" if slice_axis == 'Y' else "Column"
        st.info(f"Visualizing vertical defect stack for {axis_name} Index: {slice_index}.")

        matrix, layer_labels, axis_labels = get_cross_section_matrix(
            self.store.layer_data, slice_axis, slice_index, panel_rows, panel_cols
        )

        fig = create_cross_section_heatmap(
            matrix, layer_labels, axis_labels,
            f"Virtual Slice: {axis_name} {slice_index}"
        )
        st.plotly_chart(fig, use_container_width=True)
