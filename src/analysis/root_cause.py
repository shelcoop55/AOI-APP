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
        st.markdown("**Cross-Section Settings**")

        params = self.store.analysis_params
        panel_rows = params.get("panel_rows", 7)
        panel_cols = params.get("panel_cols", 7)

        max_x = (panel_cols * 2) - 1
        max_y = (panel_rows * 2) - 1

        st.caption("Region of Interest (ROI)")

        # We need persistant state for sliders
        if 'rc_x_range' not in st.session_state: st.session_state.rc_x_range = (0, max_x)
        if 'rc_y_range' not in st.session_state: st.session_state.rc_y_range = (0, max_y)
        if 'rc_slice_axis' not in st.session_state: st.session_state.rc_slice_axis = 'Y'

        st.session_state.rc_x_range = st.slider("X Range (Cols)", min_value=0, max_value=max_x, value=st.session_state.rc_x_range)
        st.session_state.rc_y_range = st.slider("Y Range (Rows)", min_value=0, max_value=max_y, value=st.session_state.rc_y_range)

        st.caption("Projection Axis")
        # Radio returns label, we map back
        axis_label = st.radio("View Projection", ["By Row (onto X)", "By Col (onto Y)"], index=0 if st.session_state.rc_slice_axis == 'Y' else 1)
        st.session_state.rc_slice_axis = 'Y' if "Row" in axis_label else 'X'

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

        x_range = st.session_state.rc_x_range
        y_range = st.session_state.rc_y_range
        slice_axis = st.session_state.rc_slice_axis

        proj_desc = "X-Axis" if slice_axis == 'Y' else "Y-Axis"
        st.info(f"Visualizing vertical defect propagation within ROI (X: {x_range}, Y: {y_range}). Projecting onto {proj_desc}.")

        matrix, layer_labels, axis_labels = get_cross_section_matrix(
            self.store.layer_data, slice_axis, x_range, y_range, panel_rows, panel_cols
        )

        fig = create_cross_section_heatmap(
            matrix, layer_labels, axis_labels,
            f"ROI Slice: X{x_range} / Y{y_range} (View: {slice_axis})"
        )
        st.plotly_chart(fig, use_container_width=True)
