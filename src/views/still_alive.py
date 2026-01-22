import streamlit as st
import pandas as pd
import numpy as np
from src.state import SessionStore
from src.plotting import create_still_alive_figure
from src.analysis.calculations import get_true_defect_coordinates, FilterContext
from src.config import GAP_SIZE, PANEL_WIDTH, PANEL_HEIGHT

def render_still_alive_main(store: SessionStore, theme_config=None):
    """Renders the Main Content for the Still Alive view."""
    params = store.analysis_params
    panel_rows = params.get("panel_rows", 7)
    panel_cols = params.get("panel_cols", 7)

    # --- Filter Logic Adaptation ---
    all_layers = store.layer_data.get_all_layer_nums()
    selected_layers = store.multi_layer_selection if store.multi_layer_selection else all_layers
    excluded_layers = list(set(all_layers) - set(selected_layers))

    side_pills = st.session_state.get("analysis_side_pills", ["Front", "Back"])
    included_sides = []
    if "Front" in side_pills: included_sides.append('F')
    if "Back" in side_pills: included_sides.append('B')

    full_df = store.layer_data.get_combined_dataframe()
    all_verifs = []
    if not full_df.empty and 'Verification' in full_df.columns:
        all_verifs = sorted(full_df['Verification'].dropna().unique().tolist())

    selected_verifs = st.session_state.get('multi_verification_selection', all_verifs)
    excluded_defects = list(set(all_verifs) - set(selected_verifs))

    context = FilterContext(
        excluded_layers=excluded_layers,
        excluded_defect_types=excluded_defects,
        included_sides=included_sides
    )

    true_defect_data = get_true_defect_coordinates(
        store.layer_data,
        context
    )

    map_col, summary_col = st.columns([3, 1])

    with map_col:
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

        fig = create_still_alive_figure(
            panel_rows, panel_cols, true_defect_data,
            offset_x=offset_x, offset_y=offset_y,
            gap_x=gap_x, gap_y=gap_y,
            panel_width=p_width, panel_height=p_height,
            theme_config=theme_config,
            visual_origin_x=visual_origin_x,
            visual_origin_y=visual_origin_y,
            fixed_offset_x=fixed_offset_x,
            fixed_offset_y=fixed_offset_y
        )
        st.plotly_chart(fig, use_container_width=True)

    with summary_col:
        total_cells = (panel_rows * 2) * (panel_cols * 2)
        defective_cell_count = len(true_defect_data)
        alive_cell_count = total_cells - defective_cell_count
        yield_percentage = (alive_cell_count / total_cells) * 100 if total_cells > 0 else 0

        st.subheader("Yield Summary")
        st.metric("Panel Yield", f"{yield_percentage:.2f}%")
        st.metric("Surviving Cells", f"{alive_cell_count:,} / {total_cells:,}")
        st.metric("Defective Cells", f"{defective_cell_count:,}")

        st.divider()

        # --- Vectorized Zonal Yield Analysis ---
        st.subheader("Zonal Yield")

        total_rows_grid = panel_rows * 2
        total_cols_grid = panel_cols * 2

        # Create grid of indices (Note: meshgrid ij indexing gives row, col)
        yy, xx = np.meshgrid(np.arange(total_rows_grid), np.arange(total_cols_grid), indexing='ij')

        # Calculate distance to nearest edge
        # Columns (xx) are 0..total_cols-1
        dist_x = np.minimum(xx, total_cols_grid - 1 - xx)
        dist_y = np.minimum(yy, total_rows_grid - 1 - yy)
        ring_index = np.minimum(dist_x, dist_y)

        # Define Zones
        # Ring 0
        mask_edge = (ring_index == 0)
        # Ring 1, 2
        mask_middle = (ring_index >= 1) & (ring_index <= 2)
        # Ring > 2
        mask_center = (ring_index > 2)

        # Create Dead Mask
        is_dead_grid = np.zeros((total_rows_grid, total_cols_grid), dtype=bool)
        if true_defect_data:
            # Keys are (col, row) -> (x, y)
            dead_coords = np.array(list(true_defect_data.keys()))
            if dead_coords.size > 0:
                # Assign True. dead_coords[:, 1] is Y (row), [:, 0] is X (col)
                is_dead_grid[dead_coords[:, 1], dead_coords[:, 0]] = True

        def calc_yield(mask):
            total = np.sum(mask)
            if total == 0: return 0, 0
            dead = np.sum(is_dead_grid & mask)
            alive = total - dead
            return alive, total

        center_alive, center_total = calc_yield(mask_center)
        middle_alive, middle_total = calc_yield(mask_middle)
        edge_alive, edge_total = calc_yield(mask_edge)

        c_yield = (center_alive / center_total * 100) if center_total > 0 else 0
        m_yield = (middle_alive / middle_total * 100) if middle_total > 0 else 0
        e_yield = (edge_alive / edge_total * 100) if edge_total > 0 else 0

        st.metric("Center Yield", f"{c_yield:.1f}%", help=f"Inner Core (Ring 4+). Total Units: {center_total}")
        st.metric("Middle Yield", f"{m_yield:.1f}%", help=f"Rings 2 & 3. Total Units: {middle_total}")
        st.metric("Edge Yield", f"{e_yield:.1f}%", help=f"Outer Ring (Ring 1). Total Units: {edge_total}")

        st.divider()

        # --- Pick List Download (Optimized Generation) ---
        # Generate DataFrame only when requested or lazily?
        # Streamlit download button requires data upfront usually.
        # But we can generate the string efficiently.

        # Vectorized generation of alive units
        # Get indices where is_dead_grid is False
        alive_rows, alive_cols = np.where(~is_dead_grid)
        # We need physical x (cols) and unit index y (rows)
        # Create DF directly

        if len(alive_rows) > 0:
            df_alive = pd.DataFrame({
                'PHYSICAL_X': alive_cols,
                'UNIT_INDEX_Y': alive_rows
            })

            from src.utils import generate_standard_filename
            target_layer = store.multi_layer_selection[0] if len(store.multi_layer_selection) == 1 else None
            filename = generate_standard_filename(
                prefix="Pick_List",
                selected_layer=target_layer,
                layer_data=store.layer_data,
                analysis_params=store.analysis_params,
                extension="csv"
            )

            st.download_button(
                "📥 Download Pick List",
                data=df_alive.to_csv(index=False).encode('utf-8'),
                file_name=filename,
                mime="text/csv",
                help="CSV list of coordinate pairs (Physical X, Y) for good units."
            )
