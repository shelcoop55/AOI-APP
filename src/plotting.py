"""
Plotting and Visualization Module.
This version draws a true-to-scale simulation of a 510x510mm physical panel.
UPDATED: Now includes an outer border frame and has been refactored for clarity.
"""
import plotly.graph_objects as go
import pandas as pd
from typing import List, Dict, Any, Set, Tuple

from src.config import (
    PANEL_COLOR, GRID_COLOR, defect_style_map, TEXT_COLOR,
    PANEL_WIDTH, PANEL_HEIGHT, GAP_SIZE,
    ALIVE_CELL_COLOR, DEFECTIVE_CELL_COLOR
)
from src.data_handler import QUADRANT_WIDTH, QUADRANT_HEIGHT

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
        # Top Border
        dict(type="rect", x0=0, y0=total_height_with_gap, x1=total_width_with_gap, y1=total_height_with_gap + GAP_SIZE, fillcolor=gap_color, line_width=0, layer='below'),
        # Bottom Border
        dict(type="rect", x0=0, y0=-GAP_SIZE, x1=total_width_with_gap, y1=0, fillcolor=gap_color, line_width=0, layer='below'),
        # Left Border
        dict(type="rect", x0=-GAP_SIZE, y0=-GAP_SIZE, x1=0, y1=total_height_with_gap + GAP_SIZE, fillcolor=gap_color, line_width=0, layer='below'),
        # Right Border
        dict(type="rect", x0=total_width_with_gap, y0=-GAP_SIZE, x1=total_width_with_gap + GAP_SIZE, y1=total_height_with_gap + GAP_SIZE, fillcolor=gap_color, line_width=0, layer='below')
    ])

    # Inner gaps
    shapes.extend([
        # Vertical inner gap
        dict(type="rect", x0=QUADRANT_WIDTH, y0=0, x1=QUADRANT_WIDTH + GAP_SIZE, y1=total_height_with_gap, fillcolor=gap_color, line_width=0, layer='below'),
        # Horizontal inner gap
        dict(type="rect", x0=0, y0=QUADRANT_HEIGHT, x1=total_width_with_gap, y1=QUADRANT_HEIGHT + GAP_SIZE, fillcolor=gap_color, line_width=0, layer='below')
    ])
    return shapes

def _draw_quadrant_grids(origins_to_draw: Dict, panel_rows: int, panel_cols: int) -> List[Dict[str, Any]]:
    """Creates the shapes for the quadrant outlines and their internal grid lines."""
    shapes = []
    cell_width = QUADRANT_WIDTH / panel_cols
    cell_height = QUADRANT_HEIGHT / panel_rows

    for x_start, y_start in origins_to_draw.values():
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

def create_grid_shapes(panel_rows: int, panel_cols: int, quadrant: str = 'All') -> List[Dict[str, Any]]:
    """
    Creates the visual shapes for the panel grid in a fixed 510x510mm coordinate system.
    This function orchestrates calls to private helpers to build the grid.
    """
    all_origins = {
        'Q1': (0, 0),
        'Q2': (QUADRANT_WIDTH + GAP_SIZE, 0),
        'Q3': (0, QUADRANT_HEIGHT + GAP_SIZE),
        'Q4': (QUADRANT_WIDTH + GAP_SIZE, QUADRANT_HEIGHT + GAP_SIZE)
    }

    origins_to_draw = all_origins if quadrant == 'All' else {quadrant: all_origins[quadrant]}

    shapes = []
    if quadrant == 'All':
        shapes.extend(_draw_border_and_gaps())

    shapes.extend(_draw_quadrant_grids(origins_to_draw, panel_rows, panel_cols))

    return shapes

def create_defect_traces(df: pd.DataFrame) -> List[go.Scatter]:
    """
    Creates a list of scatter traces, one for each defect type in the dataframe.
    """
    traces = []

    # Check if the 'Verification' column exists to make the hovertemplate robust
    has_verification = 'Verification' in df.columns

    for dtype, color in defect_style_map.items():
        dff = df[df['DEFECT_TYPE'] == dtype]
        if not dff.empty:
            # Base custom data and hover template
            custom_data_cols = ['UNIT_INDEX_X', 'UNIT_INDEX_Y', 'DEFECT_TYPE', 'DEFECT_ID']
            hovertemplate = (
                "<b>Type: %{customdata[2]}</b><br>"
                "Unit Index (X, Y): (%{customdata[0]}, %{customdata[1]})<br>"
                "Defect ID: %{customdata[3]}"
            )

            # Add verification info only if the column exists
            if has_verification:
                custom_data_cols.append('Verification')
                hovertemplate += "<br>Verification: %{customdata[4]}"

            hovertemplate += "<extra></extra>"

            traces.append(go.Scatter(
                x=dff['plot_x'], y=dff['plot_y'], mode='markers',
                marker=dict(color=color, size=8, line=dict(width=1, color='black')),
                name=dtype,
                customdata=dff[custom_data_cols],
                hovertemplate=hovertemplate
            ))
    return traces
    
def create_pareto_trace(df: pd.DataFrame) -> go.Bar:
    """
    Creates a single bar trace for a Pareto chart.
    """
    if df.empty:
        return go.Bar(name='Pareto')
    pareto_data = df['DEFECT_TYPE'].value_counts().reset_index()
    pareto_data.columns = ['Defect Type', 'Count']
    return go.Bar(
        x=pareto_data['Defect Type'],
        y=pareto_data['Count'],
        name='Pareto',
        marker_color=[defect_style_map.get(dtype, 'grey') for dtype in pareto_data['Defect Type']]
    )

def create_grouped_pareto_trace(df: pd.DataFrame) -> List[go.Bar]:
    """
    Creates a list of bar traces for a grouped Pareto chart (by quadrant).
    """
    if df.empty:
        return []
    grouped_data = df.groupby(['QUADRANT', 'DEFECT_TYPE']).size().reset_index(name='Count')
    top_defects = df['DEFECT_TYPE'].value_counts().index.tolist()
    traces = []
    quadrants = ['Q1', 'Q2', 'Q3', 'Q4']
    for quadrant in quadrants:
        quadrant_data = grouped_data[grouped_data['QUADRANT'] == quadrant]
        pivot = quadrant_data.pivot(index='DEFECT_TYPE', columns='QUADRANT', values='Count').reindex(top_defects).fillna(0)
        if not pivot.empty:
            traces.append(go.Bar(
                name=quadrant,
                x=pivot.index,
                y=pivot[quadrant]
            ))
    return traces

def create_verification_status_chart(df: pd.DataFrame) -> List[go.Bar]:
    """
    Creates traces for a grouped, stacked bar chart showing the verification
    status (T, F, TA) for each defect type, grouped by quadrant.
    This is achieved by creating a multi-level x-axis and using barmode='stack'.
    """
    if df.empty:
        return []

    # 1. Prepare the data: Group by the three categories and get the size
    grouped = df.groupby(['DEFECT_TYPE', 'QUADRANT', 'Verification']).size().unstack(fill_value=0)

    # 2. Reindex to ensure all combinations are present for clean grouping.
    # This prevents missing bars and ensures consistent group spacing.
    all_defect_types = df['DEFECT_TYPE'].unique()
    all_quadrants = ['Q1', 'Q2', 'Q3', 'Q4']
    all_combinations = pd.MultiIndex.from_product(
        [all_defect_types, all_quadrants],
        names=['DEFECT_TYPE', 'QUADRANT']
    )
    grouped = grouped.reindex(all_combinations, fill_value=0)

    # 3. Ensure T, F, TA columns exist even if there's no data for them
    for status in ['T', 'F', 'TA']:
        if status not in grouped.columns:
            grouped[status] = 0

    grouped = grouped.reset_index()

    # 4. Define the multi-level x-axis data for Plotly
    x_axis_data = [grouped['DEFECT_TYPE'], grouped['QUADRANT']]

    # 5. Define colors and names for the legend
    status_map = {
        'T': {'name': 'True', 'color': '#FF0000'},
        'F': {'name': 'False', 'color': '#2ca02c'},
        'TA': {'name': 'Acceptable', 'color': '#FFBF00'}
    }

    # 6. Create a trace for each verification status
    traces = []
    for status_code, details in status_map.items():
        traces.append(go.Bar(
            name=details['name'],
            x=x_axis_data,
            y=grouped[status_code],
            marker_color=details['color']
        ))

    return traces

def create_still_alive_map(
    panel_rows: int,
    panel_cols: int,
    true_defect_coords: Set[Tuple[int, int]]
) -> List[Dict[str, Any]]:
    """
    Creates the shapes for the 'Still Alive' map, coloring cells based on defects.
    This version draws colored cells first, then overlays the grid lines.
    """
    shapes = []
    total_cols = panel_cols * 2
    total_rows = panel_rows * 2

    all_origins = {
        'Q1': (0, 0), 'Q2': (QUADRANT_WIDTH + GAP_SIZE, 0),
        'Q3': (0, QUADRANT_HEIGHT + GAP_SIZE), 'Q4': (QUADRANT_WIDTH + GAP_SIZE, QUADRANT_HEIGHT + GAP_SIZE)
    }
    cell_width = QUADRANT_WIDTH / panel_cols
    cell_height = QUADRANT_HEIGHT / panel_rows

    # 1. Draw the colored cells first (without borders)
    for row in range(total_rows):
        for col in range(total_cols):
            quadrant_col = col // panel_cols
            quadrant_row = row // panel_rows

            if quadrant_col == 0 and quadrant_row == 0: quad_key = 'Q1'
            elif quadrant_col == 1 and quadrant_row == 0: quad_key = 'Q2'
            elif quadrant_col == 0 and quadrant_row == 1: quad_key = 'Q3'
            else: quad_key = 'Q4'

            x_origin, y_origin = all_origins[quad_key]

            local_col = col % panel_cols
            local_row = row % panel_rows

            x0 = x_origin + local_col * cell_width
            y0 = y_origin + local_row * cell_height
            x1 = x0 + cell_width
            y1 = y0 + cell_height

            fill_color = DEFECTIVE_CELL_COLOR if (col, row) in true_defect_coords else ALIVE_CELL_COLOR

            shapes.append({
                'type': 'rect',
                'x0': x0, 'y0': y0, 'x1': x1, 'y1': y1,
                'fillcolor': fill_color,
                'line': {'width': 0},
                'layer': 'below'
            })

    # 2. Draw grid lines over the colored cells
    for quadrant_key, (x_start, y_start) in all_origins.items():
        # Draw vertical lines for the quadrant
        for i in range(panel_cols + 1):
            line_x = x_start + (i * cell_width)
            shapes.append(dict(type="line", x0=line_x, y0=y_start, x1=line_x, y1=y_start + QUADRANT_HEIGHT, line=dict(color=GRID_COLOR, width=1)))
        # Draw horizontal lines for the quadrant
        for i in range(panel_rows + 1):
            line_y = y_start + (i * cell_height)
            shapes.append(dict(type="line", x0=x_start, y0=line_y, x1=x_start + QUADRANT_WIDTH, y1=line_y, line=dict(color=GRID_COLOR, width=1)))

    # 3. Add the outer border and main quadrant gaps
    shapes.extend(_draw_border_and_gaps())

    return shapes
