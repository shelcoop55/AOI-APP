import streamlit as st
from src.state import SessionStore
from src.plotting import create_still_alive_figure
from src.data_handler import get_true_defect_coordinates

def render_still_alive_view(store: SessionStore):
    params = store.analysis_params
    panel_rows = params.get("panel_rows", 7)
    panel_cols = params.get("panel_cols", 7)

    st.header("Still Alive Panel Yield Map")
    map_col, summary_col = st.columns([2.5, 1])
    with map_col:
        true_defect_coords = get_true_defect_coordinates(store.layer_data)
        fig = create_still_alive_figure(panel_rows, panel_cols, true_defect_coords)
        st.plotly_chart(fig, use_container_width=True)

    with summary_col:
        total_cells = (panel_rows * 2) * (panel_cols * 2)
        defective_cell_count = len(true_defect_coords)
        alive_cell_count = total_cells - defective_cell_count
        yield_percentage = (alive_cell_count / total_cells) * 100 if total_cells > 0 else 0
        st.subheader("Yield Summary")
        st.metric("Panel Yield", f"{yield_percentage:.2f}%")
        st.metric("Surviving Cells", f"{alive_cell_count:,} / {total_cells:,}")
        st.metric("Defective Cells", f"{defective_cell_count:,}")
