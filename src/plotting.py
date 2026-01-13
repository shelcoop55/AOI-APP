"""
Plotting and Visualization Module.
This version draws a true-to-scale simulation of a 510x510mm physical panel
with explicit margins and gaps.
"""
import plotly.graph_objects as go
import pandas as pd
from typing import List, Dict, Any, Set, Tuple, Optional
import numpy as np

from src.config import (
    PANEL_COLOR, GRID_COLOR, defect_style_map, TEXT_COLOR, BACKGROUND_COLOR, PLOT_AREA_COLOR,
    PANEL_WIDTH, PANEL_HEIGHT, GAP_SIZE, MARGIN_X, MARGIN_Y,
    ALIVE_CELL_COLOR, DEFECTIVE_CELL_COLOR, FALLBACK_COLORS, SAFE_VERIFICATION_VALUES,
    VERIFICATION_COLOR_SAFE, VERIFICATION_COLOR_DEFECT, NEON_PALETTE
)
from src.documentation import VERIFICATION_DESCRIPTIONS
from src.enums import Quadrant

# --- Recalculate Active Area based on Margins and Gaps ---
# Total Width = MARGIN_X + Active_W + GAP + Active_W + MARGIN_X
# Active_W = (PANEL_WIDTH - 2*MARGIN_X - GAP_SIZE) / 2
ACTIVE_QUADRANT_WIDTH = (PANEL_WIDTH - (2 * MARGIN_X) - GAP_SIZE) / 2
ACTIVE_QUADRANT_HEIGHT = (PANEL_HEIGHT - (2 * MARGIN_Y) - GAP_SIZE) / 2

# Origins for the 4 Quadrants (Top-Left 0,0 based on global panel)
# Q1: Top-Left
Q1_ORIGIN = (MARGIN_X, MARGIN_Y)
# Q2: Top-Right
Q2_ORIGIN = (MARGIN_X + ACTIVE_QUADRANT_WIDTH + GAP_SIZE, MARGIN_Y)
# Q3: Bottom-Left
Q3_ORIGIN = (MARGIN_X, MARGIN_Y + ACTIVE_QUADRANT_HEIGHT + GAP_SIZE)
# Q4: Bottom-Right
Q4_ORIGIN = (MARGIN_X + ACTIVE_QUADRANT_WIDTH + GAP_SIZE, MARGIN_Y + ACTIVE_QUADRANT_HEIGHT + GAP_SIZE)

# Map Quadrant Keys to Origins
QUADRANT_ORIGINS = {
    'Q1': Q1_ORIGIN,
    'Q2': Q2_ORIGIN,
    'Q3': Q3_ORIGIN,
    'Q4': Q4_ORIGIN
}

# ==============================================================================
# --- Private Helper Functions for Grid Creation ---
# ==============================================================================

def _draw_border_and_gaps() -> List[Dict[str, Any]]:
    """Creates the shapes for the outer border and inner gaps of the panel."""
    shapes = []
    # Visual cues for dead zones (Margins and Gaps)
    # We can draw a large rectangle for the whole panel (background)
    # and then overlay the active quadrants. Or draw the gaps.

    # Let's draw the "Dead Zone" background
    shapes.append(dict(
        type="rect",
        x0=0, y0=0, x1=PANEL_WIDTH, y1=PANEL_HEIGHT,
        fillcolor=PLOT_AREA_COLOR, # Dark Grey for background
        line=dict(color=GRID_COLOR, width=2),
        layer='below'
    ))

    # We don't need explicit gap rectangles if we draw the active quadrants on top.
    return shapes

def _draw_quadrant_grids(origins_to_draw: Dict[str, Tuple[float, float]], panel_rows: int, panel_cols: int, fill: bool = True) -> List[Dict[str, Any]]:
    """Creates the shapes for the quadrant outlines and their internal grid lines."""
    shapes = []

    # Calculate cell size based on Active Dimensions
    cell_width = ACTIVE_QUADRANT_WIDTH / panel_cols
    cell_height = ACTIVE_QUADRANT_HEIGHT / panel_rows

    for quad_key, (x_start, y_start) in origins_to_draw.items():
        # Draw the Active Quadrant Background
        if fill:
            shapes.append(dict(
                type="rect",
                x0=x_start, y0=y_start,
                x1=x_start + ACTIVE_QUADRANT_WIDTH, y1=y_start + ACTIVE_QUADRANT_HEIGHT,
                line=dict(color=GRID_COLOR, width=2),
                fillcolor=PANEL_COLOR,
                layer='below'
            ))

        # Draw Internal Grid Lines
        for i in range(1, panel_cols):
            line_x = x_start + (i * cell_width)
            shapes.append(dict(
                type="line",
                x0=line_x, y0=y_start,
                x1=line_x, y1=y_start + ACTIVE_QUADRANT_HEIGHT,
                line=dict(color=GRID_COLOR, width=1, dash='solid'),
                opacity=0.3,
                layer='below'
            ))

        for i in range(1, panel_rows):
            line_y = y_start + (i * cell_height)
            shapes.append(dict(
                type="line",
                x0=x_start, y0=line_y,
                x1=x_start + ACTIVE_QUADRANT_WIDTH, y1=line_y,
                line=dict(color=GRID_COLOR, width=1, dash='solid'),
                opacity=0.3,
                layer='below'
            ))
            
    return shapes

# ==============================================================================
# --- Public API Functions ---
# ==============================================================================

def create_grid_shapes(panel_rows: int, panel_cols: int, quadrant: str = 'All', fill: bool = True) -> List[Dict[str, Any]]:
    """
    Creates the visual shapes for the panel grid in a fixed 510x515mm coordinate system.
    """
    origins_to_draw = QUADRANT_ORIGINS if quadrant == 'All' else {quadrant: QUADRANT_ORIGINS[quadrant]}

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

    has_verification_data = df['HAS_VERIFICATION_DATA'].any() if 'HAS_VERIFICATION_DATA' in df.columns else False
    group_col = 'Verification' if has_verification_data else 'DEFECT_TYPE'
    unique_groups = df[group_col].unique()

    local_style_map = {}
    if group_col == 'DEFECT_TYPE':
        local_style_map = defect_style_map.copy()
        fallback_index = 0
        for dtype in unique_groups:
            if dtype not in local_style_map:
                local_style_map[dtype] = FALLBACK_COLORS[fallback_index % len(FALLBACK_COLORS)]
                fallback_index += 1
    else:
        fallback_index = 0
        for code in unique_groups:
            local_style_map[code] = FALLBACK_COLORS[fallback_index % len(FALLBACK_COLORS)]
            fallback_index += 1

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

def create_multi_layer_defect_map(df: pd.DataFrame, panel_rows: int, panel_cols: int, use_real_coords: bool = False) -> go.Figure:
    """
    Creates a defect map visualizing defects from ALL layers simultaneously.
    UPDATED: Granular Legend Control (No Grouping).
    """
    fig = go.Figure()

    if not df.empty:
        if 'LAYER_NUM' not in df.columns: df['LAYER_NUM'] = 0

        # Use real coords by default now as preferred by user logic, but keep flag
        x_col = 'plot_x_coord' if use_real_coords and 'plot_x_coord' in df.columns else 'plot_x'
        y_col = 'plot_y_coord' if use_real_coords and 'plot_y_coord' in df.columns else 'plot_y'

        unique_layer_nums = sorted(df['LAYER_NUM'].unique())
        layer_colors = {num: FALLBACK_COLORS[i % len(FALLBACK_COLORS)] for i, num in enumerate(unique_layer_nums)}
        symbol_map = {'F': 'circle', 'B': 'diamond'}

        for layer_num in unique_layer_nums:
            layer_color = layer_colors[layer_num]
            layer_df = df[df['LAYER_NUM'] == layer_num]

            for side in sorted(layer_df['SIDE'].unique()):
                dff = layer_df[layer_df['SIDE'] == side]
                symbol = symbol_map.get(side, 'circle')
                side_name = "Front" if side == 'F' else "Back"

                # Further break down by Defect Type or just Layer/Side?
                # User asked for "Legend per trace". Usually this means per Defect Type if colored by Type.
                # But here we color by Layer.
                # If we want to toggle specific defects, we should iterate types too?
                # But that would explode the legend (Layer 1 Front Short, Layer 1 Front Open...)
                # The user said: "toggle individual traces" (plural).
                # Current implementation: Trace per Layer+Side.
                # If I remove legendgroup, I can toggle "Layer 1 (Front)" independently of "Layer 1 (Back)".
                # This seems to be what is requested vs "Grouped".

                trace_name = f"Layer {layer_num} ({side_name})"

                if 'Verification' in dff.columns:
                     dff = dff.copy()
                     dff['Description'] = dff['Verification'].map(VERIFICATION_DESCRIPTIONS).fillna("Unknown Code")
                else:
                     dff['Description'] = "N/A"

                custom_data_cols = ['UNIT_INDEX_X', 'UNIT_INDEX_Y', 'DEFECT_TYPE', 'DEFECT_ID', 'Verification', 'Description', 'SOURCE_FILE']

                hovertemplate = ("<b>Layer: " + str(layer_num) + "</b><br>"
                                 "Side: " + side_name + "<br>"
                                 "Status: %{customdata[4]}<br>"
                                 "Type: %{customdata[2]}<br>"
                                 "Coords: (%{customdata[0]}, %{customdata[1]})<br>"
                                 "File: %{customdata[6]}"
                                 "<extra></extra>")

                fig.add_trace(go.Scatter(
                    x=dff[x_col],
                    y=dff[y_col],
                    mode='markers',
                    marker=dict(
                        color=layer_color,
                        symbol=symbol,
                        size=9,
                        line=dict(width=1, color='black')
                    ),
                    name=trace_name,
                    # REMOVED legendgroup to allow individual toggling
                    customdata=dff[custom_data_cols],
                    hovertemplate=hovertemplate
                ))

    # Add Grid and Layout
    fig.update_layout(shapes=create_grid_shapes(panel_rows, panel_cols, quadrant='All'))

    # Calculate Ticks based on Active Areas
    cell_width = ACTIVE_QUADRANT_WIDTH / panel_cols
    cell_height = ACTIVE_QUADRANT_HEIGHT / panel_rows

    # Ticks for Q1/Q3 (Left) and Q2/Q4 (Right)
    # Note: Ticks should align with the center of the UNIT, relative to the QUADRANT ORIGIN
    x_tick_vals = []
    # Q1/Q3 X-ticks
    x_tick_vals.extend([MARGIN_X + (i * cell_width) + (cell_width/2) for i in range(panel_cols)])
    # Q2/Q4 X-ticks
    x_tick_vals.extend([MARGIN_X + ACTIVE_QUADRANT_WIDTH + GAP_SIZE + (i * cell_width) + (cell_width/2) for i in range(panel_cols)])

    y_tick_vals = []
    # Q1/Q2 Y-ticks
    y_tick_vals.extend([MARGIN_Y + (i * cell_height) + (cell_height/2) for i in range(panel_rows)])
    # Q3/Q4 Y-ticks
    y_tick_vals.extend([MARGIN_Y + ACTIVE_QUADRANT_HEIGHT + GAP_SIZE + (i * cell_height) + (cell_height/2) for i in range(panel_rows)])

    title_text = "Multi-Layer Combined Defect Map"
    subtitle = "(Real Coordinates)" if use_real_coords else "(Unit Grid + Jitter)"

    fig.update_layout(
        title=dict(text=f"{title_text} {subtitle}", font=dict(color=TEXT_COLOR), x=0.5, xanchor='center'),
        xaxis=dict(
            title="Unit Column Index",
            tickvals=x_tick_vals,
            range=[0, PANEL_WIDTH], constrain='domain', # Use full panel width
            showgrid=False, zeroline=False, showline=True, linewidth=3, linecolor=GRID_COLOR, mirror=True,
            title_font=dict(color=TEXT_COLOR), tickfont=dict(color=TEXT_COLOR)
        ),
        yaxis=dict(
            title="Unit Row Index",
            tickvals=y_tick_vals,
            range=[0, PANEL_HEIGHT], # Use full panel height
            scaleanchor="x", scaleratio=1,
            showgrid=False, zeroline=False, showline=True, linewidth=3, linecolor=GRID_COLOR, mirror=True,
            title_font=dict(color=TEXT_COLOR), tickfont=dict(color=TEXT_COLOR)
        ),
        plot_bgcolor=PLOT_AREA_COLOR, paper_bgcolor=BACKGROUND_COLOR,
        legend=dict(title=dict(text="Build-Up Layer"), title_font=dict(color=TEXT_COLOR), font=dict(color=TEXT_COLOR), x=1.02, y=1, xanchor='left', yanchor='top'),
        hoverlabel=dict(bgcolor="#4A4A4A", font_size=14, font_family="sans-serif"), height=800
    )

    return fig
    
def create_defect_map_figure(df: pd.DataFrame, panel_rows: int, panel_cols: int, quadrant_selection: str = Quadrant.ALL.value, lot_number: Optional[str] = None, title: Optional[str] = None) -> go.Figure:
    """
    Creates the full Defect Map Figure (Traces + Grid + Layout).
    """
    fig = go.Figure(data=create_defect_traces(df))
    fig.update_layout(shapes=create_grid_shapes(panel_rows, panel_cols, quadrant_selection))

    # Ticks
    cell_width = ACTIVE_QUADRANT_WIDTH / panel_cols
    cell_height = ACTIVE_QUADRANT_HEIGHT / panel_rows

    x_tick_vals = []
    x_tick_vals.extend([MARGIN_X + (i * cell_width) + (cell_width/2) for i in range(panel_cols)])
    x_tick_vals.extend([MARGIN_X + ACTIVE_QUADRANT_WIDTH + GAP_SIZE + (i * cell_width) + (cell_width/2) for i in range(panel_cols)])

    y_tick_vals = []
    y_tick_vals.extend([MARGIN_Y + (i * cell_height) + (cell_height/2) for i in range(panel_rows)])
    y_tick_vals.extend([MARGIN_Y + ACTIVE_QUADRANT_HEIGHT + GAP_SIZE + (i * cell_height) + (cell_height/2) for i in range(panel_rows)])

    x_tick_text, y_tick_text = list(range(panel_cols * 2)), list(range(panel_rows * 2))

    # Ranges
    x_axis_range = [0, PANEL_WIDTH]
    y_axis_range = [0, PANEL_HEIGHT]
    show_ticks = True

    if quadrant_selection != Quadrant.ALL.value:
        show_ticks = False
        # Calculate localized ranges
        origin = QUADRANT_ORIGINS[quadrant_selection]
        x_axis_range = [origin[0], origin[0] + ACTIVE_QUADRANT_WIDTH]
        y_axis_range = [origin[1], origin[1] + ACTIVE_QUADRANT_HEIGHT]

    final_title = title if title else f"Panel Defect Map - Quadrant: {quadrant_selection}"

    fig.update_layout(
        title=dict(text=final_title, font=dict(color=TEXT_COLOR), x=0.5, xanchor='center'),
        xaxis=dict(
            title="Unit Column Index", title_font=dict(color=TEXT_COLOR), tickfont=dict(color=TEXT_COLOR),
            tickvals=x_tick_vals if show_ticks else [], ticktext=x_tick_text if show_ticks else [],
            range=x_axis_range, constrain='domain',
            showgrid=False, zeroline=False, showline=True, linewidth=3, linecolor=GRID_COLOR, mirror=True
        ),
        yaxis=dict(
            title="Unit Row Index", title_font=dict(color=TEXT_COLOR), tickfont=dict(color=TEXT_COLOR),
            tickvals=y_tick_vals if show_ticks else [], ticktext=y_tick_text if show_ticks else [],
            range=y_axis_range, scaleanchor="x", scaleratio=1,
            showgrid=False, zeroline=False, showline=True, linewidth=3, linecolor=GRID_COLOR, mirror=True
        ),
        plot_bgcolor=PLOT_AREA_COLOR, paper_bgcolor=BACKGROUND_COLOR,
        legend=dict(title_font=dict(color=TEXT_COLOR), font=dict(color=TEXT_COLOR), x=1.02, y=1, xanchor='left', yanchor='top'),
        hoverlabel=dict(bgcolor="#4A4A4A", font_size=14, font_family="sans-serif"), height=800
    )

    if lot_number and quadrant_selection == Quadrant.ALL.value:
        fig.add_annotation(x=PANEL_WIDTH, y=PANEL_HEIGHT, text=f"<b>Lot #: {lot_number}</b>", showarrow=False, font=dict(size=14, color=TEXT_COLOR), align="right", xanchor="right", yanchor="bottom")

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

    cell_width = ACTIVE_QUADRANT_WIDTH / panel_cols
    cell_height = ACTIVE_QUADRANT_HEIGHT / panel_rows

    # 1. Draw the colored cells first (without borders)
    for row in range(total_rows):
        for col in range(total_cols):
            quadrant_col, local_col = divmod(col, panel_cols)
            quadrant_row, local_row = divmod(row, panel_rows)
            quad_key = f"Q{quadrant_row * 2 + quadrant_col + 1}"
            x_origin, y_origin = QUADRANT_ORIGINS[quad_key]

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

    # Ticks Calculation
    cell_width = ACTIVE_QUADRANT_WIDTH / panel_cols
    cell_height = ACTIVE_QUADRANT_HEIGHT / panel_rows

    x_tick_vals = []
    x_tick_vals.extend([MARGIN_X + (i * cell_width) + (cell_width/2) for i in range(panel_cols)])
    x_tick_vals.extend([MARGIN_X + ACTIVE_QUADRANT_WIDTH + GAP_SIZE + (i * cell_width) + (cell_width/2) for i in range(panel_cols)])

    y_tick_vals = []
    y_tick_vals.extend([MARGIN_Y + (i * cell_height) + (cell_height/2) for i in range(panel_rows)])
    y_tick_vals.extend([MARGIN_Y + ACTIVE_QUADRANT_HEIGHT + GAP_SIZE + (i * cell_height) + (cell_height/2) for i in range(panel_rows)])

    x_tick_text = list(range(panel_cols * 2))
    y_tick_text = list(range(panel_rows * 2))

    fig.update_layout(
        title=dict(text=f"Still Alive Map ({len(true_defect_coords)} Defective Cells)", font=dict(color=TEXT_COLOR), x=0.5, xanchor='center'),
        xaxis=dict(
            title="Unit Column Index", range=[0, PANEL_WIDTH], constrain='domain',
            tickvals=x_tick_vals, ticktext=x_tick_text,
            showgrid=False, zeroline=False, showline=True, linewidth=2, linecolor=GRID_COLOR, mirror=True,
            title_font=dict(color=TEXT_COLOR), tickfont=dict(color=TEXT_COLOR)
        ),
        yaxis=dict(
            title="Unit Row Index", range=[0, PANEL_HEIGHT],
            tickvals=y_tick_vals, ticktext=y_tick_text,
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
    IMPROVEMENTS:
    - Smart Labels with Counts/Percentages
    - Neon Color Palette
    - Sorted Nodes
    - Thicker Nodes & Solid Links
    - Narrative Tooltips
    """
    if df.empty:
        return None

    has_verification = df['HAS_VERIFICATION_DATA'].iloc[0] if 'HAS_VERIFICATION_DATA' in df.columns else False
    if not has_verification:
        return None

    # Data Prep: Group by [DEFECT_TYPE, Verification]
    sankey_df = df.groupby(['DEFECT_TYPE', 'Verification']).size().reset_index(name='Count')

    # Calculate Totals for Labels and Sorting
    total_defects = sankey_df['Count'].sum()
    defect_counts = sankey_df.groupby('DEFECT_TYPE')['Count'].sum().sort_values(ascending=False)
    verification_counts = sankey_df.groupby('Verification')['Count'].sum().sort_values(ascending=False)

    # Unique Sorted Labels
    defect_types = defect_counts.index.tolist()
    verification_statuses = verification_counts.index.tolist()

    all_labels_raw = defect_types + verification_statuses

    # Generate Smart Labels: "Scratch (42 - 15%)"
    smart_labels = []

    # Source Labels (Defects)
    for dtype in defect_types:
        count = defect_counts[dtype]
        pct = (count / total_defects) * 100
        smart_labels.append(f"{dtype} ({count} - {pct:.1f}%)")

    # Target Labels (Verification)
    for ver in verification_statuses:
        count = verification_counts[ver]
        pct = (count / total_defects) * 100
        smart_labels.append(f"{ver} ({count} - {pct:.1f}%)")

    # Mapping
    source_map = {label: i for i, label in enumerate(defect_types)}
    offset = len(defect_types)
    target_map = {label: i + offset for i, label in enumerate(verification_statuses)}

    sources = []
    targets = []
    values = []
    link_colors = []
    custom_hovers = []

    # Assign Neon Colors to Source Nodes
    source_colors_hex = []
    for i, dtype in enumerate(defect_types):
        color = NEON_PALETTE[i % len(NEON_PALETTE)]
        source_colors_hex.append(color)

    # Assign Status Colors to Target Nodes
    safe_values_upper = {v.upper() for v in SAFE_VERIFICATION_VALUES}
    target_colors_hex = []
    for status in verification_statuses:
        if status.upper() in safe_values_upper:
            target_colors_hex.append(VERIFICATION_COLOR_SAFE)
        else:
            target_colors_hex.append(VERIFICATION_COLOR_DEFECT)

    node_colors = source_colors_hex + target_colors_hex

    # Build Links
    # We iterate through the SORTED defect types to ensure visual flow order
    for dtype in defect_types:
        dtype_df = sankey_df[sankey_df['DEFECT_TYPE'] == dtype]
        for _, row in dtype_df.iterrows():
            ver = row['Verification']
            count = row['Count']

            s_idx = source_map[dtype]
            t_idx = target_map[ver]

            sources.append(s_idx)
            targets.append(t_idx)
            values.append(count)

            # Link Color: Match Source with High Opacity (0.8) for "Pipe" look
            source_hex = source_colors_hex[s_idx]
            link_colors.append(hex_to_rgba(source_hex, opacity=0.8))

            # Narrative Tooltip
            pct_flow = (count / total_defects) * 100
            hover_text = (
                f"<b>{count} {dtype}s</b> accounted for <b>{pct_flow:.1f}%</b> of total flow<br>"
                f"Resulting in <b>{ver}</b> status."
            )
            custom_hovers.append(hover_text)

    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=25,
            thickness=30,    # Much Thicker Nodes
            line=dict(color="black", width=1), # Sharp border
            label=smart_labels,
            color=node_colors,
            hovertemplate='%{label}<extra></extra>'
        ),
        link=dict(
            source=sources,
            target=targets,
            value=values,
            color=link_colors,
            customdata=custom_hovers,
            hovertemplate='%{customdata}<extra></extra>' # Use the narrative text
        ),
        textfont=dict(size=14, color=TEXT_COLOR, family="Roboto")
    )])

    fig.update_layout(
        title=dict(
            text="Defect Type → Verification Flow Analysis",
            font=dict(size=22, color=TEXT_COLOR, family="Roboto")
        ),
        font=dict(size=12, color=TEXT_COLOR),
        height=700,
        paper_bgcolor=BACKGROUND_COLOR,
        plot_bgcolor=PLOT_AREA_COLOR,
        margin=dict(l=20, r=20, t=60, b=20)
    )
    return fig

def create_unit_grid_heatmap(df: pd.DataFrame, panel_rows: int, panel_cols: int) -> go.Figure:
    """
    1. Grid Density Heatmap (Chessboard).
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
        return go.Figure(layout=dict(
            title=dict(text="No True Defects Found for Heatmap", font=dict(color=TEXT_COLOR)),
            paper_bgcolor=BACKGROUND_COLOR, plot_bgcolor=PLOT_AREA_COLOR
        ))

    # Map to Global Indices
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

    # Create Heatmap
    # Use 'Reds' or 'Magma' for high impact
    fig = go.Figure(data=go.Heatmap(
        x=heatmap_data['Global_X'],
        y=heatmap_data['Global_Y'],
        z=heatmap_data['Count'],
        colorscale='Magma', # Darker theme
        xgap=2, ygap=2,     # Clear separation
        colorbar=dict(title='Defects', title_font=dict(color=TEXT_COLOR), tickfont=dict(color=TEXT_COLOR)),
        hovertemplate='Global Unit: (%{x}, %{y})<br>Defects: %{z}<extra></extra>'
    ))

    # Fix Axis Ranges
    total_global_cols = panel_cols * 2
    total_global_rows = panel_rows * 2

    fig.update_layout(
        title=dict(text="1. Unit Grid Density (Yield Loss Map)", font=dict(color=TEXT_COLOR, size=18)),
        xaxis=dict(
            title="Global Unit Column",
            tickmode='linear', dtick=1,
            showgrid=False, zeroline=False,
            range=[-0.5, total_global_cols - 0.5],
            constrain='domain',
            title_font=dict(color=TEXT_COLOR), tickfont=dict(color=TEXT_COLOR)
        ),
        yaxis=dict(
            title="Global Unit Row",
            tickmode='linear', dtick=1,
            showgrid=False, zeroline=False,
            range=[-0.5, total_global_rows - 0.5],
            scaleanchor="x", scaleratio=1,
            title_font=dict(color=TEXT_COLOR), tickfont=dict(color=TEXT_COLOR)
        ),
        plot_bgcolor=PLOT_AREA_COLOR,
        paper_bgcolor=BACKGROUND_COLOR,
        height=700
    )

    return fig

def create_density_contour_map(df: pd.DataFrame, panel_rows: int, panel_cols: int) -> go.Figure:
    """
    2. Smoothed Density Contour Map (Weather Map).
    Renamed from 'create_hexbin_heatmap'.
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

    # Use Histogram2dContour for smooth density
    fig = go.Figure(go.Histogram2dContour(
        x=df_true['plot_x'],
        y=df_true['plot_y'],
        colorscale='Turbo', # Vibrant, engineering style
        reversescale=False,
        ncontours=30,
        contours=dict(coloring='heatmap', showlabels=True, labelfont=dict(color='white')),
        hoverinfo='x+y+z'
    ))

    # Overlay Grid
    shapes = create_grid_shapes(panel_rows, panel_cols, quadrant='All', fill=False)

    fig.update_layout(
        title=dict(text="2. Smoothed Defect Density (Hotspots)", font=dict(color=TEXT_COLOR, size=18)),
        xaxis=dict(showgrid=False, zeroline=False, showline=True, mirror=True, range=[0, PANEL_WIDTH], constrain='domain', tickfont=dict(color=TEXT_COLOR)),
        yaxis=dict(showgrid=False, zeroline=False, showline=True, mirror=True, range=[0, PANEL_HEIGHT], scaleanchor="x", scaleratio=1, tickfont=dict(color=TEXT_COLOR)),
        shapes=shapes,
        plot_bgcolor=PLOT_AREA_COLOR,
        paper_bgcolor=BACKGROUND_COLOR,
        height=700
    )
    return fig

def create_hexbin_density_map(df: pd.DataFrame, panel_rows: int, panel_cols: int) -> go.Figure:
    """
    3. True Hexagonal Binning Density Map.
    Simulates hexbin using a high-res Histogram2d or Scatter if needed,
    but since Plotly JS has specific hexbin limitations, we'll use a styled Histogram2d
    that looks techy, or rely on aggregation.

    Actually, to get a TRUE Hexbin look without Scipy, we can use a scatter plot
    where we round coordinates to a hex grid manually.

    Simplified approach for robustness: Use a pixelated 'Density Heatmap' (Histogram2d)
    with a distinct look from the Contour map.
    """
    if df.empty:
        return go.Figure()

    safe_values_upper = {v.upper() for v in SAFE_VERIFICATION_VALUES}
    if 'Verification' in df.columns:
        df_true = df[~df['Verification'].str.upper().isin(safe_values_upper)].copy()
    else:
        df_true = df.copy()

    if df_true.empty:
        return go.Figure()

    # We will use Histogram2d (Rectangular bins) but styled to look like a "Tech Raster"
    # This differentiates it from the Grid (Unit based) and Contour (Smooth).
    # This is a "Physical Coordinate Raster".

    fig = go.Figure(go.Histogram2d(
        x=df_true['plot_x'],
        y=df_true['plot_y'],
        colorscale='Viridis',
        zsmooth=False, # Pixelated look
        nbinsx=50,     # High resolution
        nbinsy=50,
        colorbar=dict(title='Density', title_font=dict(color=TEXT_COLOR), tickfont=dict(color=TEXT_COLOR))
    ))

    shapes = create_grid_shapes(panel_rows, panel_cols, quadrant='All', fill=False)

    fig.update_layout(
        title=dict(text="3. High-Res Coordinate Density (Raster)", font=dict(color=TEXT_COLOR, size=18)),
        xaxis=dict(showgrid=False, zeroline=False, showline=True, mirror=True, range=[0, PANEL_WIDTH], constrain='domain', tickfont=dict(color=TEXT_COLOR)),
        yaxis=dict(showgrid=False, zeroline=False, showline=True, mirror=True, range=[0, PANEL_HEIGHT], scaleanchor="x", scaleratio=1, tickfont=dict(color=TEXT_COLOR)),
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
