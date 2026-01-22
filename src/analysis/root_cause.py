import streamlit as st
from src.analysis.base import AnalysisTool
from src.plotting import create_cross_section_heatmap
from src.analysis.calculations import calculate_yield_killers, get_cross_section_matrix, FilterContext

class RootCauseTool(AnalysisTool):
    @property
    def name(self) -> str:
        return "Root Cause Analysis"

    def render_sidebar(self):
        pass

    def render_main(self):
        params = self.store.analysis_params
        panel_rows, panel_cols = params.get("panel_rows", 7), params.get("panel_cols", 7)

        # Build Filter Context
        selected_layer_nums = self.store.multi_layer_selection or self.store.layer_data.get_all_layer_nums()
        side_selection = st.session_state.get("analysis_side_pills", ["Front", "Back"])
        selected_verifs = st.session_state.get("multi_verification_selection", [])
        selected_quadrant = st.session_state.get("analysis_quadrant_selection", "All")

        sides_mapped = []
        if "Front" in side_selection: sides_mapped.append('F')
        if "Back" in side_selection: sides_mapped.append('B')

        context = FilterContext(
            selected_layers=selected_layer_nums,
            selected_sides=sides_mapped,
            verification_filter=selected_verifs,
            quadrant_filter=selected_quadrant
        )

        # KPIs (Filtered)
        metrics = calculate_yield_killers(self.store.layer_data, panel_rows, panel_cols, context)
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

        matrix, layer_labels, axis_labels = get_cross_section_matrix(
            self.store.layer_data, slice_axis, slice_index, panel_rows, panel_cols, context
        )

        fig = create_cross_section_heatmap(
            matrix, layer_labels, axis_labels,
            f"Virtual Slice: {axis_name} {slice_index}"
        )
        st.plotly_chart(fig, use_container_width=True)
