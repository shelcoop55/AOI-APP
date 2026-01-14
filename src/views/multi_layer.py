import streamlit as st
import pandas as pd
from src.state import SessionStore
from src.data_handler import prepare_multi_layer_data
from src.plotting import create_multi_layer_defect_map

def render_multi_layer_view(store: SessionStore, selected_layers: list, selected_sides: list):
    st.header("Multi-Layer Combined Defect Map")
    st.info("Visualizing 'True Defects' from selected layers. Colors indicate the source layer.")

    params = store.analysis_params
    panel_rows, panel_cols = params.get("panel_rows", 7), params.get("panel_cols", 7)

    combined_df = prepare_multi_layer_data(store.layer_data)

    if not combined_df.empty:
        if selected_layers:
            combined_df = combined_df[combined_df['LAYER_NUM'].isin(selected_layers)]
        else: combined_df = pd.DataFrame()

        if not combined_df.empty and selected_sides:
            combined_df = combined_df[combined_df['SIDE'].isin(selected_sides)]
        elif not selected_sides: combined_df = pd.DataFrame()

    if not combined_df.empty:
        fig = create_multi_layer_defect_map(combined_df, panel_rows, panel_cols)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No data matches current filters.")
