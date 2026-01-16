"""
Plotting and Visualization Module.
This version draws a true-to-scale simulation of a 510x510mm physical panel.
UPDATED: Sankey charts with Neon Palette, 3 types of Heatmaps, and polished styling.
"""
import plotly.graph_objects as go
import pandas as pd
from typing import List, Dict, Any, Set, Tuple, Optional
import numpy as np

from src.config import (
    PANEL_COLOR, GRID_COLOR, defect_style_map, TEXT_COLOR, BACKGROUND_COLOR, PLOT_AREA_COLOR,
    PANEL_WIDTH, PANEL_HEIGHT, GAP_SIZE,
    ALIVE_CELL_COLOR, DEFECTIVE_CELL_COLOR, FALLBACK_COLORS, SAFE_VERIFICATION_VALUES,
    VERIFICATION_COLOR_SAFE, VERIFICATION_COLOR_DEFECT, NEON_PALETTE,
    UNIT_FACE_COLOR, UNIT_EDGE_COLOR, INTER_UNIT_GAP
)
from src.data_handler import StressMapData
from src.documentation import VERIFICATION_DESCRIPTIONS
from src.enums import Quadrant


# ==============================================================================
# --- Private Helper Functions for Grid Creation ---
# ==============================================================================

def _draw_border_and_gaps(ox: float = 0.0, oy: float = 0.0, gap_x: float = GAP_SIZE, gap_y: float = GAP_SIZE, panel_width: float = PANEL_WIDTH, panel_height: float = PANEL_HEIGHT) -> List[Dict[str, Any]]:
    """Creates the shapes for the outer border and inner gaps of the panel."""
    shapes = []
    # Use PANEL_COLOR for the frame/gaps (Rich Copper)
    gap_color = PANEL_COLOR
    total_width_with_gap = panel_width + gap_x
    total_height_with_gap = panel_height + gap_y

    quad_width = panel_width / 2
    quad_height = panel_height / 2

    # Outer border frame (Shifted by ox, oy)
    shapes.extend([
        # Bottom Border
        dict(type="rect", x0=0+ox, y0=total_height_with_gap+oy, x1=total_width_with_gap+ox, y1=total_height_with_gap + gap_y+oy, fillcolor=gap_color, line_width=0, layer='below'),
        # Top Border
        dict(type="rect", x0=0+ox, y0=-gap_y+oy, x1=total_width_with_gap+ox, y1=0+oy, fillcolor=gap_color, line_width=0, layer='below'),
        # Left Border
        dict(type="rect", x0=-gap_x+ox, y0=-gap_y+oy, x1=0+ox, y1=total_height_with_gap + gap_y+oy, fillcolor=gap_color, line_width=0, layer='below'),
        # Right Border
        dict(type="rect", x0=total_width_with_gap+ox, y0=-gap_y+oy, x1=total_width_with_gap + gap_x+ox, y1=total_height_with_gap + gap_y+oy, fillcolor=gap_color, line_width=0, layer='below')
    ])

    # Inner gaps
    shapes.extend([
        # Vertical Gap (separating Q1/Q3 from Q2/Q4) -> uses gap_x
        dict(type="rect", x0=quad_width+ox, y0=0+oy, x1=quad_width + gap_x+ox, y1=total_height_with_gap+oy, fillcolor=gap_color, line_width=0, layer='below'),
        # Horizontal Gap (separating Q1/Q2 from Q3/Q4) -> uses gap_y
        dict(type="rect", x0=0+ox, y0=quad_height+oy, x1=total_width_with_gap+ox, y1=quad_height + gap_y+oy, fillcolor=gap_color, line_width=0, layer='below')
    ])
    return shapes

def _draw_quadrant_grids(origins_to_draw: Dict, panel_rows: int, panel_cols: int, fill: bool = True, panel_width: float = PANEL_WIDTH, panel_height: float = PANEL_HEIGHT) -> List[Dict[str, Any]]:
    """Creates the shapes for the quadrant units with inter-unit gaps."""
    shapes = []
    quad_width = panel_width / 2
    quad_height = panel_height / 2

    # Calculate Cell Pitch (Center-to-Center distance)
    # The 'grid' logic in models.py assumes uniform cells summing to quad_width.
    cell_pitch_x = quad_width / panel_cols
    cell_pitch_y = quad_height / panel_rows

    # Calculate Actual Unit Size (subtracting inter-unit gap)
    # Spec: Unit Width = (Quad_W - (Gaps)) / Cols?
    # Actually, let's assume the Inter-Unit Gap is centered on the grid line.
    # So the unit rectangle is slightly smaller than the cell pitch.
    # Unit_W = Pitch_X - Gap? Or Pitch_X - (Gap * (N-1)/N)?
    # To be consistent with "5 gaps for 6 units" logic:
    # Total Width = N * Unit + (N-1) * Gap.
    # But our grid logic assumes N * Cell = Total.
    # So Cell = Unit + (N-1)/N * Gap.
    # This is getting complicated to align with models.py.

    # Simple approach for Visualization:
    # Shrink the rectangle by INTER_UNIT_GAP/2 on all sides relative to the cell boundary.
    # This creates a gap of INTER_UNIT_GAP between adjacent units.

    half_gap = INTER_UNIT_GAP / 2.0

    for x_start, y_start in origins_to_draw.values():
        # Draw Quadrant Background (The Gaps)
        if fill:
            shapes.append(dict(
                type="rect", x0=x_start, y0=y_start, x1=x_start + quad_width, y1=y_start + quad_height,
                line_width=0, fillcolor=PANEL_COLOR, layer='below'
            ))

        # Draw Individual Units
        for r in range(panel_rows):
            for c in range(panel_cols):
                # Cell Boundaries
                x0 = x_start + (c * cell_pitch_x)
                y0 = y_start + (r * cell_pitch_y)
                x1 = x0 + cell_pitch_x
                y1 = y0 + cell_pitch_y

                # Unit Rect (Shrunk)
                # Ensure we don't shrink into negative if gap is too large
                ux0 = x0 + half_gap
                uy0 = y0 + half_gap
                ux1 = x1 - half_gap
                uy1 = y1 - half_gap

                if fill:
                    shapes.append(dict(
                        type="rect",
                        x0=ux0, y0=uy0, x1=ux1, y1=uy1,
                        line=dict(color=UNIT_EDGE_COLOR, width=1),
                        fillcolor=UNIT_FACE_COLOR,
                        layer='below'
                    ))
                else:
                    # Wireframe mode (just grid lines)
                    # We replicate the 'line' logic from previous implementation but per unit?
                    # Or just standard grid lines?
                    # If fill=False (e.g. overlays), we usually just want lines.
                    # Previous logic drew lines across.
                    pass

    # If fill is False, we might want to draw the grid lines (Inter-unit gaps)
    # But usually fill=False is used when we want to see Heatmap underneath.
    # If Heatmap is active, drawing solid unit faces blocks it.
    # So if fill=False, we draw Border of units only? Or just standard grid lines.
    # Let's stick to standard grid lines for fill=False to avoid clutter.
    if not fill:
         for x_start, y_start in origins_to_draw.values():
            shapes.append(dict(
                type="rect", x0=x_start, y0=y_start, x1=x_start + quad_width, y1=y_start + quad_height,
                line=dict(color=GRID_COLOR, width=2), fillcolor='rgba(0,0,0,0)', layer='below'
            ))
            for i in range(1, panel_cols):
                line_x = x_start + (i * cell_pitch_x)
                shapes.append(dict(type="line", x0=line_x, y0=y_start, x1=line_x, y1=y_start + quad_height, line=dict(color=GRID_COLOR, width=1, dash='solid'), opacity=0.5, layer='below'))
            for i in range(1, panel_rows):
                line_y = y_start + (i * cell_pitch_y)
                shapes.append(dict(type="line", x0=x_start, y0=line_y, x1=x_start + quad_width, y1=line_y, line=dict(color=GRID_COLOR, width=1, dash='solid'), opacity=0.5, layer='below'))

    return shapes

# ==============================================================================
# --- Public API Functions ---
# ==============================================================================

def apply_panel_theme(fig: go.Figure, title: str = "", height: int = 800) -> go.Figure:
    """
    Applies the standard engineering styling to any figure.
    This centralized function replaces redundant layout code in specific plotting functions.
    """
    fig.update_layout(
        title=dict(text=title, font=dict(color=TEXT_COLOR, size=18), x=0.5, xanchor='center'),
        plot_bgcolor=PLOT_AREA_COLOR,
        paper_bgcolor=BACKGROUND_COLOR,
        height=height,
        font=dict(color=TEXT_COLOR),
        # Default Axis Styling (can be overridden)
        xaxis=dict(
            showgrid=False, zeroline=False, showline=True,
            linewidth=2, linecolor=GRID_COLOR, mirror=True,
            title_font=dict(color=TEXT_COLOR), tickfont=dict(color=TEXT_COLOR)
        ),
        yaxis=dict(
            showgrid=False, zeroline=False, showline=True,
            linewidth=2, linecolor=GRID_COLOR, mirror=True,
            title_font=dict(color=TEXT_COLOR), tickfont=dict(color=TEXT_COLOR),
            scaleanchor="x", scaleratio=1
        ),
        legend=dict(
            title_font=dict(color=TEXT_COLOR), font=dict(color=TEXT_COLOR),
            bgcolor=BACKGROUND_COLOR, bordercolor=GRID_COLOR, borderwidth=1,
            x=1.02, y=1, xanchor='left', yanchor='top'
        ),
        hoverlabel=dict(bgcolor="#4A4A4A", font_size=14, font_family="sans-serif")
    )
    return fig

def create_grid_shapes(panel_rows: int, panel_cols: int, quadrant: str = 'All', fill: bool = True, offset_x: float = 0.0, offset_y: float = 0.0, gap_x: float = GAP_SIZE, gap_y: float = GAP_SIZE, panel_width: float = PANEL_WIDTH, panel_height: float = PANEL_HEIGHT) -> List[Dict[str, Any]]:
    """
    Creates the visual shapes for the panel grid in a fixed 510x510mm coordinate system.
    Supports shifting origin via offset_x/y and dynamic gap.
    """
    quad_width = panel_width / 2
    quad_height = panel_height / 2

    all_origins = {
        'Q1': (0 + offset_x, 0 + offset_y),
        'Q2': (quad_width + gap_x + offset_x, 0 + offset_y),
        'Q3': (0 + offset_x, quad_height + gap_y + offset_y),
        'Q4': (quad_width + gap_x + offset_x, quad_height + gap_y + offset_y)
    }
    origins_to_draw = all_origins if quadrant == 'All' else {quadrant: all_origins[quadrant]}
    shapes = []
    if quadrant == 'All':
        shapes.extend(_draw_border_and_gaps(offset_x, offset_y, gap_x, gap_y, panel_width, panel_height))

    shapes.extend(_draw_quadrant_grids(origins_to_draw, panel_rows, panel_cols, fill=fill, panel_width=panel_width, panel_height=panel_height))
    return shapes

def create_defect_traces(df: pd.DataFrame, offset_x: float = 0.0, offset_y: float = 0.0, gap_x: float = GAP_SIZE, gap_y: float = GAP_SIZE) -> List[go.Scatter]:
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

    # Generate traces using GroupBy (Optimization #4)
    # 1. Pre-calculate Descriptions globally
    if 'Verification' in df.columns:
        # Avoid SettingWithCopyWarning if df is a slice
        df = df.copy()
        df['Description'] = df['Verification'].map(VERIFICATION_DESCRIPTIONS).fillna("Unknown Code")
    else:
        df = df.copy()
        df['Description'] = "N/A"

    # 2. Pre-calculate Raw Coords globally
    has_raw_coords = 'X_COORDINATES' in df.columns and 'Y_COORDINATES' in df.columns
    coord_str = ""
    if has_raw_coords:
        df['RAW_COORD_STR'] = df.apply(lambda row: f"({row['X_COORDINATES']/1000:.2f}, {row['Y_COORDINATES']/1000:.2f}) mm", axis=1)
        custom_data_cols = ['UNIT_INDEX_X', 'UNIT_INDEX_Y', 'DEFECT_TYPE', 'DEFECT_ID', 'Verification', 'Description', 'RAW_COORD_STR']
        coord_str = "<br>Raw Coords: %{customdata[6]}"
    else:
        custom_data_cols = ['UNIT_INDEX_X', 'UNIT_INDEX_Y', 'DEFECT_TYPE', 'DEFECT_ID', 'Verification', 'Description']

    # 3. GroupBy Loop
    grouped = df.groupby(group_col, observed=True)

    for group_val, dff in grouped:
        if group_val not in local_style_map:
            continue

        color = local_style_map[group_val]

        hovertemplate = ("<b>Status: %{customdata[4]}</b><br>"
                            "Description : %{customdata[5]}<br>"
                            "Type: %{customdata[2]}<br>"
                            "Unit Index (X, Y): (%{customdata[0]}, %{customdata[1]})<br>"
                            "Defect ID: %{customdata[3]}"
                            + coord_str +
                            "<extra></extra>")

        x_vals = dff['plot_x'] + offset_x
        y_vals = dff['plot_y'] + offset_y

        traces.append(go.Scattergl(
            x=x_vals,
            y=y_vals,
            mode='markers',
            marker=dict(color=color, size=8, line=dict(width=1, color='black')),
            name=str(group_val),
            customdata=dff[custom_data_cols],
            hovertemplate=hovertemplate
        ))

    return traces

def create_multi_layer_defect_map(
    df: pd.DataFrame,
    panel_rows: int,
    panel_cols: int,
    flip_back: bool = True,
    offset_x: float = 0.0,
    offset_y: float = 0.0,
    gap_x: float = GAP_SIZE,
    gap_y: float = GAP_SIZE,
    panel_width: float = PANEL_WIDTH,
    panel_height: float = PANEL_HEIGHT
) -> go.Figure:
    """
    Creates a defect map visualizing defects from ALL layers simultaneously.
    Supports toggling Back Side alignment (Flip vs Raw).
    """
    fig = go.Figure()

    if not df.empty:
        # Ensure LAYER_NUM exists
        if 'LAYER_NUM' not in df.columns:
            df['LAYER_NUM'] = 0

        unique_layer_nums = sorted(df['LAYER_NUM'].unique())

        # Generate colors
        layer_colors = {}
        for i, num in enumerate(unique_layer_nums):
            layer_colors[num] = FALLBACK_COLORS[i % len(FALLBACK_COLORS)]

        symbol_map = {'F': 'circle', 'B': 'diamond'}

        for layer_num in unique_layer_nums:
            layer_color = layer_colors[layer_num]
            layer_df = df[df['LAYER_NUM'] == layer_num]

            for side in sorted(layer_df['SIDE'].unique()):
                dff = layer_df[layer_df['SIDE'] == side]
                symbol = symbol_map.get(side, 'circle')
                side_name = "Front" if side == 'F' else "Back"
                trace_name = f"Layer {layer_num} ({side_name})"

                if 'Verification' in dff.columns:
                     dff = dff.copy()
                     dff['Description'] = dff['Verification'].map(VERIFICATION_DESCRIPTIONS).fillna("Unknown Code")
                else:
                     dff['Description'] = "N/A"

                # Prepare Custom Data (Include Raw Coords - Convert um to mm)
                coord_str = ""
                if 'X_COORDINATES' in dff.columns and 'Y_COORDINATES' in dff.columns:
                    dff['RAW_COORD_STR'] = dff.apply(lambda row: f"({row['X_COORDINATES']/1000:.2f}, {row['Y_COORDINATES']/1000:.2f}) mm", axis=1)
                    custom_data_cols = ['UNIT_INDEX_X', 'UNIT_INDEX_Y', 'DEFECT_TYPE', 'DEFECT_ID', 'Verification', 'Description', 'SOURCE_FILE', 'RAW_COORD_STR']
                    coord_str = "<br>Raw Coords: %{customdata[7]}"
                else:
                    custom_data_cols = ['UNIT_INDEX_X', 'UNIT_INDEX_Y', 'DEFECT_TYPE', 'DEFECT_ID', 'Verification', 'Description', 'SOURCE_FILE']

                # Fix Hover Template
                hovertemplate = (f"<b>Layer: {layer_num}</b><br>"
                                 "Side: " + side_name + "<br>"
                                 "Status: %{customdata[4]}<br>"
                                 "Type: %{customdata[2]}<br>"
                                 "Unit Index: (%{customdata[0]}, %{customdata[1]})<br>"
                                 "File: %{customdata[6]}"
                                 + coord_str +
                                 "<extra></extra>")

                # Determine X Coordinates based on Flip Toggle
                # We use the pre-calculated columns from models.py
                if flip_back:
                    x_col_name = 'physical_plot_x_flipped'
                else:
                    x_col_name = 'physical_plot_x_raw'

                x_coords = dff[x_col_name]

                # OPTIMIZATION: Use WebGL
                fig.add_trace(go.Scattergl(
                    x=x_coords + offset_x,
                    y=dff['plot_y'] + offset_y,
                    mode='markers',
                    marker=dict(
                        color=layer_color,
                        symbol=symbol,
                        size=9,
                        line=dict(width=1, color='black')
                    ),
                    name=trace_name,
                    customdata=dff[custom_data_cols],
                    hovertemplate=hovertemplate
                ))

    # Add Grid
    fig.update_layout(shapes=create_grid_shapes(panel_rows, panel_cols, quadrant='All', offset_x=offset_x, offset_y=offset_y, gap_x=gap_x, gap_y=gap_y, panel_width=panel_width, panel_height=panel_height))

    quad_width = panel_width / 2
    quad_height = panel_height / 2

    # Calculate ticks (reused from standard map logic)
    cell_width, cell_height = quad_width / panel_cols, quad_height / panel_rows
    x_tick_vals_q1 = [(i * cell_width) + (cell_width / 2) + offset_x for i in range(panel_cols)]
    x_tick_vals_q2 = [(quad_width + gap_x) + (i * cell_width) + (cell_width / 2) + offset_x for i in range(panel_cols)]
    y_tick_vals_q1 = [(i * cell_height) + (cell_height / 2) + offset_y for i in range(panel_rows)]
    y_tick_vals_q3 = [(quad_height + gap_y) + (i * cell_height) + (cell_height / 2) + offset_y for i in range(panel_rows)]
    x_tick_text = list(range(panel_cols * 2))
    y_tick_text = list(range(panel_rows * 2))

    apply_panel_theme(fig, "Multi-Layer Combined Defect Map (True Defects Only)")

    fig.update_layout(
        xaxis=dict(
            title="Unit Column Index",
            tickvals=x_tick_vals_q1 + x_tick_vals_q2,
            ticktext=x_tick_text,
            range=[offset_x, offset_x + panel_width + gap_x], constrain='domain'
        ),
        yaxis=dict(
            title="Unit Row Index",
            tickvals=y_tick_vals_q1 + y_tick_vals_q3,
            ticktext=y_tick_text,
            range=[offset_y, offset_y + panel_height + gap_y]
        ),
        legend=dict(title=dict(text="Build-Up Layer"))
    )

    return fig
    
def create_defect_map_figure(df: pd.DataFrame, panel_rows: int, panel_cols: int, quadrant_selection: str = Quadrant.ALL.value, lot_number: Optional[str] = None, title: Optional[str] = None, offset_x: float = 0.0, offset_y: float = 0.0, gap_x: float = GAP_SIZE, gap_y: float = GAP_SIZE, panel_width: float = PANEL_WIDTH, panel_height: float = PANEL_HEIGHT) -> go.Figure:
    """
    Creates the full Defect Map Figure (Traces + Grid + Layout).
    """
    # Use Dynamic Dimensions
    quad_width = panel_width / 2
    quad_height = panel_height / 2

    fig = go.Figure(data=create_defect_traces(df, offset_x=offset_x, offset_y=offset_y, gap_x=gap_x, gap_y=gap_y))
    fig.update_layout(shapes=create_grid_shapes(panel_rows, panel_cols, quadrant_selection, offset_x=offset_x, offset_y=offset_y, gap_x=gap_x, gap_y=gap_y, panel_width=panel_width, panel_height=panel_height))

    # Calculate ticks and ranges with offsets
    cell_width, cell_height = quad_width / panel_cols, quad_height / panel_rows
    x_tick_vals_q1 = [(i * cell_width) + (cell_width / 2) + offset_x for i in range(panel_cols)]
    x_tick_vals_q2 = [(quad_width + gap_x) + (i * cell_width) + (cell_width / 2) + offset_x for i in range(panel_cols)]
    y_tick_vals_q1 = [(i * cell_height) + (cell_height / 2) + offset_y for i in range(panel_rows)]
    y_tick_vals_q3 = [(quad_height + gap_y) + (i * cell_height) + (cell_height / 2) + offset_y for i in range(panel_rows)]
    x_tick_text, y_tick_text = list(range(panel_cols * 2)), list(range(panel_rows * 2))

    x_axis_range = [offset_x, offset_x + panel_width + gap_x]
    y_axis_range = [offset_y, offset_y + panel_height + gap_y]
    show_ticks = True

    if quadrant_selection != Quadrant.ALL.value:
        show_ticks = False
        ranges = {
            'Q1': ([0+offset_x, quad_width+offset_x], [0+offset_y, quad_height+offset_y]),
            'Q2': ([quad_width + gap_x+offset_x, panel_width + gap_x+offset_x], [0+offset_y, quad_height+offset_y]),
            'Q3': ([0+offset_x, quad_width+offset_x], [quad_height + gap_y+offset_y, panel_height + gap_y+offset_y]),
            'Q4': ([quad_width + gap_x+offset_x, panel_width + gap_x+offset_x], [quad_height + gap_y+offset_y, panel_height + gap_y+offset_y])
        }
        x_axis_range, y_axis_range = ranges[quadrant_selection]

    final_title = title if title else f"Panel Defect Map - Quadrant: {quadrant_selection}"

    apply_panel_theme(fig, final_title)

    fig.update_layout(
        xaxis=dict(title="Unit Column Index", tickvals=x_tick_vals_q1 + x_tick_vals_q2 if show_ticks else [], ticktext=x_tick_text if show_ticks else [], range=x_axis_range, constrain='domain'),
        yaxis=dict(title="Unit Row Index", tickvals=y_tick_vals_q1 + y_tick_vals_q3 if show_ticks else [], ticktext=y_tick_text if show_ticks else [], range=y_axis_range)
    )

    if lot_number and quadrant_selection == Quadrant.ALL.value:
        fig.add_annotation(x=panel_width + gap_x + offset_x, y=panel_height + gap_y + offset_y, text=f"<b>Lot #: {lot_number}</b>", showarrow=False, font=dict(size=14, color=TEXT_COLOR), align="right", xanchor="right", yanchor="bottom")

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

    grouped_data = df.groupby(['QUADRANT', group_col], observed=True).size().reset_index(name='Count')
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

    apply_panel_theme(fig, f"Defect Pareto - Quadrant: {quadrant_selection}", height=600)

    fig.update_layout(
        xaxis=dict(title="Defect Type", categoryorder='total descending'),
        yaxis=dict(showgrid=True) # Override to show grid on Pareto
    )
    return fig

def create_verification_status_chart(df: pd.DataFrame) -> List[go.Bar]:
    if df.empty: return []
    grouped = df.groupby(['DEFECT_TYPE', 'QUADRANT', 'Verification'], observed=True).size().unstack(fill_value=0)
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

def create_still_alive_map(
    panel_rows: int,
    panel_cols: int,
    true_defect_data: Dict[Tuple[int, int], Dict[str, Any]],
    offset_x: float = 0.0,
    offset_y: float = 0.0,
    gap_x: float = GAP_SIZE,
    gap_y: float = GAP_SIZE,
    panel_width: float = PANEL_WIDTH,
    panel_height: float = PANEL_HEIGHT
) -> Tuple[List[Dict[str, Any]], List[go.Scatter]]:
    """
    Creates the shapes for the 'Still Alive' map AND invisible scatter points for tooltips.
    """
    shapes = []
    traces = []

    quad_width = panel_width / 2
    quad_height = panel_height / 2

    total_cols, total_rows = panel_cols * 2, panel_rows * 2
    all_origins = {
        'Q1': (0 + offset_x, 0 + offset_y),
        'Q2': (quad_width + gap_x + offset_x, 0 + offset_y),
        'Q3': (0 + offset_x, quad_height + gap_y + offset_y),
        'Q4': (quad_width + gap_x + offset_x, quad_height + gap_y + offset_y)
    }
    cell_width, cell_height = quad_width / panel_cols, quad_height / panel_rows

    # Prepare lists for scatter trace (Tooltips)
    hover_x = []
    hover_y = []
    hover_text = []
    hover_colors = []

    # 1. Draw the colored cells first (without borders)
    for row in range(total_rows):
        for col in range(total_cols):
            quadrant_col, local_col = divmod(col, panel_cols)
            quadrant_row, local_row = divmod(row, panel_rows)
            quad_key = f"Q{quadrant_row * 2 + quadrant_col + 1}"
            x_origin, y_origin = all_origins[quad_key]
            x0, y0 = x_origin + local_col * cell_width, y_origin + local_row * cell_height

            # Determine status
            is_dead = (col, row) in true_defect_data

            if is_dead:
                metadata = true_defect_data[(col, row)]
                first_killer = metadata['first_killer_layer']

                # Color logic: Revert to binary RED for all defects
                fill_color = DEFECTIVE_CELL_COLOR

                # Add to hover data (Keep Autopsy Tooltip)
                center_x = x0 + cell_width/2
                center_y = y0 + cell_height/2
                hover_x.append(center_x)
                hover_y.append(center_y)

                tooltip = (
                    f"<b>Unit: ({col}, {row})</b><br>"
                    f"First Killer: Layer {first_killer}<br>"
                    f"Details: {metadata['defect_summary']}"
                )
                hover_text.append(tooltip)
                # Hover dots should also match the cell color (Red) to be invisible
                hover_colors.append(fill_color)

            else:
                fill_color = ALIVE_CELL_COLOR

            shapes.append({'type': 'rect', 'x0': x0, 'y0': y0, 'x1': x0 + cell_width, 'y1': y0 + cell_height, 'fillcolor': fill_color, 'line': {'width': 0}, 'layer': 'below'})

    # 2. Draw grid lines over the colored cells
    shapes.extend(create_grid_shapes(panel_rows, panel_cols, quadrant='All', fill=False, offset_x=offset_x, offset_y=offset_y, gap_x=gap_x, gap_y=gap_y, panel_width=panel_width, panel_height=panel_height))

    # 3. Create Scatter Trace for Hover
    if hover_x:
        traces.append(go.Scatter(
            x=hover_x,
            y=hover_y,
            mode='markers',
            marker=dict(size=0, color=hover_colors, opacity=0), # Invisible markers
            text=hover_text,
            hoverinfo='text'
        ))

    return shapes, traces

def create_still_alive_figure(
    panel_rows: int,
    panel_cols: int,
    true_defect_data: Dict[Tuple[int, int], Dict[str, Any]],
    offset_x: float = 0.0,
    offset_y: float = 0.0,
    gap_x: float = GAP_SIZE,
    gap_y: float = GAP_SIZE,
    panel_width: float = PANEL_WIDTH,
    panel_height: float = PANEL_HEIGHT
) -> go.Figure:
    """
    Creates the Still Alive Map Figure (Shapes + Layout + Tooltips).
    """
    map_shapes, hover_traces = create_still_alive_map(panel_rows, panel_cols, true_defect_data, offset_x=offset_x, offset_y=offset_y, gap_x=gap_x, gap_y=gap_y, panel_width=panel_width, panel_height=panel_height)

    fig = go.Figure(data=hover_traces) # Add hover traces

    quad_width = panel_width / 2
    quad_height = panel_height / 2

    cell_width, cell_height = quad_width / panel_cols, quad_height / panel_rows
    x_tick_vals_q1 = [(i * cell_width) + (cell_width / 2) + offset_x for i in range(panel_cols)]
    x_tick_vals_q2 = [(quad_width + gap_x) + (i * cell_width) + (cell_width / 2) + offset_x for i in range(panel_cols)]
    y_tick_vals_q1 = [(i * cell_height) + (cell_height / 2) + offset_y for i in range(panel_rows)]
    y_tick_vals_q3 = [(quad_height + gap_y) + (i * cell_height) + (cell_height / 2) + offset_y for i in range(panel_rows)]
    x_tick_text = list(range(panel_cols * 2))
    y_tick_text = list(range(panel_rows * 2))

    apply_panel_theme(fig, f"Still Alive Map ({len(true_defect_data)} Defective Cells)")

    fig.update_layout(
        xaxis=dict(
            title="Unit Column Index", range=[offset_x, offset_x + panel_width + gap_x], constrain='domain',
            tickvals=x_tick_vals_q1 + x_tick_vals_q2, ticktext=x_tick_text
        ),
        yaxis=dict(
            title="Unit Row Index", range=[offset_y, offset_y + panel_height + gap_y],
            tickvals=y_tick_vals_q1 + y_tick_vals_q3, ticktext=y_tick_text
        ),
        shapes=map_shapes, margin=dict(l=20, r=20, t=80, b=20),
        showlegend=False
    )
    return fig

def create_density_contour_map(
    df: pd.DataFrame,
    panel_rows: int,
    panel_cols: int,
    show_points: bool = False,
    smoothing_factor: int = 30,
    saturation_cap: int = 0,
    show_grid: bool = True,
    view_mode: str = "Continuous",
    flip_back: bool = False,
    quadrant_selection: str = 'All',
    offset_x: float = 0.0,
    offset_y: float = 0.0,
    gap_x: float = GAP_SIZE,
    gap_y: float = GAP_SIZE,
    panel_width: float = PANEL_WIDTH,
    panel_height: float = PANEL_HEIGHT
) -> go.Figure:
    """
    2. Smoothed Density Contour Map (OPTIMIZED).
    Uses Server-Side aggregation (numpy.histogram2d) instead of client-side computation.
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

    # Determine X Coordinates based on Toggle
    if 'physical_plot_x_flipped' in df_true.columns:
        x_col_name = 'physical_plot_x_flipped' if flip_back else 'physical_plot_x_raw'
    else:
        x_col_name = 'plot_x'

    # Apply Dynamic Gap Correction
    # Since models.py already applies gap_x to 'plot_x' etc, we might not need this.

    df_true['plot_x_corrected'] = df_true[x_col_name]
    df_true['plot_y_corrected'] = df_true['plot_y']

    x_col = 'plot_x_corrected'

    fig = go.Figure()

    scale_factor = 10.0 / max(1, smoothing_factor)

    # Dynamic Binning
    bins_x = max(10, int((panel_cols * 2) * 2 * scale_factor))
    bins_y = max(10, int((panel_rows * 2) * 2 * scale_factor))

    num_bins = [bins_y, bins_x]

    # Boundary Definitions with Offsets
    x_min, x_max = offset_x, panel_width + gap_x + offset_x
    y_min, y_max = offset_y, panel_height + gap_y + offset_y

    def aggregate_quadrant(q_df, x_range, y_range):
        if q_df.empty:
            return None, None, None, None, None

        # Apply offsets to data before binning
        x_c = q_df[x_col].values + offset_x
        y_c = q_df['plot_y_corrected'].values + offset_y

        # 1. Density (Z)
        H, x_edges, y_edges = np.histogram2d(x_c, y_c, bins=num_bins, range=[x_range, y_range])

        # 2. Dominant Defect Driver (Mode)
        if 'DEFECT_TYPE' in q_df.columns:
            unique_types = q_df['DEFECT_TYPE'].unique()
            if len(unique_types) > 10:
                top_types = q_df['DEFECT_TYPE'].value_counts().nlargest(10).index.tolist()
                unique_types = top_types

            type_grids = []
            type_labels = []

            for dtype in unique_types:
                sub_df = q_df[q_df['DEFECT_TYPE'] == dtype]
                if not sub_df.empty:
                    sub_x = sub_df[x_col] + offset_x
                    sub_y = sub_df['plot_y_corrected'] + offset_y
                    h_sub, _, _ = np.histogram2d(sub_x, sub_y, bins=num_bins, range=[x_range, y_range])
                    type_grids.append(h_sub)
                    type_labels.append(dtype)

            if type_grids:
                stack = np.stack(type_grids, axis=0)
                max_indices = np.argmax(stack, axis=0)
                driver_map = np.empty(max_indices.shape, dtype=object)
                for idx, label in enumerate(type_labels):
                    driver_map[max_indices == idx] = label
                driver_map[H == 0] = ""
                driver_text = driver_map.T
            else:
                driver_text = None
        else:
            driver_text = None

        x_centers = (x_edges[:-1] + x_edges[1:]) / 2
        y_centers = (y_edges[:-1] + y_edges[1:]) / 2

        return H.T, x_centers, y_centers, driver_text

    weights = None

    H, x_centers, y_centers, driver_text_t = aggregate_quadrant(
        df_true,
        [x_min, x_max],
        [y_min, y_max]
    )

    if H is None:
        return go.Figure(layout=dict(title="Error in Aggregation"))

    Z = H

    # Masking Gap (Shifted by offset)
    quad_width = panel_width / 2
    quad_height = panel_height / 2

    gap_x_start = quad_width + offset_x
    gap_x_end = quad_width + gap_x + offset_x
    gap_y_start = quad_height + offset_y
    gap_y_end = quad_height + gap_y + offset_y

    mask_x = (x_centers > gap_x_start) & (x_centers < gap_x_end)
    mask_y = (y_centers > gap_y_start) & (y_centers < gap_y_end)

    Z[np.ix_(mask_y, mask_x)] = np.nan
    Z[:, mask_x] = 0
    Z[mask_y, :] = 0

    if driver_text_t is not None:
        driver_text_t[np.ix_(mask_y, mask_x)] = ""
        driver_text_t[:, mask_x] = ""
        driver_text_t[mask_y, :] = ""

        hovertemplate = 'X: %{x:.1f}mm<br>Y: %{y:.1f}mm<br>Density: %{z:.0f}<br>Top Cause: %{text}<extra></extra>'
        text_arg = driver_text_t
    else:
        hovertemplate = 'X: %{x:.1f}mm<br>Y: %{y:.1f}mm<br>Density: %{z:.0f}<extra></extra>'
        text_arg = None

    fig.add_trace(go.Contour(
        z=Z,
        x=x_centers,
        y=y_centers,
        text=text_arg,
        colorscale='Turbo',
        contours=dict(
            coloring='heatmap',
            showlabels=True,
            labelfont=dict(color='white')
        ),
        zmin=0,
        zmax=saturation_cap if saturation_cap > 0 else None,
        hoverinfo='x+y+z+text' if text_arg is not None else 'x+y+z',
        hovertemplate=hovertemplate
    ))

    # 2. Points Overlay
    if show_points:
        fig.add_trace(go.Scattergl(
            x=df_true[x_col] + offset_x,
            y=df_true['plot_y_corrected'] + offset_y,
            mode='markers',
            marker=dict(color='white', size=3, opacity=0.5),
            hoverinfo='skip',
            name='Defects'
        ))

    # 3. Grid Overlay
    shapes = []
    if show_grid:
        shapes = create_grid_shapes(panel_rows, panel_cols, quadrant='All', fill=False, offset_x=offset_x, offset_y=offset_y, gap_x=gap_x, gap_y=gap_y, panel_width=panel_width, panel_height=panel_height)

    # 4. Axis Labels
    x_tick_vals = []
    x_tick_text = []
    for i in range(total_cols):
        offset = gap_x if i >= panel_cols else 0
        center_mm = (i * cell_width) + (cell_width / 2) + offset + offset_x
        x_tick_vals.append(center_mm)
        x_tick_text.append(str(i))

    y_tick_vals = []
    y_tick_text = []
    for i in range(total_rows):
        offset = gap_y if i >= panel_rows else 0
        center_mm = (i * cell_height) + (cell_height / 2) + offset + offset_y
        y_tick_vals.append(center_mm)
        y_tick_text.append(str(i))

    x_axis_range = [offset_x, offset_x + panel_width + gap_x]
    y_axis_range = [offset_y, offset_y + panel_height + gap_y]

    if quadrant_selection != 'All':
        ranges = {
            'Q1': ([offset_x, offset_x + quad_width], [offset_y, offset_y + quad_height]),
            'Q2': ([offset_x + quad_width + gap_x, offset_x + panel_width + gap_x], [offset_y, offset_y + quad_height]),
            'Q3': ([offset_x, offset_x + quad_width], [offset_y + quad_height + gap_y, offset_y + panel_height + gap_y]),
            'Q4': ([offset_x + quad_width + gap_x, offset_x + panel_width + gap_x], [offset_y + quad_height + gap_y, offset_y + panel_height + gap_y])
        }
        x_axis_range, y_axis_range = ranges[quadrant_selection]

    apply_panel_theme(fig, "Smooth Density Hotspot (Server-Side Aggregated)", height=700)

    fig.update_layout(
        xaxis=dict(
            title="Unit Column Index (Approx)",
            tickvals=x_tick_vals,
            ticktext=x_tick_text,
            range=x_axis_range, constrain='domain'
        ),
        yaxis=dict(
            title="Unit Row Index (Approx)",
            tickvals=y_tick_vals,
            ticktext=y_tick_text,
            range=y_axis_range
        ),
        shapes=shapes
    )
    return fig
