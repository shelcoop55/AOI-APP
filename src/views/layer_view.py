import streamlit as st
import pandas as pd
from src.state import SessionStore
from src.enums import ViewMode, Quadrant
from src.plotting import create_defect_map_figure, create_pareto_figure

def render_layer_view(store: SessionStore, view_mode: str, quadrant_selection: str, verification_selection: str):
    params = store.analysis_params
    panel_rows, panel_cols = params.get("panel_rows", 7), params.get("panel_cols", 7)
    lot_number = params.get("lot_number")

    selected_layer_num = store.selected_layer
    if selected_layer_num:
        layer_info = store.layer_data.get(selected_layer_num, {})
        side_df = layer_info.get(store.selected_side)

        if side_df is not None and not side_df.empty:
            filtered_df = side_df[side_df['Verification'] == verification_selection] if verification_selection != 'All' else side_df
            display_df = filtered_df[filtered_df['QUADRANT'] == quadrant_selection] if quadrant_selection != Quadrant.ALL.value else filtered_df

            if view_mode == ViewMode.DEFECT.value:
                fig = create_defect_map_figure(display_df, panel_rows, panel_cols, quadrant_selection, lot_number)
                st.plotly_chart(fig, use_container_width=True)
            elif view_mode == ViewMode.PARETO.value:
                fig = create_pareto_figure(display_df, quadrant_selection)
                st.plotly_chart(fig, use_container_width=True)
            elif view_mode == ViewMode.SUMMARY.value:
                    st.info("Summary View loaded.")
