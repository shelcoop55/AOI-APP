import streamlit as st
from src.analysis.base import AnalysisTool
from src.plotting import create_defect_sunburst, create_defect_sankey

class InsightsTool(AnalysisTool):
    @property
    def name(self) -> str:
        return "Insights & Sankey"

    def render_sidebar(self):
        st.info("No specific settings for this view. It analyzes the currently selected single layer (from state).")

    def render_main(self):
        st.header("Insights & Sankey View")

        layer_num = self.store.selected_layer
        side = self.store.selected_side

        layer = self.store.layer_data.get_layer(layer_num, side)

        if layer and not layer.data.empty:
            display_df = layer.data
            st.caption(f"Analyzing: Layer {layer_num} - {side}")
            st.plotly_chart(create_defect_sunburst(display_df), use_container_width=True)
            sankey = create_defect_sankey(display_df)
            if sankey: st.plotly_chart(sankey, use_container_width=True)
        else:
            st.warning("No data available or no layer selected.")
