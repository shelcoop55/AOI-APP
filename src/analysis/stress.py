import streamlit as st
from src.analysis.base import AnalysisTool
from src.plotting import create_stress_heatmap, create_delta_heatmap
from src.analysis.calculations import aggregate_stress_data, FilterContext
from src.config import GAP_SIZE, PANEL_WIDTH, PANEL_HEIGHT

class StressMapTool(AnalysisTool):
    @property
    def name(self) -> str:
        return "Stress Map"

    def render_sidebar(self):
        pass

    def render_main(self):
        params = self.store.analysis_params
        panel_rows, panel_cols = params.get("panel_rows", 7), params.get("panel_cols", 7)
        panel_uid = getattr(self.store.layer_data, "id", "static")

        # READ INPUTS
        mode_new = st.session_state.get('stress_map_mode', 'Cumulative')
        selected_layer_nums = self.store.multi_layer_selection or self.store.layer_data.get_all_layer_nums()
        side_selection = st.session_state.get("analysis_side_pills", ["Front", "Back"])
        selected_verifs = st.session_state.get("multi_verification_selection", [])
        view_mode = "Continuous"
        selected_quadrant = st.session_state.get("analysis_quadrant_selection", "All")

        # Map UI Selection to codes
        sides_mapped = []
        if "Front" in side_selection: sides_mapped.append('F')
        if "Back" in side_selection: sides_mapped.append('B')

        # Layout Params
        offset_x = params.get("offset_x", 0.0)
        offset_y = params.get("offset_y", 0.0)
        gap_x = params.get("gap_x", GAP_SIZE)
        gap_y = params.get("gap_y", GAP_SIZE)
        p_width = params.get("panel_width", PANEL_WIDTH)
        p_height = params.get("panel_height", PANEL_HEIGHT)
        visual_origin_x = params.get("visual_origin_x", 0.0)
        visual_origin_y = params.get("visual_origin_y", 0.0)
        fixed_offset_x = params.get("fixed_offset_x", 0.0)
        fixed_offset_y = params.get("fixed_offset_y", 0.0)

        fig = None

        if mode_new == "Cumulative":
             context = FilterContext(
                 selected_layers=selected_layer_nums,
                 selected_sides=sides_mapped,
                 verification_filter=selected_verifs,
                 quadrant_filter=selected_quadrant
             )
             stress_data = aggregate_stress_data(
                self.store.layer_data, context, panel_rows, panel_cols, panel_uid
            )
             fig = create_stress_heatmap(
                 stress_data, panel_rows, panel_cols, view_mode=view_mode,
                 offset_x=offset_x, offset_y=offset_y, gap_x=gap_x, gap_y=gap_y,
                 panel_width=p_width, panel_height=p_height,
                 visual_origin_x=visual_origin_x, visual_origin_y=visual_origin_y,
                 fixed_offset_x=fixed_offset_x, fixed_offset_y=fixed_offset_y
             )

        elif mode_new == "Delta Difference":
            st.info("Delta Difference Mode: Calculating (Front Side - Back Side) for selected layers.")

            # Context A (Front, if selected)
            sides_f = [s for s in sides_mapped if s == 'F']
            context_f = FilterContext(
                 selected_layers=selected_layer_nums,
                 selected_sides=sides_f,
                 verification_filter=selected_verifs,
                 quadrant_filter=selected_quadrant
            )

            # Context B (Back, if selected)
            sides_b = [s for s in sides_mapped if s == 'B']
            context_b = FilterContext(
                 selected_layers=selected_layer_nums,
                 selected_sides=sides_b,
                 verification_filter=selected_verifs,
                 quadrant_filter=selected_quadrant
            )

            stress_data_a = aggregate_stress_data(
                self.store.layer_data, context_f, panel_rows, panel_cols, panel_uid
            )
            stress_data_b = aggregate_stress_data(
                self.store.layer_data, context_b, panel_rows, panel_cols, panel_uid
            )

            fig = create_delta_heatmap(
                stress_data_a, stress_data_b, panel_rows, panel_cols, view_mode=view_mode,
                offset_x=offset_x, offset_y=offset_y, gap_x=gap_x, gap_y=gap_y,
                panel_width=p_width, panel_height=p_height,
                visual_origin_x=visual_origin_x, visual_origin_y=visual_origin_y,
                fixed_offset_x=fixed_offset_x, fixed_offset_y=fixed_offset_y
            )

        if fig:
            st.plotly_chart(fig, use_container_width=True)
