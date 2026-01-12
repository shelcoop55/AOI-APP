"""
Plotting and Visualization Module.
This version draws a true-to-scale simulation of a 510x510mm physical panel.
UPDATED: Now includes an outer border frame and has been refactored for clarity.
"""
import plotly.graph_objects as go
import pandas as pd
from typing import List, Dict, Any, Set, Tuple, Optional

from src.config import (
    PANEL_COLOR, GRID_COLOR, defect_style_map, TEXT_COLOR, BACKGROUND_COLOR, PLOT_AREA_COLOR,
    PANEL_WIDTH, PANEL_HEIGHT, GAP_SIZE,
    ALIVE_CELL_COLOR, DEFECTIVE_CELL_COLOR, FALLBACK_COLORS, SAFE_VERIFICATION_VALUES,
    VERIFICATION_COLOR_SAFE, VERIFICATION_COLOR_DEFECT
)
from src.data_handler import QUADRANT_WIDTH, QUADRANT_HEIGHT
from src.documentation import VERIFICATION_DESCRIPTIONS
from src.enums import Quadrant

# ==============================================================================
# --- Private Helper Functions for Grid Creation ---
# ==============================================================================

def _draw_border_and_gaps() -> List[Dict[str, Any]]:
    """Creates the shapes for the outer border and inner gaps of the panel."""
    shapes = []
    gap_color = '#A8652A'
    total_width_with_gap = PANEL_WIDTH + GAP_SIZE
    total_height_with_gap = PANEL_HEIGHT + GAP_SIZE

    # Outer border frame
    shapes.extend([
        dict(type="rect", x0=0, y0=total_height_with_gap, x1=total_width_with_gap, y1=total_height_with_gap + GAP_SIZE, fillcolor=gap_color, line_width=0, layer='below'),
        dict(type="rect", x0=0, y0=-GAP_SIZE, x1=total_width_with_gap, y1=0, fillcolor=gap_color, line_width=0, layer='below'),
        dict(type="rect", x0=-GAP_SIZE, y0=-GAP_SIZE, x1=0, y1=total_height_with_gap + GAP_SIZE, fillcolor=gap_color, line_width=0, layer='below'),
        dict(type="rect", x0=total_width_with_gap, y0=-GAP_SIZE, x1=total_width_with_gap + GAP_SIZE, y1=total_height_with_gap + GAP_SIZE, fillcolor=gap_color, line_width=0, layer='below')
    ])

    # Inner gaps
    shapes.extend([
        dict(type="rect", x0=QUADRANT_WIDTH, y0=0, x1=QUADRANT_WIDTH + GAP_SIZE, y1=total_height_with_gap, fillcolor=gap_color, line_width=0, layer='below'),
        dict(type="rect", x0=0, y0=QUADRANT_HEIGHT, x1=total_width_with_gap, y1=QUADRANT_HEIGHT + GAP_SIZE, fillcolor=gap_color, line_width=0, layer='below')
    ])
    return shapes

def _draw_quadrant_grids(origins_to_draw: Dict, panel_rows: int, panel_cols: int, fill: bool = True) -> List[Dict[str, Any]]:
    """Creates the shapes for the quadrant outlines and their internal grid lines."""
    shapes = []
    cell_width = QUADRANT_WIDTH / panel_cols
    cell_height = QUADRANT_HEIGHT / panel_rows

    for x_start, y_start in origins_to_draw.values():
        if fill:
            shapes.append(dict(
                type="rect", x0=x_start, y0=y_start, x1=x_start + QUADRANT_WIDTH, y1=y_start + QUADRANT_HEIGHT,
                line=dict(color=GRID_COLOR, width=2), fillcolor=PANEL_COLOR, layer='below'
            ))
        for i in range(1, panel_cols):
            line_x = x_start + (i * cell_width)
            shapes.append(dict(type="line", x0=line_x, y0=y_start, x1=line_x, y1=y_start + QUADRANT_HEIGHT, line=dict(color=GRID_COLOR, width=1, dash='solid'), opacity=0.5, layer='below'))
        for i in range(1, panel_rows):
            line_y = y_start + (i * cell_height)
            shapes.append(dict(type="line", x0=x_start, y0=line_y, x1=x_start + QUADRANT_WIDTH, y1=line_y, line=dict(color=GRID_COLOR, width=1, dash='solid'), opacity=0.5, layer='below'))
            
    return shapes

# ==============================================================================
# --- Public API Functions ---
# ==============================================================================

def create_grid_shapes(panel_rows: int, panel_cols: int, quadrant: str = 'All', fill: bool = True) -> List[Dict[str, Any]]:
    """
    Creates the visual shapes for the panel grid in a fixed 510x510mm coordinate system.
    """
    all_origins = {
        'Q1': (0, 0), 'Q2': (QUADRANT_WIDTH + GAP_SIZE, 0),
        'Q3': (0, QUADRANT_HEIGHT + GAP_SIZE), 'Q4': (QUADRANT_WIDTH + GAP_SIZE, QUADRANT_HEIGHT + GAP_SIZE)
    }
    origins_to_draw = all_origins if quadrant == 'All' else {quadrant: all_origins[quadrant]}
    shapes = []
    if quadrant == 'All':
        shapes.extend(_draw_border_and_gaps())
    shapes.extend(_draw_quadrant_grids(origins_to_draw, panel_rows, panel_cols, fill=fill))
    return shapes

def create_defect_traces(df: pd.DataFrame) -> List[go.Scatter]:
    """
    Generates scatter plot traces.
    """
    traces = []
    if df.empty: return traces

    # Check the flag. If mixed (some rows T, some F), default to True if any are True
    has_verification_data = df['HAS_VERIFICATION_DATA'].any() if 'HAS_VERIFICATION_DATA' in df.columns else False

    # Determine what column to group by
    group_col = 'Verification' if has_verification_data else 'DEFECT_TYPE'

    unique_groups = df[group_col].unique()

    # --- COLOR MAPPING ---
    local_style_map = {}

    if group_col == 'DEFECT_TYPE':
        # Use the standard defect style map + fallback
        local_style_map = defect_style_map.copy()
        fallback_index = 0
        for dtype in unique_groups:
            if dtype not in local_style_map:
                color = FALLBACK_COLORS[fallback_index % len(FALLBACK_COLORS)]
                local_style_map[dtype] = color
                fallback_index += 1
    else:
        # For Verification codes (CU22, N, etc.), generate a map on the fly
        fallback_index = 0
        for code in unique_groups:
            color = FALLBACK_COLORS[fallback_index % len(FALLBACK_COLORS)]
            local_style_map[code] = color
            fallback_index += 1

    # Generate traces
    for group_val, color in local_style_map.items():
        dff = df[df[group_col] == group_val]
        if not dff.empty:
            if 'Verification' in dff.columns:
                 dff = dff.copy()
                 dff['Description'] = dff['Verification'].map(VERIFICATION_DESCRIPTIONS).fillna("Unknown Code")
            else:
                 dff['Description'] = "N/A"

            custom_data_cols = ['UNIT_INDEX_X', 'UNIT_INDEX_Y', 'DEFECT_TYPE', 'DEFECT_ID', 'Verification', 'Description']

            hovertemplate = ("<b>Status: %{customdata[4]}</b><br>"
                             "Description : %{customdata[5]}<br>"
                             "Type: %{customdata[2]}<br>"
                             "Unit Index (X, Y): (%{customdata[0]}, %{customdata[1]})<br>"
                             "Defect ID: %{customdata[3]}"
                             "<extra></extra>")

            traces.append(go.Scatter(
                x=dff['plot_x'],
                y=dff['plot_y'],
                mode='markers',
                marker=dict(color=color, size=8, line=dict(width=1, color='black')),
                name=group_val,
                customdata=dff[custom_data_cols],
                hovertemplate=hovertemplate
            ))

    return traces
    
def create_defect_map_figure(df: pd.DataFrame, panel_rows: int, panel_cols: int, quadrant_selection: str = Quadrant.ALL.value, lot_number: Optional[str] = None, title: Optional[str] = None) -> go.Figure:
    """
    Creates the full Defect Map Figure (Traces + Grid + Layout).
    """
    fig = go.Figure(data=create_defect_traces(df))
    fig.update_layout(shapes=create_grid_shapes(panel_rows, panel_cols, quadrant_selection))

    # Calculate ticks and ranges
    cell_width, cell_height = QUADRANT_WIDTH / panel_cols, QUADRANT_HEIGHT / panel_rows
    x_tick_vals_q1 = [(i * cell_width) + (cell_width / 2) for i in range(panel_cols)]
    x_tick_vals_q2 = [(QUADRANT_WIDTH + GAP_SIZE) + (i * cell_width) + (cell_width / 2) for i in range(panel_cols)]
    y_tick_vals_q1 = [(i * cell_height) + (cell_height / 2) for i in range(panel_rows)]
    y_tick_vals_q3 = [(QUADRANT_HEIGHT + GAP_SIZE) + (i * cell_height) + (cell_height / 2) for i in range(panel_rows)]
    x_tick_text, y_tick_text = list(range(panel_cols * 2)), list(range(panel_rows * 2))
    x_axis_range, y_axis_range, show_ticks = [-GAP_SIZE, PANEL_WIDTH + (GAP_SIZE * 2)], [-GAP_SIZE, PANEL_HEIGHT + (GAP_SIZE * 2)], True

    if quadrant_selection != Quadrant.ALL.value:
        show_ticks = False
        ranges = {
            'Q1': ([0, QUADRANT_WIDTH], [0, QUADRANT_HEIGHT]),
            'Q2': ([QUADRANT_WIDTH + GAP_SIZE, PANEL_WIDTH + GAP_SIZE], [0, QUADRANT_HEIGHT]),
            'Q3': ([0, QUADRANT_WIDTH], [QUADRANT_HEIGHT + GAP_SIZE, PANEL_HEIGHT + GAP_SIZE]),
            'Q4': ([QUADRANT_WIDTH + GAP_SIZE, PANEL_WIDTH + GAP_SIZE], [QUADRANT_HEIGHT + GAP_SIZE, PANEL_HEIGHT + GAP_SIZE])
        }
        x_axis_range, y_axis_range = ranges[quadrant_selection]

    final_title = title if title else f"Panel Defect Map - Quadrant: {quadrant_selection}"

    fig.update_layout(
        title=dict(text=final_title, font=dict(color=TEXT_COLOR), x=0.5, xanchor='center'),
        xaxis=dict(title="Unit Column Index", title_font=dict(color=TEXT_COLOR), tickfont=dict(color=TEXT_COLOR), tickvals=x_tick_vals_q1 + x_tick_vals_q2 if show_ticks else [], ticktext=x_tick_text if show_ticks else [], range=x_axis_range, showgrid=False, zeroline=False, showline=True, linewidth=3, linecolor=GRID_COLOR, mirror=True),
        yaxis=dict(title="Unit Row Index", title_font=dict(color=TEXT_COLOR), tickfont=dict(color=TEXT_COLOR), tickvals=y_tick_vals_q1 + y_tick_vals_q3 if show_ticks else [], ticktext=y_tick_text if show_ticks else [], range=y_axis_range, scaleanchor="x", scaleratio=1, showgrid=False, zeroline=False, showline=True, linewidth=3, linecolor=GRID_COLOR, mirror=True),
        plot_bgcolor=PLOT_AREA_COLOR, paper_bgcolor=BACKGROUND_COLOR, legend=dict(title_font=dict(color=TEXT_COLOR), font=dict(color=TEXT_COLOR), x=1.02, y=1, xanchor='left', yanchor='top'),
        hoverlabel=dict(bgcolor="#4A4A4A", font_size=14, font_family="sans-serif"), height=800
    )

    if lot_number and quadrant_selection == Quadrant.ALL.value:
        fig.add_annotation(x=PANEL_WIDTH + GAP_SIZE, y=PANEL_HEIGHT + GAP_SIZE, text=f"<b>Lot #: {lot_number}</b>", showarrow=False, font=dict(size=14, color=TEXT_COLOR), align="right", xanchor="right", yanchor="bottom")

    return fig

def create_pareto_trace(df: pd.DataFrame) -> go.Bar:
    if df.empty: return go.Bar(name='Pareto')

    has_verification_data = df['HAS_VERIFICATION_DATA'].any() if 'HAS_VERIFICATION_DATA' in df.columns else False
    group_col = 'Verification' if has_verification_data else 'DEFECT_TYPE'

    pareto_data = df[group_col].value_counts().reset_index()
    pareto_data.columns = ['Label', 'Count']

    return go.Bar(x=pareto_data['Label'], y=pareto_data['Count'], name='Pareto', marker_color='#4682B4')

def create_grouped_pareto_trace(df: pd.DataFrame) -> List[go.Bar]:
    if df.empty: return []

    has_verification_data = df['HAS_VERIFICATION_DATA'].any() if 'HAS_VERIFICATION_DATA' in df.columns else False
    group_col = 'Verification' if has_verification_data else 'DEFECT_TYPE'

    grouped_data = df.groupby(['QUADRANT', group_col]).size().reset_index(name='Count')
    top_items = df[group_col].value_counts().index.tolist()

    traces = []
    quadrants = ['Q1', 'Q2', 'Q3', 'Q4']
    for quadrant in quadrants:
        quadrant_data = grouped_data[grouped_data['QUADRANT'] == quadrant]
        pivot = quadrant_data.pivot(index=group_col, columns='QUADRANT', values='Count').reindex(top_items).fillna(0)
        if not pivot.empty:
            traces.append(go.Bar(name=quadrant, x=pivot.index, y=pivot[quadrant]))
    return traces

def create_pareto_figure(df: pd.DataFrame, quadrant_selection: str = Quadrant.ALL.value) -> go.Figure:
    """
    Creates the Pareto Figure (Traces + Layout).
    """
    fig = go.Figure()
    if quadrant_selection == Quadrant.ALL.value:
        for trace in create_grouped_pareto_trace(df): fig.add_trace(trace)
        fig.update_layout(barmode='stack')
    else:
        fig.add_trace(create_pareto_trace(df))

    fig.update_layout(
        title=dict(text=f"Defect Pareto - Quadrant: {quadrant_selection}", font=dict(color=TEXT_COLOR)),
        xaxis=dict(title="Defect Type", categoryorder='total descending', title_font=dict(color=TEXT_COLOR), tickfont=dict(color=TEXT_COLOR)),
        yaxis=dict(title_font=dict(color=TEXT_COLOR), tickfont=dict(color=TEXT_COLOR)),
        plot_bgcolor=PLOT_AREA_COLOR, paper_bgcolor=BACKGROUND_COLOR, height=600,
        legend=dict(font=dict(color=TEXT_COLOR))
    )
    return fig

def create_verification_status_chart(df: pd.DataFrame) -> List[go.Bar]:
    # ... (omitted for brevity, same as before)
    if df.empty: return []
    grouped = df.groupby(['DEFECT_TYPE', 'QUADRANT', 'Verification']).size().unstack(fill_value=0)
    all_defect_types = df['DEFECT_TYPE'].unique()
    all_quadrants = ['Q1', 'Q2', 'Q3', 'Q4']
    all_combinations = pd.MultiIndex.from_product([all_defect_types, all_quadrants], names=['DEFECT_TYPE', 'QUADRANT'])
    grouped = grouped.reindex(all_combinations, fill_value=0)
    for status in ['T', 'F', 'TA']:
        if status not in grouped.columns: grouped[status] = 0
    grouped = grouped.reset_index()
    x_axis_data = [grouped['DEFECT_TYPE'], grouped['QUADRANT']]
    status_map = {'T': {'name': 'True', 'color': '#FF0000'}, 'F': {'name': 'False', 'color': '#2ca02c'}, 'TA': {'name': 'Acceptable', 'color': '#FFBF00'}}
    traces = []
    for status_code, details in status_map.items():
        traces.append(go.Bar(name=details['name'], x=x_axis_data, y=grouped[status_code], marker_color=details['color']))
    return traces

def create_still_alive_map(panel_rows: int, panel_cols: int, true_defect_coords: Set[Tuple[int, int]]) -> List[Dict[str, Any]]:
    """
    Creates the shapes for the 'Still Alive' map by drawing colored cells and an overlay grid.
    """
    shapes = []
    total_cols, total_rows = panel_cols * 2, panel_rows * 2
    all_origins = {'Q1': (0, 0), 'Q2': (QUADRANT_WIDTH + GAP_SIZE, 0), 'Q3': (0, QUADRANT_HEIGHT + GAP_SIZE), 'Q4': (QUADRANT_WIDTH + GAP_SIZE, QUADRANT_HEIGHT + GAP_SIZE)}
    cell_width, cell_height = QUADRANT_WIDTH / panel_cols, QUADRANT_HEIGHT / panel_rows

    # 1. Draw the colored cells first (without borders)
    for row in range(total_rows):
        for col in range(total_cols):
            quadrant_col, local_col = divmod(col, panel_cols)
            quadrant_row, local_row = divmod(row, panel_rows)
            quad_key = f"Q{quadrant_row * 2 + quadrant_col + 1}"
            x_origin, y_origin = all_origins[quad_key]
            x0, y0 = x_origin + local_col * cell_width, y_origin + local_row * cell_height
            fill_color = DEFECTIVE_CELL_COLOR if (col, row) in true_defect_coords else ALIVE_CELL_COLOR
            shapes.append({'type': 'rect', 'x0': x0, 'y0': y0, 'x1': x0 + cell_width, 'y1': y0 + cell_height, 'fillcolor': fill_color, 'line': {'width': 0}, 'layer': 'below'})

    # 2. Draw grid lines over the colored cells by calling create_grid_shapes with fill=False
    shapes.extend(create_grid_shapes(panel_rows, panel_cols, quadrant='All', fill=False))

    return shapes

def create_still_alive_figure(panel_rows: int, panel_cols: int, true_defect_coords: Set[Tuple[int, int]]) -> go.Figure:
    """
    Creates the Still Alive Map Figure (Shapes + Layout).
    """
    fig = go.Figure()
    map_shapes = create_still_alive_map(panel_rows, panel_cols, true_defect_coords)

    cell_width, cell_height = QUADRANT_WIDTH / panel_cols, QUADRANT_HEIGHT / panel_rows
    x_tick_vals_q1 = [(i * cell_width) + (cell_width / 2) for i in range(panel_cols)]
    x_tick_vals_q2 = [(QUADRANT_WIDTH + GAP_SIZE) + (i * cell_width) + (cell_width / 2) for i in range(panel_cols)]
    y_tick_vals_q1 = [(i * cell_height) + (cell_height / 2) for i in range(panel_rows)]
    y_tick_vals_q3 = [(QUADRANT_HEIGHT + GAP_SIZE) + (i * cell_height) + (cell_height / 2) for i in range(panel_rows)]
    x_tick_text = list(range(panel_cols * 2))
    y_tick_text = list(range(panel_rows * 2))

    fig.update_layout(
        title=dict(text=f"Still Alive Map ({len(true_defect_coords)} Defective Cells)", font=dict(color=TEXT_COLOR), x=0.5, xanchor='center'),
        xaxis=dict(
            title="Unit Column Index", range=[-GAP_SIZE, PANEL_WIDTH + (GAP_SIZE * 2)],
            tickvals=x_tick_vals_q1 + x_tick_vals_q2, ticktext=x_tick_text,
            showgrid=False, zeroline=False, showline=True, linewidth=2, linecolor=GRID_COLOR, mirror=True,
            title_font=dict(color=TEXT_COLOR), tickfont=dict(color=TEXT_COLOR)
        ),
        yaxis=dict(
            title="Unit Row Index", range=[-GAP_SIZE, PANEL_HEIGHT + (GAP_SIZE * 2)],
            tickvals=y_tick_vals_q1 + y_tick_vals_q3, ticktext=y_tick_text,
            scaleanchor="x", scaleratio=1, showgrid=False, zeroline=False, showline=True, linewidth=2, linecolor=GRID_COLOR, mirror=True,
            title_font=dict(color=TEXT_COLOR), tickfont=dict(color=TEXT_COLOR)
        ),
        plot_bgcolor=PLOT_AREA_COLOR, paper_bgcolor=BACKGROUND_COLOR, shapes=map_shapes, height=800, margin=dict(l=20, r=20, t=80, b=20)
    )
    return fig

def hex_to_rgba(hex_color: str, opacity: float = 0.5) -> str:
    """Helper to convert hex color to rgba string for Plotly without matplotlib dependency."""
    try:
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 6:
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            return f'rgba({r}, {g}, {b}, {opacity})'
        return f'rgba(128, 128, 128, {opacity})'
    except ValueError:
        return f'rgba(128, 128, 128, {opacity})' # Fallback grey

def create_defect_sankey(df: pd.DataFrame) -> go.Sankey:
    """
    Creates a Sankey diagram mapping Defect Types (Left) to Verification Status (Right).
    Only returns a figure if HAS_VERIFICATION_DATA is true.
    """
    if df.empty:
        return None

    has_verification = df['HAS_VERIFICATION_DATA'].iloc[0] if 'HAS_VERIFICATION_DATA' in df.columns else False
    if not has_verification:
        return None

    # Prepare data for Sankey
    # Group by [DEFECT_TYPE, Verification] and count
    sankey_df = df.groupby(['DEFECT_TYPE', 'Verification']).size().reset_index(name='Count')

    # Create unique labels list
    defect_types = sankey_df['DEFECT_TYPE'].unique().tolist()
    verification_statuses = sankey_df['Verification'].unique().tolist()

    all_labels = defect_types + verification_statuses

    # Create independent maps for source and target
    # Source Map: Maps Defect Type string to index 0..N-1
    source_map = {label: i for i, label in enumerate(defect_types)}

    # Target Map: Maps Verification string to index N..N+M-1
    offset = len(defect_types)
    target_map = {label: i + offset for i, label in enumerate(verification_statuses)}

    sources = []
    targets = []
    values = []
    link_colors = []

    # Assign colors to source nodes (Defect Types) using defect_style_map
    source_colors_hex = []
    fallback_idx = 0

    # 1. Colors for Defect Types (Left Side)
    for dtype in defect_types:
        if dtype in defect_style_map:
            color = defect_style_map[dtype]
        else:
            color = FALLBACK_COLORS[fallback_idx % len(FALLBACK_COLORS)]
            fallback_idx += 1
        source_colors_hex.append(color)

    # 2. Colors for Verification Status (Right Side)
    # Logic: Green for 'Safe' (N, GE57), Red/Orange for others
    safe_values_upper = {v.upper() for v in SAFE_VERIFICATION_VALUES}
    target_colors_hex = []

    for status in verification_statuses:
        if status.upper() in safe_values_upper:
            target_colors_hex.append(VERIFICATION_COLOR_SAFE)
        else:
            target_colors_hex.append(VERIFICATION_COLOR_DEFECT)

    node_colors = source_colors_hex + target_colors_hex

    # 3. Build Links and Link Colors
    for _, row in sankey_df.iterrows():
        s_idx = source_map[row['DEFECT_TYPE']]
        t_idx = target_map[row['Verification']]
        sources.append(s_idx)
        targets.append(t_idx)
        values.append(row['Count'])

        # Link color = Source Color with opacity
        source_hex = source_colors_hex[s_idx]
        link_colors.append(hex_to_rgba(source_hex, opacity=0.4))

    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=20,
            thickness=20,    # Thicker nodes for better visibility (Task 2)
            line=dict(color="#444444", width=0.5), # Subtle dark grey border (Task 2)
            label=all_labels,
            color=node_colors,
            hovertemplate='Total Defects: %{value}<extra></extra>' # Cleaner tooltip
        ),
        link=dict(
            source=sources,
            target=targets,
            value=values,
            color=[hex_to_rgba(c, opacity=0.6) for c in link_colors] # Increased opacity (Task 3)
        ),
        textfont=dict(size=14, color=TEXT_COLOR, family="Roboto") # Modern Font (Task 1)
    )])

    # Set background color explicitly to match the app theme
    fig.update_layout(
        title=dict(
            text="Defect Type → Verification Flow",
            font=dict(size=20, color=TEXT_COLOR) # Larger Title
        ),
        font=dict(size=14, color=TEXT_COLOR), # Base font size
        height=600,
        paper_bgcolor=BACKGROUND_COLOR,
        plot_bgcolor=PLOT_AREA_COLOR,
        margin=dict(l=20, r=20, t=50, b=20)
    )
    return fig

def create_unit_grid_heatmap(df: pd.DataFrame, panel_rows: int, panel_cols: int) -> go.Figure:
    """
    Creates a 'Chessboard' style Grid Density Heatmap using UNIT INDICES.
    Filters for TRUE DEFECTS only.
    """
    if df.empty:
        return go.Figure()

    # Filter for True Defects (exclude Safe Values)
    safe_values_upper = {v.upper() for v in SAFE_VERIFICATION_VALUES}
    if 'Verification' in df.columns:
        df_true = df[~df['Verification'].str.upper().isin(safe_values_upper)].copy()
    else:
        df_true = df.copy()

    if df_true.empty:
        return go.Figure(layout=dict(
            title=dict(text="No True Defects Found for Heatmap", font=dict(color=TEXT_COLOR)),
            paper_bgcolor=BACKGROUND_COLOR, plot_bgcolor=PLOT_AREA_COLOR
        ))

    # Aggregate counts per unit index
    # Note: We need to handle Quadrant offsets for indices to make a global map
    # UNIT_INDEX_X and UNIT_INDEX_Y are usually local to the quadrant in the raw data?
    # Let's check how 'plot_x' is derived. 'plot_x' is physical.
    # For a purely logical map, we should map everything to a global row/col index.

    # Logic:
    # Global Col = (Quadrant Col Offset) + UNIT_INDEX_X
    # Global Row = (Quadrant Row Offset) + UNIT_INDEX_Y
    # Q1: (0,0), Q2: (cols, 0), Q3: (0, rows), Q4: (cols, rows)

    global_indices = []
    for _, row in df_true.iterrows():
        q = row['QUADRANT']
        u_x = int(row['UNIT_INDEX_X'])
        u_y = int(row['UNIT_INDEX_Y'])

        g_x = u_x + (panel_cols if q in ['Q2', 'Q4'] else 0)
        g_y = u_y + (panel_rows if q in ['Q3', 'Q4'] else 0)
        global_indices.append((g_x, g_y))

    heatmap_df = pd.DataFrame(global_indices, columns=['Global_X', 'Global_Y'])
    heatmap_data = heatmap_df.groupby(['Global_X', 'Global_Y']).size().reset_index(name='Count')

    # Create the Heatmap
    # Using 'Reds' colorscale for serious yield impact
    fig = go.Figure(data=go.Heatmap(
        x=heatmap_data['Global_X'],
        y=heatmap_data['Global_Y'],
        z=heatmap_data['Count'],
        colorscale='Reds',
        xgap=1, ygap=1, # Create the grid look
        colorbar=dict(title='Defects', title_font=dict(color=TEXT_COLOR), tickfont=dict(color=TEXT_COLOR))
    ))

    # Layout improvements
    total_global_cols = panel_cols * 2
    total_global_rows = panel_rows * 2

    fig.update_layout(
        title=dict(text="True Defect Grid Density (Yield Loss Map)", font=dict(color=TEXT_COLOR, size=18)),
        xaxis=dict(
            title="Global Unit Column",
            tickmode='linear', dtick=1,
            showgrid=False, zeroline=False,
            range=[-0.5, total_global_cols - 0.5],
            title_font=dict(color=TEXT_COLOR), tickfont=dict(color=TEXT_COLOR)
        ),
        yaxis=dict(
            title="Global Unit Row",
            tickmode='linear', dtick=1,
            showgrid=False, zeroline=False,
            range=[-0.5, total_global_rows - 0.5],
            scaleanchor="x", scaleratio=1, # Keep squares square
            title_font=dict(color=TEXT_COLOR), tickfont=dict(color=TEXT_COLOR)
        ),
        plot_bgcolor=PLOT_AREA_COLOR,
        paper_bgcolor=BACKGROUND_COLOR,
        height=700
    )

    return fig

def create_hexbin_heatmap(df: pd.DataFrame, panel_rows: int, panel_cols: int) -> go.Figure:
    """
    Creates a Hexbin/Point Density Heatmap using Physical Coordinates.
    Filters for TRUE DEFECTS only.
    """
    if df.empty:
        return go.Figure()

    # Filter for True Defects
    safe_values_upper = {v.upper() for v in SAFE_VERIFICATION_VALUES}
    if 'Verification' in df.columns:
        df_true = df[~df['Verification'].str.upper().isin(safe_values_upper)].copy()
    else:
        df_true = df.copy()

    if df_true.empty:
        return go.Figure(layout=dict(title="No True Defects Found"))

    # Use Histogram2d (Rectangular bins look cleaner than Hexbin in Plotly sometimes,
    # but let's try to mimic the Hex look or smooth density)

    # Option 3 was "Hexbin / Point Density". Plotly's Histogram2dContour is the "Weather Map".
    # Plotly's Histogram2d is the pixelated one.
    # To get a "Point Density" look, we can use a high-resolution contour or a density heatmap.

    fig = go.Figure(go.Histogram2dContour(
        x=df_true['plot_x'],
        y=df_true['plot_y'],
        colorscale='Viridis', # Distinct from the Red grid map
        reversescale=False,
        xaxis='x',
        yaxis='y',
        ncontours=25,
        contours=dict(coloring='heatmap', showlabels=True)
    ))

    # Overlay Grid for reference
    shapes = create_grid_shapes(panel_rows, panel_cols, quadrant='All', fill=False)

    fig.update_layout(
        title=dict(text="True Defect Density Clusters (Hotspots)", font=dict(color=TEXT_COLOR, size=18)),
        xaxis=dict(showgrid=False, zeroline=False, showline=True, mirror=True, range=[-GAP_SIZE, PANEL_WIDTH + GAP_SIZE*2], tickfont=dict(color=TEXT_COLOR)),
        yaxis=dict(showgrid=False, zeroline=False, showline=True, mirror=True, range=[-GAP_SIZE, PANEL_HEIGHT + GAP_SIZE*2], scaleanchor="x", scaleratio=1, tickfont=dict(color=TEXT_COLOR)),
        shapes=shapes,
        plot_bgcolor=PLOT_AREA_COLOR,
        paper_bgcolor=BACKGROUND_COLOR,
        height=700
    )
    return fig

def create_defect_sunburst(df: pd.DataFrame) -> go.Figure:
    """
    Creates a Sunburst chart: Defect Type -> Verification (if avail).
    Hierarchy: Total -> Defect Type -> Verification Status
    """
    if df.empty:
        return go.Figure()

    has_verification = df['HAS_VERIFICATION_DATA'].iloc[0] if 'HAS_VERIFICATION_DATA' in df.columns else False

    # 1. Aggregate
    if has_verification:
        grouped = df.groupby(['DEFECT_TYPE', 'Verification']).size().reset_index(name='Count')
    else:
        grouped = df.groupby(['DEFECT_TYPE']).size().reset_index(name='Count')

    # Build lists
    ids = []
    labels = []
    parents = []
    values = []

    # Root
    total_count = grouped['Count'].sum()
    ids.append("Total")
    labels.append(f"Total<br>{total_count}")
    parents.append("")
    values.append(total_count)

    # Level 1: Defect Type
    for dtype in grouped['DEFECT_TYPE'].unique():
        dtype_count = grouped[grouped['DEFECT_TYPE'] == dtype]['Count'].sum()
        ids.append(f"{dtype}")
        labels.append(dtype)
        parents.append("Total")
        values.append(dtype_count)

        # Level 2: Verification (if exists)
        if has_verification:
            dtype_df = grouped[grouped['DEFECT_TYPE'] == dtype]
            for ver in dtype_df['Verification'].unique():
                ver_count = dtype_df[dtype_df['Verification'] == ver]['Count'].sum()
                ids.append(f"{dtype}-{ver}")
                labels.append(ver)
                parents.append(f"{dtype}")
                values.append(ver_count)

    fig = go.Figure(go.Sunburst(
        ids=ids,
        labels=labels,
        parents=parents,
        values=values,
        branchvalues="total"
    ))
    # IMPROVEMENT: Fix "Black and White" export by setting dark theme colors
    fig.update_layout(
        margin=dict(t=0, l=0, r=0, b=0),
        height=500,
        paper_bgcolor=BACKGROUND_COLOR,
        font=dict(color=TEXT_COLOR)
    )

    return fig
