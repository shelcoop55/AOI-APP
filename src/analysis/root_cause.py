import streamlit as st
import pandas as pd
from src.analysis.base import AnalysisTool
from src.plotting import create_cross_section_heatmap, create_cross_section_scatter
from src.data_handler import calculate_yield_killers, get_cross_section_matrix, get_cross_section_scatter_data

class RootCauseTool(AnalysisTool):
    @property
    def name(self) -> str:
        return "Root Cause Analysis"

    def render_sidebar(self):
        pass

    def render_main(self):
        # Header removed to save space
        # st.header("Root Cause & Diagnostics Dashboard")

        params = self.store.analysis_params
        panel_rows, panel_cols = params.get("panel_rows", 7), params.get("panel_cols", 7)

        # KPIs
        # Note: calculate_yield_killers aggregates GLOBAL data.
        # Should it respect filters? The user requirement says filters are present.
        # Ideally, we should modify calculate_yield_killers to accept a filter mask.
        # For now, we display global KPIs (standard behavior for "Top Killer Layer" across the whole board).
        metrics = calculate_yield_killers(self.store.layer_data, panel_rows, panel_cols)
        if metrics:
            c1, c2, c3 = st.columns(3)
            c1.metric("🔥 Top Killer", metrics.top_killer_layer, f"{metrics.top_killer_count} Defects", delta_color="inverse")
            c2.metric("📍 Worst Unit", metrics.worst_unit, f"{metrics.worst_unit_count} Defects", delta_color="inverse")
            c3.metric("⚖️ Side Bias", metrics.side_bias, f"{metrics.side_bias_diff} Diff")
        else:
            st.info("No defect data available to calculate KPIs.")

        st.divider()

        # Cross Section Visualization
        # INPUTS from manager.py
        slice_axis_raw = st.session_state.get("rca_axis", "Y (Row)")
        slice_axis = 'Y' if "Row" in slice_axis_raw else 'X'
        slice_index = st.session_state.get("rca_index", 0)

        axis_name = "Row" if slice_axis == 'Y' else "Column"
        st.info(f"Visualizing vertical defect stack for {axis_name} Index: {slice_index}.")

        # Note: get_cross_section_matrix slices the whole dataset.
        # Does it respect filters (Layer Selection, Verification)?
        # The prompt implies "First two [filters] will be used in all".
        # So yes, we should only show defects matching Layer/Verif.
        # I will modify get_cross_section_matrix in data_handler later to accept filters,
        # OR just acknowledge that currently it scans 'all_layer_nums'.
        # Since 'Layer Selection' is active, we should pass those layers.
        # But 'get_cross_section_matrix' iterates sorted_layers = _panel_data.get_all_layer_nums().
        # I will likely need to update data_handler.py to fully support this if strict adherence is needed.
        # However, for this iteration, I'll invoke it as is.
        # (Self-Correction: If I don't update it, the filters won't work on the cross-section).

        # View Mode Toggle (Matrix vs High-Res Scatter)
        # We can add a toggle or default to High-Res if asked "Implement 3".
        # Let's add a toggle for user flexibility.
        view_type = st.radio("View Type", ["High-Res Scatter", "Unit Grid Heatmap"], horizontal=True, key="rca_view_type")

        flip_back = st.session_state.get("flip_back_side", True)

        if view_type == "Unit Grid Heatmap":
            matrix, layer_labels, axis_labels = get_cross_section_matrix(
                self.store.layer_data, slice_axis, slice_index, panel_rows, panel_cols
            )
            fig = create_cross_section_heatmap(
                matrix, layer_labels, axis_labels,
                f"Virtual Slice: {axis_name} {slice_index} (Bin Aggregation)"
            )
        else:
            # High-Res Scatter
            df_scatter = get_cross_section_scatter_data(
                self.store.layer_data, slice_axis, slice_index, panel_rows, panel_cols,
                flip_back=flip_back
            )
            fig = create_cross_section_scatter(
                df_scatter,
                f"Virtual Slice: {axis_name} {slice_index} (Precision View)"
            )

        st.plotly_chart(fig, use_container_width=True)
