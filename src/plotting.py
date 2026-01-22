"""
Plotting and Visualization Module.
This version draws a true-to-scale simulation of a 510x510mm physical panel.
"""
import plotly.graph_objects as go
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import streamlit as st

from src.config import (
    PANEL_COLOR, GRID_COLOR, defect_style_map, TEXT_COLOR, BACKGROUND_COLOR, PLOT_AREA_COLOR,
    PANEL_WIDTH, PANEL_HEIGHT, GAP_SIZE, FRAME_WIDTH, FRAME_HEIGHT,
    ALIVE_CELL_COLOR, DEFECTIVE_CELL_COLOR, FALLBACK_COLORS, SAFE_VERIFICATION_VALUES,
    VERIFICATION_COLOR_SAFE, VERIFICATION_COLOR_DEFECT, NEON_PALETTE,
    UNIT_FACE_COLOR, UNIT_EDGE_COLOR, PANEL_BACKGROUND_COLOR, INTER_UNIT_GAP,
    PlotTheme, SAFE_VERIFICATION_VALUES_UPPER
)
from src.models import StressMapData
from src.documentation import VERIFICATION_DESCRIPTIONS
from src.enums import Quadrant

# ==============================================================================
# --- Private Helper Functions for Grid Creation ---
# ==============================================================================

def _get_rounded_rect_path(x0: float, y0: float, x1: float, y1: float, r: float) -> str:
    """Generates an SVG path string for a rounded rectangle."""
    width = x1 - x0
    height = y1 - y0
    r = min(r, width / 2, height / 2)

    return (
        f"M {x0+r} {y0} "
        f"L {x1-r} {y0} "
        f"Q {x1} {y0} {x1} {y0+r} "
        f"L {x1} {y1-r} "
        f"Q {x1} {y1} {x1-r} {y1} "
        f"L {x0+r} {y1} "
        f"Q {x0} {y1} {x0} {y1-r} "
        f"L {x0} {y0+r} "
        f"Q {x0} {y0} {x0+r} {y0} "
        "Z"
    )

def _draw_quadrant_grids(origins_to_draw: Dict, panel_rows: int, panel_cols: int, fill: bool = True, panel_width: float = PANEL_WIDTH, panel_height: float = PANEL_HEIGHT, theme_config: Optional[PlotTheme] = None) -> List[Dict[str, Any]]:
    """Creates the shapes for the quadrant outlines and individual unit rectangles."""
    shapes = []
    quad_width = panel_width / 2
    quad_height = panel_height / 2

    # Determine colors
    if theme_config:
        bg_color = theme_config.panel_background_color
        edge_color = theme_config.unit_edge_color
        face_color = theme_config.unit_face_color
        border_color = theme_config.axis_color
    else:
        bg_color = PANEL_BACKGROUND_COLOR
        edge_color = UNIT_EDGE_COLOR
        face_color = UNIT_FACE_COLOR
        border_color = GRID_COLOR

    unit_width = (quad_width - (panel_cols + 1) * INTER_UNIT_GAP) / panel_cols
    unit_height = (quad_height - (panel_rows + 1) * INTER_UNIT_GAP) / panel_rows

    for x_start, y_start in origins_to_draw.values():
        if fill:
            path = _get_rounded_rect_path(x_start, y_start, x_start + quad_width, y_start + quad_height, 20.0)
            shapes.append(dict(
                type="path",
                path=path,
                fillcolor=bg_color,
                line=dict(color=border_color, width=3),
                layer='below'
            ))

            for r in range(panel_rows):
                for c in range(panel_cols):
                    ux = x_start + INTER_UNIT_GAP + c * (unit_width + INTER_UNIT_GAP)
                    uy = y_start + INTER_UNIT_GAP + r * (unit_height + INTER_UNIT_GAP)

                    shapes.append(dict(
                        type="rect",
                        x0=ux, y0=uy,
                        x1=ux + unit_width, y1=uy + unit_height,
                        line=dict(color=edge_color, width=1),
                        fillcolor=face_color,
                        layer='below'
                    ))
        else:
             for r in range(panel_rows):
                for c in range(panel_cols):
                    ux = x_start + INTER_UNIT_GAP + c * (unit_width + INTER_UNIT_GAP)
                    uy = y_start + INTER_UNIT_GAP + r * (unit_height + INTER_UNIT_GAP)
                    shapes.append(dict(
                        type="rect",
                        x0=ux, y0=uy,
                        x1=ux + unit_width, y1=uy + unit_height,
                        line=dict(color=edge_color, width=1),
                        fillcolor="rgba(0,0,0,0)",
                        layer='below'
                    ))
            
    return shapes

# ==============================================================================
# --- Public API Functions ---
# ==============================================================================

def apply_panel_theme(fig: go.Figure, title: str = "", height: int = 800, theme_config: Optional[PlotTheme] = None) -> go.Figure:
    """Applies the standard engineering styling to any figure."""
    if theme_config:
        bg_color = theme_config.background_color
        plot_color = theme_config.plot_area_color
        text_color = theme_config.text_color
        axis_color = theme_config.axis_color
    else:
        bg_color = BACKGROUND_COLOR
        plot_color = PLOT_AREA_COLOR
        text_color = TEXT_COLOR
        axis_color = GRID_COLOR

    fig.update_layout(
        title=dict(text=title, font=dict(color=text_color, size=18), x=0.5, xanchor='center'),
        plot_bgcolor=plot_color,
        paper_bgcolor=bg_color,
        height=height,
        font=dict(color=text_color),
        xaxis=dict(
            showgrid=False, zeroline=False, showline=True,
            linewidth=2, linecolor=axis_color, mirror=True,
            title_font=dict(color=text_color), tickfont=dict(color=text_color)
        ),
        yaxis=dict(
            showgrid=False, zeroline=False, showline=True,
            linewidth=2, linecolor=axis_color, mirror=True,
            title_font=dict(color=text_color), tickfont=dict(color=text_color),
            scaleanchor="x", scaleratio=1
        ),
        legend=dict(
            title_font=dict(color=text_color), font=dict(color=text_color),
            bgcolor=bg_color, bordercolor=axis_color, borderwidth=1,
            x=1.02, y=1, xanchor='left', yanchor='top'
        ),
        hoverlabel=dict(bgcolor="#4A4A4A", font_size=14, font_family="sans-serif")
    )
    return fig

@st.cache_data
def create_grid_shapes(
    panel_rows: int,
    panel_cols: int,
    quadrant: str = 'All',
    fill: bool = True,
    offset_x: float = 0.0,
    offset_y: float = 0.0,
    gap_x: float = GAP_SIZE,
    gap_y: float = GAP_SIZE,
    panel_width: float = PANEL_WIDTH,
    panel_height: float = PANEL_HEIGHT,
    theme_config: Optional[PlotTheme] = None,
    visual_origin_x: float = 0.0,
    visual_origin_y: float = 0.0,
    fixed_offset_x: float = 0.0,
    fixed_offset_y: float = 0.0
) -> List[Dict[str, Any]]:
    """Creates visual shapes for the panel grid (Cached)."""
    quad_width = panel_width / 2
    quad_height = panel_height / 2

    gap_color = theme_config.panel_background_color if theme_config else PANEL_BACKGROUND_COLOR
    border_color = theme_config.axis_color if theme_config else GRID_COLOR

    shapes = []

    if quadrant == 'All':
        # Draw BIG Copper Frame using Constants
        path_frame = _get_rounded_rect_path(0, 0, FRAME_WIDTH, FRAME_HEIGHT, 20.0)
        shapes.append(dict(
            type="path",
            path=path_frame,
            fillcolor=gap_color,
            line=dict(color=border_color, width=3),
            layer='below'
        ))

        if fixed_offset_x > 0 and fixed_offset_y > 0:
            x0_inner = fixed_offset_x
            y0_inner = fixed_offset_y
            x1_inner = FRAME_WIDTH - fixed_offset_x
            y1_inner = FRAME_HEIGHT - fixed_offset_y

            fill_col = theme_config.inner_gap_color if theme_config and hasattr(theme_config, 'inner_gap_color') else "black"

            shapes.append(dict(
                type="rect",
                x0=x0_inner, y0=y0_inner,
                x1=x1_inner, y1=y1_inner,
                fillcolor=fill_col,
                line=dict(width=0),
                layer='below'
            ))

    all_origins = {
        'Q1': (0+offset_x , 0+offset_y),
        'Q2': (quad_width + gap_x + offset_x, 0+offset_y),
        'Q3': (0+offset_x, quad_height + gap_y + offset_y),
        'Q4': (quad_width + gap_x + offset_x, quad_height + gap_y + offset_y)
    }
    origins_to_draw = all_origins if quadrant == 'All' else {quadrant: all_origins[quadrant]}

    shapes.extend(_draw_quadrant_grids(origins_to_draw, panel_rows, panel_cols, fill=fill, panel_width=panel_width, panel_height=panel_height, theme_config=theme_config))
    return shapes

def create_defect_traces(
    df: pd.DataFrame,
    offset_x: float = 0.0,
    offset_y: float = 0.0,
    gap_x: float = GAP_SIZE,
    gap_y: float = GAP_SIZE,
    visual_origin_x: float = 0.0,
    visual_origin_y: float = 0.0
) -> List[go.Scatter]:
    """Generates scatter plot traces. Uses consolidated trace if too many groups."""
    traces = []
    if df.empty: return traces

    has_verification_data = df['HAS_VERIFICATION_DATA'].any() if 'HAS_VERIFICATION_DATA' in df.columns else False
    group_col = 'Verification' if has_verification_data else 'DEFECT_TYPE'
    unique_groups = df[group_col].unique()

    # Optimization: If > 20 groups, combine into single trace to save DOM nodes
    use_single_trace = len(unique_groups) > 20

    if 'Verification' in df.columns:
        df = df.copy() # Safe copy for display logic
        df['Description'] = df['Verification'].map(VERIFICATION_DESCRIPTIONS).fillna("Unknown Code")
    else:
        df = df.copy()
        df['Description'] = "N/A"

    # Pre-calculate Coordinates
    if 'X_COORDINATES' in df.columns:
        # Absolute
        x_vals = df['plot_x'] + visual_origin_x
        y_vals = df['plot_y'] + visual_origin_y
        df['RAW_COORD_STR'] = df.apply(lambda row: f"({row['X_COORDINATES']/1000:.2f}, {row['Y_COORDINATES']/1000:.2f}) mm", axis=1)
        coord_str = "<br>Raw Coords: %{customdata[6]}"
        custom_data_cols = ['UNIT_INDEX_X', 'UNIT_INDEX_Y', 'DEFECT_TYPE', 'DEFECT_ID', 'Verification', 'Description', 'RAW_COORD_STR']
    else:
        # Relative
        x_vals = (df['plot_x'] + offset_x) + visual_origin_x
        y_vals = (df['plot_y'] + offset_y) + visual_origin_y
        coord_str = ""
        custom_data_cols = ['UNIT_INDEX_X', 'UNIT_INDEX_Y', 'DEFECT_TYPE', 'DEFECT_ID', 'Verification', 'Description']

    if use_single_trace:
        # Single Trace Logic using marker colors
        # Map groups to colors
        color_map = {}
        for i, grp in enumerate(unique_groups):
            color_map[grp] = FALLBACK_COLORS[i % len(FALLBACK_COLORS)]

        colors = df[group_col].map(color_map)

        hovertemplate = ("<b>Status: %{customdata[4]}</b><br>"
                            "Description : %{customdata[5]}<br>"
                            "Type: %{customdata[2]}<br>"
                            "Unit Index: (%{customdata[0]}, %{customdata[1]})<br>"
                            "Defect ID: %{customdata[3]}"
                            + coord_str +
                            "<extra></extra>")

        traces.append(go.Scattergl(
            x=x_vals, y=y_vals, mode='markers',
            marker=dict(color=colors, size=8, line=dict(width=1, color='black')),
            name="All Defects",
            customdata=df[custom_data_cols],
            hovertemplate=hovertemplate
        ))

    else:
        # Standard Multi-Trace Logic
        local_style_map = {}
        idx = 0
        for grp in unique_groups:
            local_style_map[grp] = FALLBACK_COLORS[idx % len(FALLBACK_COLORS)]
            idx += 1

        grouped = df.groupby(group_col, observed=True)
        for group_val, dff in grouped:
            color = local_style_map.get(group_val, '#333333')

            hovertemplate = ("<b>Status: %{customdata[4]}</b><br>"
                                "Description : %{customdata[5]}<br>"
                                "Type: %{customdata[2]}<br>"
                                "Unit Index: (%{customdata[0]}, %{customdata[1]})<br>"
                                "Defect ID: %{customdata[3]}"
                                + coord_str +
                                "<extra></extra>")

            # Filter coords for this group
            # We must use the index or mask
            mask = df[group_col] == group_val

            traces.append(go.Scattergl(
                x=x_vals[mask], y=y_vals[mask], mode='markers',
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
    panel_height: float = PANEL_HEIGHT,
    theme_config: Optional[PlotTheme] = None,
    visual_origin_x: float = 0.0,
    visual_origin_y: float = 0.0,
    fixed_offset_x: float = 0.0,
    fixed_offset_y: float = 0.0
) -> go.Figure:
    fig = go.Figure()

    if not df.empty:
        if 'LAYER_NUM' not in df.columns: df['LAYER_NUM'] = 0
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
                trace_name = f"Layer {layer_num} ({side_name})"

                if 'Verification' in dff.columns:
                     dff = dff.copy()
                     dff['Description'] = dff['Verification'].map(VERIFICATION_DESCRIPTIONS).fillna("Unknown Code")
                else:
                     dff['Description'] = "N/A"

                coord_str = ""
                if 'X_COORDINATES' in dff.columns and 'Y_COORDINATES' in dff.columns:
                    dff['RAW_COORD_STR'] = dff.apply(lambda row: f"({row['X_COORDINATES']/1000:.2f}, {row['Y_COORDINATES']/1000:.2f}) mm", axis=1)
                    custom_data_cols = ['UNIT_INDEX_X', 'UNIT_INDEX_Y', 'DEFECT_TYPE', 'DEFECT_ID', 'Verification', 'Description', 'SOURCE_FILE', 'RAW_COORD_STR']
                    coord_str = "<br>Raw Coords: %{customdata[7]}"
                else:
                    custom_data_cols = ['UNIT_INDEX_X', 'UNIT_INDEX_Y', 'DEFECT_TYPE', 'DEFECT_ID', 'Verification', 'Description', 'SOURCE_FILE']

                hovertemplate = (f"<b>Layer: {layer_num}</b><br>"
                                 "Side: " + side_name + "<br>"
                                 "Status: %{customdata[4]}<br>"
                                 "Type: %{customdata[2]}<br>"
                                 "Unit Index: (%{customdata[0]}, %{customdata[1]})<br>"
                                 "File: %{customdata[6]}"
                                 + coord_str +
                                 "<extra></extra>")

                if flip_back:
                    x_col_name = 'physical_plot_x_flipped'
                else:
                    x_col_name = 'physical_plot_x_raw'
                x_coords = dff[x_col_name]

                if 'X_COORDINATES' in dff.columns:
                     final_x = x_coords + visual_origin_x
                     final_y = dff['plot_y'] + visual_origin_y
                else:
                     final_x = (x_coords + offset_x) + visual_origin_x
                     final_y = (dff['plot_y'] + offset_y) + visual_origin_y

                fig.add_trace(go.Scattergl(
                    x=final_x, y=final_y, mode='markers',
                    marker=dict(color=layer_color, symbol=symbol, size=9, line=dict(width=1, color='black')),
                    name=trace_name, customdata=dff[custom_data_cols], hovertemplate=hovertemplate
                ))

    fig.update_layout(shapes=create_grid_shapes(panel_rows, panel_cols, quadrant='All', offset_x=offset_x, offset_y=offset_y, gap_x=gap_x, gap_y=gap_y, panel_width=panel_width, panel_height=panel_height, theme_config=theme_config, visual_origin_x=visual_origin_x, visual_origin_y=visual_origin_y, fixed_offset_x=fixed_offset_x, fixed_offset_y=fixed_offset_y))

    quad_width = panel_width / 2
    quad_height = panel_height / 2
    cell_width, cell_height = quad_width / panel_cols, quad_height / panel_rows

    x_tick_vals_q1 = [(i * cell_width) + (cell_width / 2) + offset_x for i in range(panel_cols)]
    x_tick_vals_q2 = [(quad_width + gap_x) + (i * cell_width) + (cell_width / 2) + offset_x for i in range(panel_cols)]
    y_tick_vals_q1 = [(i * cell_height) + (cell_height / 2) + offset_y for i in range(panel_rows)]
    y_tick_vals_q3 = [(quad_height + gap_y) + (i * cell_height) + (cell_height / 2) + offset_y for i in range(panel_rows)]
    x_tick_text = list(range(panel_cols * 2))
    y_tick_text = list(range(panel_rows * 2))

    apply_panel_theme(fig, "Multi-Layer Combined Defect Map (True Defects Only)", theme_config=theme_config)

    x_range = [0, FRAME_WIDTH]
    y_range = [0, FRAME_HEIGHT]

    fig.update_layout(
        xaxis=dict(title="Unit Column Index", tickvals=x_tick_vals_q1 + x_tick_vals_q2, ticktext=x_tick_text, range=x_range, constrain='domain'),
        yaxis=dict(title="Unit Row Index", tickvals=y_tick_vals_q1 + y_tick_vals_q3, ticktext=y_tick_text, range=y_range),
        legend=dict(title=dict(text="Build-Up Layer"))
    )

    return fig
    
def create_defect_map_figure(
    df: pd.DataFrame,
    panel_rows: int,
    panel_cols: int,
    quadrant_selection: str = Quadrant.ALL.value,
    lot_number: Optional[str] = None,
    title: Optional[str] = None,
    offset_x: float = 0.0,
    offset_y: float = 0.0,
    gap_x: float = GAP_SIZE,
    gap_y: float = GAP_SIZE,
    panel_width: float = PANEL_WIDTH,
    panel_height: float = PANEL_HEIGHT,
    theme_config: Optional[PlotTheme] = None,
    visual_origin_x: float = 0.0,
    visual_origin_y: float = 0.0,
    fixed_offset_x: float = 0.0,
    fixed_offset_y: float = 0.0
) -> go.Figure:
    quad_width = panel_width / 2
    quad_height = panel_height / 2

    fig = go.Figure(data=create_defect_traces(df, offset_x=offset_x, offset_y=offset_y, gap_x=gap_x, gap_y=gap_y, visual_origin_x=visual_origin_x, visual_origin_y=visual_origin_y))
    fig.update_layout(shapes=create_grid_shapes(panel_rows, panel_cols, quadrant_selection, offset_x=offset_x, offset_y=offset_y, gap_x=gap_x, gap_y=gap_y, panel_width=panel_width, panel_height=panel_height, theme_config=theme_config, visual_origin_x=0, visual_origin_y=0, fixed_offset_x=fixed_offset_x, fixed_offset_y=fixed_offset_y))

    cell_width, cell_height = quad_width / panel_cols, quad_height / panel_rows
    x_tick_vals_q1 = [(i * cell_width) + (cell_width / 2) + offset_x for i in range(panel_cols)]
    x_tick_vals_q2 = [(quad_width + gap_x) + (i * cell_width) + (cell_width / 2) + offset_x for i in range(panel_cols)]
    y_tick_vals_q1 = [(i * cell_height) + (cell_height / 2) + offset_y for i in range(panel_rows)]
    y_tick_vals_q3 = [(quad_height + gap_y) + (i * cell_height) + (cell_height / 2) + offset_y for i in range(panel_rows)]
    x_tick_text, y_tick_text = list(range(panel_cols * 2)), list(range(panel_rows * 2))

    x_axis_range = [0, FRAME_WIDTH]
    y_axis_range = [0, FRAME_HEIGHT]
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

    apply_panel_theme(fig, final_title, theme_config=theme_config)

    fig.update_layout(
        xaxis=dict(title="Unit Column Index", tickvals=x_tick_vals_q1 + x_tick_vals_q2 if show_ticks else [], ticktext=x_tick_text if show_ticks else [], range=x_axis_range, constrain='domain'),
        yaxis=dict(title="Unit Row Index", tickvals=y_tick_vals_q1 + y_tick_vals_q3 if show_ticks else [], ticktext=y_tick_text if show_ticks else [], range=y_axis_range)
    )

    if lot_number and quadrant_selection == Quadrant.ALL.value:
        t_col = theme_config.text_color if theme_config else TEXT_COLOR
        fig.add_annotation(x=(panel_width + gap_x + offset_x), y=(panel_height + gap_y + offset_y), text=f"<b>Lot #: {lot_number}</b>", showarrow=False, font=dict(size=14, color=t_col), align="right", xanchor="right", yanchor="bottom")

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

def create_pareto_figure(df: pd.DataFrame, quadrant_selection: str = Quadrant.ALL.value, theme_config: Optional[PlotTheme] = None) -> go.Figure:
    fig = go.Figure()
    if quadrant_selection == Quadrant.ALL.value:
        for trace in create_grouped_pareto_trace(df): fig.add_trace(trace)
        fig.update_layout(barmode='stack')
    else:
        fig.add_trace(create_pareto_trace(df))

    apply_panel_theme(fig, f"Defect Pareto - Quadrant: {quadrant_selection}", height=600, theme_config=theme_config)

    fig.update_layout(
        xaxis=dict(title="Defect Type", categoryorder='total descending'),
        yaxis=dict(showgrid=True)
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
    panel_height: float = PANEL_HEIGHT,
    theme_config: Optional[PlotTheme] = None,
    visual_origin_x: float = 0.0,
    visual_origin_y: float = 0.0,
    fixed_offset_x: float = 0.0,
    fixed_offset_y: float = 0.0
) -> Tuple[List[Dict[str, Any]], List[go.Scatter]]:
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

    unit_width = (quad_width - (panel_cols + 1) * INTER_UNIT_GAP) / panel_cols
    unit_height = (quad_height - (panel_rows + 1) * INTER_UNIT_GAP) / panel_rows

    hover_x = []
    hover_y = []
    hover_text = []
    hover_colors = []

    border_color = theme_config.axis_color if theme_config else GRID_COLOR
    bg_color = theme_config.panel_background_color if theme_config else PANEL_BACKGROUND_COLOR
    path_frame = _get_rounded_rect_path(0, 0, FRAME_WIDTH, FRAME_HEIGHT, 20.0)
    shapes.append(dict(
        type="path",
        path=path_frame,
        fillcolor=bg_color,
        line=dict(color=border_color, width=3),
        layer='below'
    ))

    if fixed_offset_x > 0 and fixed_offset_y > 0:
        x0_inner = fixed_offset_x
        y0_inner = fixed_offset_y
        x1_inner = FRAME_WIDTH - fixed_offset_x
        y1_inner = FRAME_HEIGHT - fixed_offset_y

        fill_col = theme_config.inner_gap_color if theme_config and hasattr(theme_config, 'inner_gap_color') else "black"

        shapes.append(dict(
            type="rect",
            x0=x0_inner, y0=y0_inner,
            x1=x1_inner, y1=y1_inner,
            fillcolor=fill_col,
            line=dict(width=0),
            layer='below'
        ))

    edge_color = theme_config.unit_edge_color if theme_config else UNIT_EDGE_COLOR

    for q_key, (qx, qy) in all_origins.items():
         shapes.append(dict(
            type="rect", x0=qx, y0=qy, x1=qx + quad_width, y1=qy + quad_height,
            line=dict(width=0), fillcolor=bg_color, layer='below'
        ))

    for row in range(total_rows):
        for col in range(total_cols):
            quadrant_col, local_col = divmod(col, panel_cols)
            quadrant_row, local_row = divmod(row, panel_rows)
            quad_key = f"Q{quadrant_row * 2 + quadrant_col + 1}"
            x_origin, y_origin = all_origins[quad_key]

            x0 = x_origin + INTER_UNIT_GAP + local_col * (unit_width + INTER_UNIT_GAP)
            y0 = y_origin + INTER_UNIT_GAP + local_row * (unit_height + INTER_UNIT_GAP)

            is_dead = (col, row) in true_defect_data

            if is_dead:
                metadata = true_defect_data[(col, row)]
                first_killer = metadata['first_killer_layer']
                fill_color = DEFECTIVE_CELL_COLOR
                center_x = x0 + unit_width/2
                center_y = y0 + unit_height/2
                hover_x.append(center_x)
                hover_y.append(center_y)

                tooltip = (
                    f"<b>Unit: ({col}, {row})</b><br>"
                    f"First Killer: Layer {first_killer}<br>"
                    f"Details: {metadata['defect_summary']}"
                )
                hover_text.append(tooltip)
                hover_colors.append(fill_color)

            else:
                fill_color = ALIVE_CELL_COLOR

            shapes.append({'type': 'rect', 'x0': x0, 'y0': y0, 'x1': x0 + unit_width, 'y1': y0 + unit_height, 'fillcolor': fill_color, 'line': {'width': 1, 'color': edge_color}, 'layer': 'below'})

    if hover_x:
        traces.append(go.Scatter(
            x=hover_x,
            y=hover_y,
            mode='markers',
            marker=dict(size=0, color=hover_colors, opacity=0),
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
    panel_height: float = PANEL_HEIGHT,
    theme_config: Optional[PlotTheme] = None,
    visual_origin_x: float = 0.0,
    visual_origin_y: float = 0.0,
    fixed_offset_x: float = 0.0,
    fixed_offset_y: float = 0.0
) -> go.Figure:
    map_shapes, hover_traces = create_still_alive_map(panel_rows, panel_cols, true_defect_data, offset_x=offset_x, offset_y=offset_y, gap_x=gap_x, gap_y=gap_y, panel_width=panel_width, panel_height=panel_height, theme_config=theme_config, visual_origin_x=0, visual_origin_y=0, fixed_offset_x=fixed_offset_x, fixed_offset_y=fixed_offset_y)

    fig = go.Figure(data=hover_traces)

    quad_width = panel_width / 2
    quad_height = panel_height / 2

    cell_width, cell_height = quad_width / panel_cols, quad_height / panel_rows
    x_tick_vals_q1 = [(i * cell_width) + (cell_width / 2) + offset_x for i in range(panel_cols)]
    x_tick_vals_q2 = [(quad_width + gap_x) + (i * cell_width) + (cell_width / 2) + offset_x for i in range(panel_cols)]
    y_tick_vals_q1 = [(i * cell_height) + (cell_height / 2) + offset_y for i in range(panel_rows)]
    y_tick_vals_q3 = [(quad_height + gap_y) + (i * cell_height) + (cell_height / 2) + offset_y for i in range(panel_rows)]
    x_tick_text = list(range(panel_cols * 2))
    y_tick_text = list(range(panel_rows * 2))

    apply_panel_theme(fig, f"Still Alive Map ({len(true_defect_data)} Defective Cells)", theme_config=theme_config)

    x_range = [0, FRAME_WIDTH]
    y_range = [0, FRAME_HEIGHT]

    fig.update_layout(
        xaxis=dict(
            title="Unit Column Index", range=x_range, constrain='domain',
            tickvals=x_tick_vals_q1 + x_tick_vals_q2, ticktext=x_tick_text
        ),
        yaxis=dict(
            title="Unit Row Index", range=y_range,
            tickvals=y_tick_vals_q1 + y_tick_vals_q3, ticktext=y_tick_text
        ),
        shapes=map_shapes, margin=dict(l=20, r=20, t=80, b=20),
        showlegend=False
    )
    return fig

def hex_to_rgba(hex_color: str, opacity: float = 0.5) -> str:
    try:
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 6:
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            return f'rgba({r}, {g}, {b}, {opacity})'
        return f'rgba(128, 128, 128, {opacity})'
    except ValueError:
        return f'rgba(128, 128, 128, {opacity})'

def create_defect_sankey(df: pd.DataFrame, theme_config: Optional[PlotTheme] = None) -> go.Sankey:
    if df.empty: return None
    has_verification = df['HAS_VERIFICATION_DATA'].iloc[0] if 'HAS_VERIFICATION_DATA' in df.columns else False
    if not has_verification: return None

    sankey_df = df.groupby(['DEFECT_TYPE', 'Verification'], observed=True).size().reset_index(name='Count')
    total_defects = sankey_df['Count'].sum()
    defect_counts = sankey_df.groupby('DEFECT_TYPE', observed=True)['Count'].sum().sort_values(ascending=False)
    verification_counts = sankey_df.groupby('Verification', observed=True)['Count'].sum().sort_values(ascending=False)

    defect_types = defect_counts.index.tolist()
    verification_statuses = verification_counts.index.tolist()

    smart_labels = []
    for dtype in defect_types:
        count = defect_counts[dtype]
        pct = (count / total_defects) * 100
        smart_labels.append(f"{dtype} ({count} - {pct:.1f}%)")

    for ver in verification_statuses:
        count = verification_counts[ver]
        pct = (count / total_defects) * 100
        smart_labels.append(f"{ver} ({count} - {pct:.1f}%)")

    source_map = {label: i for i, label in enumerate(defect_types)}
    offset = len(defect_types)
    target_map = {label: i + offset for i, label in enumerate(verification_statuses)}

    sources, targets, values, link_colors, custom_hovers = [], [], [], [], []
    source_colors_hex = [NEON_PALETTE[i % len(NEON_PALETTE)] for i, dtype in enumerate(defect_types)]
    target_colors_hex = []
    for status in verification_statuses:
        if status.upper() in SAFE_VERIFICATION_VALUES_UPPER:
            target_colors_hex.append(VERIFICATION_COLOR_SAFE)
        else:
            target_colors_hex.append(VERIFICATION_COLOR_DEFECT)
    node_colors = source_colors_hex + target_colors_hex

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
            source_hex = source_colors_hex[s_idx]
            link_colors.append(hex_to_rgba(source_hex, opacity=0.8))
            pct_flow = (count / total_defects) * 100
            custom_hovers.append(f"<b>{count} {dtype}s</b> accounted for <b>{pct_flow:.1f}%</b> of total flow<br>Resulting in <b>{ver}</b> status.")

    fig = go.Figure(data=[go.Sankey(
        node=dict(pad=25, thickness=30, line=dict(color="black", width=1), label=smart_labels, color=node_colors, hovertemplate='%{label}<extra></extra>'),
        link=dict(source=sources, target=targets, value=values, color=link_colors, customdata=custom_hovers, hovertemplate='%{customdata}<extra></extra>'),
        textfont=dict(size=14, color=TEXT_COLOR, family="Roboto")
    )])

    apply_panel_theme(fig, "Defect Type → Verification Flow Analysis", height=700, theme_config=theme_config)
    fig.update_layout(font=dict(size=12, color=TEXT_COLOR), margin=dict(l=20, r=20, t=60, b=20), xaxis=dict(showgrid=False, showline=False), yaxis=dict(showgrid=False, showline=False))
    return fig

def create_defect_sunburst(df: pd.DataFrame, theme_config: Optional[PlotTheme] = None) -> go.Figure:
    if df.empty: return go.Figure()
    has_verification = df['HAS_VERIFICATION_DATA'].iloc[0] if 'HAS_VERIFICATION_DATA' in df.columns else False

    if has_verification:
        grouped = df.groupby(['DEFECT_TYPE', 'Verification'], observed=True).size().reset_index(name='Count')
    else:
        grouped = df.groupby(['DEFECT_TYPE'], observed=True).size().reset_index(name='Count')

    ids, labels, parents, values, custom_data = [], [], [], [], []
    total_count = grouped['Count'].sum()
    ids.append("Total")
    labels.append(f"Total<br>{total_count}")
    parents.append("")
    values.append(total_count)
    custom_data.append(["Total", total_count, "100%", "100%"])

    for dtype in grouped['DEFECT_TYPE'].unique():
        dtype_count = grouped[grouped['DEFECT_TYPE'] == dtype]['Count'].sum()
        ids.append(f"{dtype}")
        labels.append(dtype)
        parents.append("Total")
        values.append(dtype_count)
        pct_total = (dtype_count / total_count) * 100
        custom_data.append([dtype, dtype_count, f"{pct_total:.1f}%", f"{pct_total:.1f}%"])

        if has_verification:
            dtype_df = grouped[grouped['DEFECT_TYPE'] == dtype]
            for ver in dtype_df['Verification'].unique():
                ver_count = dtype_df[dtype_df['Verification'] == ver]['Count'].sum()
                ids.append(f"{dtype}-{ver}")
                labels.append(ver)
                parents.append(f"{dtype}")
                values.append(ver_count)
                pct_parent = (ver_count / dtype_count) * 100
                pct_total_ver = (ver_count / total_count) * 100
                custom_data.append([ver, ver_count, f"{pct_parent:.1f}%", f"{pct_total_ver:.1f}%"])

    fig = go.Figure(go.Sunburst(
        ids=ids, labels=labels, parents=parents, values=values, branchvalues="total", customdata=custom_data,
        hovertemplate="<b>%{customdata[0]}</b><br>Count: %{customdata[1]}<br>% of Layer: %{customdata[2]}<br>% of Total: %{customdata[3]}<extra></extra>"
    ))
    apply_panel_theme(fig, "Defect Distribution", height=700, theme_config=theme_config)
    fig.update_layout(margin=dict(t=40, l=10, r=10, b=10), xaxis=dict(visible=False), yaxis=dict(visible=False), showlegend=False)
    return fig

def create_stress_heatmap(
    data: StressMapData,
    panel_rows: int,
    panel_cols: int,
    view_mode: str = "Continuous",
    offset_x: float = 0.0,
    offset_y: float = 0.0,
    gap_size: float = GAP_SIZE,
    panel_width: float = PANEL_WIDTH,
    panel_height: float = PANEL_HEIGHT,
    gap_x: float = GAP_SIZE,
    gap_y: float = GAP_SIZE,
    theme_config: Optional[PlotTheme] = None,
    visual_origin_x: float = 0.0,
    visual_origin_y: float = 0.0,
    fixed_offset_x: float = 0.0,
    fixed_offset_y: float = 0.0
) -> go.Figure:
    quad_width = panel_width / 2
    quad_height = panel_height / 2

    text_color = theme_config.text_color if theme_config else TEXT_COLOR
    bg_color = theme_config.background_color if theme_config else BACKGROUND_COLOR
    plot_color = theme_config.plot_area_color if theme_config else PLOT_AREA_COLOR

    if data.total_defects == 0:
        return go.Figure(layout=dict(title=dict(text="No True Defects Found in Selection", font=dict(color=text_color)), paper_bgcolor=bg_color, plot_bgcolor=plot_color))

    z_data = data.grid_counts.astype(float)
    text_data = data.grid_counts.astype(str)
    z_data[z_data == 0] = np.nan
    text_data[data.grid_counts == 0] = ""

    if view_mode == "Quarterly":
        rows, cols = z_data.shape
        cell_width = quad_width / panel_cols
        cell_height = quad_height / panel_rows
        col_indices = np.arange(cols)
        row_indices = np.arange(rows)
        u_w = (quad_width - (panel_cols + 1) * INTER_UNIT_GAP) / panel_cols
        u_h = (quad_height - (panel_rows + 1) * INTER_UNIT_GAP) / panel_rows
        stride_x = u_w + INTER_UNIT_GAP
        stride_y = u_h + INTER_UNIT_GAP
        l_cols = col_indices % panel_cols
        l_rows = row_indices % panel_rows
        x_base = INTER_UNIT_GAP + l_cols * stride_x + (u_w / 2)
        y_base = INTER_UNIT_GAP + l_rows * stride_y + (u_h / 2)
        quad_offset_x = np.where(col_indices >= panel_cols, quad_width + gap_x, 0)
        quad_offset_y = np.where(row_indices >= panel_rows, quad_height + gap_y, 0)
        x_vals = offset_x + quad_offset_x + x_base
        y_vals = offset_y + quad_offset_y + y_base
        x_coords, y_coords = np.meshgrid(x_vals, y_vals)

        fig = go.Figure(data=go.Heatmap(
            x=x_coords[0, :], y=y_coords[:, 0], z=z_data, text=text_data, texttemplate="%{text}", textfont={"color": "white"}, colorscale='Magma', xgap=2, ygap=2, hovertext=data.hover_text, hoverinfo="text", colorbar=dict(title='Defects', title_font=dict(color=text_color), tickfont=dict(color=text_color))
        ))
        fig.update_layout(shapes=create_grid_shapes(panel_rows, panel_cols, quadrant='All', fill=False, offset_x=offset_x, offset_y=offset_y, gap_x=gap_x, gap_y=gap_y, panel_width=panel_width, panel_height=panel_height, theme_config=theme_config, visual_origin_x=0, visual_origin_y=0, fixed_offset_x=fixed_offset_x, fixed_offset_y=fixed_offset_y))
        fig.update_layout(xaxis=dict(title="Physical X", range=[0, FRAME_WIDTH], constrain='domain', showticklabels=False), yaxis=dict(title="Physical Y", range=[0, FRAME_HEIGHT], showticklabels=False))
    else:
        fig = go.Figure(data=go.Heatmap(z=z_data, text=text_data, texttemplate="%{text}", textfont={"color": "white"}, colorscale='Magma', xgap=2, ygap=2, hovertext=data.hover_text, hoverinfo="text", colorbar=dict(title='Defects', title_font=dict(color=text_color), tickfont=dict(color=text_color))))
        total_cols, total_rows = panel_cols * 2, panel_rows * 2
        fig.update_layout(xaxis=dict(title="Unit Index X", tickmode='linear', dtick=1, range=[-0.5, total_cols - 0.5], constrain='domain'), yaxis=dict(title="Unit Index Y", tickmode='linear', dtick=1, range=[-0.5, total_rows - 0.5]))

    apply_panel_theme(fig, "Cumulative Stress Map (Total Defects per Unit)", height=700, theme_config=theme_config)
    return fig

def create_delta_heatmap(
    data_a: StressMapData,
    data_b: StressMapData,
    panel_rows: int,
    panel_cols: int,
    view_mode: str = "Continuous",
    offset_x: float = 0.0,
    offset_y: float = 0.0,
    gap_size: float = GAP_SIZE,
    panel_width: float = PANEL_WIDTH,
    panel_height: float = PANEL_HEIGHT,
    gap_x: float = GAP_SIZE,
    gap_y: float = GAP_SIZE,
    theme_config: Optional[PlotTheme] = None,
    visual_origin_x: float = 0.0,
    visual_origin_y: float = 0.0,
    fixed_offset_x: float = 0.0,
    fixed_offset_y: float = 0.0
) -> go.Figure:
    quad_width = panel_width / 2
    quad_height = panel_height / 2
    text_color = theme_config.text_color if theme_config else TEXT_COLOR

    diff_grid = data_a.grid_counts.astype(float) - data_b.grid_counts.astype(float)
    text_data = np.array([f"{int(x):+d}" if x != 0 else "" for x in diff_grid.flatten()]).reshape(diff_grid.shape)
    diff_grid[diff_grid == 0] = np.nan

    if view_mode == "Quarterly":
        rows, cols = diff_grid.shape
        col_indices = np.arange(cols)
        row_indices = np.arange(rows)
        u_w = (quad_width - (panel_cols + 1) * INTER_UNIT_GAP) / panel_cols
        u_h = (quad_height - (panel_rows + 1) * INTER_UNIT_GAP) / panel_rows
        stride_x = u_w + INTER_UNIT_GAP
        stride_y = u_h + INTER_UNIT_GAP
        l_cols = col_indices % panel_cols
        l_rows = row_indices % panel_rows
        x_base = INTER_UNIT_GAP + l_cols * stride_x + (u_w / 2)
        y_base = INTER_UNIT_GAP + l_rows * stride_y + (u_h / 2)
        quad_offset_x = np.where(col_indices >= panel_cols, quad_width + gap_x, 0)
        quad_offset_y = np.where(row_indices >= panel_rows, quad_height + gap_y, 0)
        x_vals = offset_x + quad_offset_x + x_base
        y_vals = offset_y + quad_offset_y + y_base

        fig = go.Figure(data=go.Heatmap(x=x_vals, y=y_vals, z=diff_grid, text=text_data, texttemplate="%{text}", colorscale='RdBu_r', zmid=0, xgap=2, ygap=2, colorbar=dict(title='Delta (A - B)', title_font=dict(color=text_color), tickfont=dict(color=text_color))))
        fig.update_layout(shapes=create_grid_shapes(panel_rows, panel_cols, quadrant='All', fill=False, offset_x=offset_x, offset_y=offset_y, gap_x=gap_x, gap_y=gap_y, panel_width=panel_width, panel_height=panel_height, theme_config=theme_config, visual_origin_x=0, visual_origin_y=0, fixed_offset_x=fixed_offset_x, fixed_offset_y=fixed_offset_y))
        fig.update_layout(xaxis=dict(title="Physical X", range=[0, FRAME_WIDTH], constrain='domain', showticklabels=False), yaxis=dict(title="Physical Y", range=[0, FRAME_HEIGHT], showticklabels=False))
    else:
        fig = go.Figure(data=go.Heatmap(z=diff_grid, text=text_data, texttemplate="%{text}", colorscale='RdBu_r', zmid=0, xgap=2, ygap=2, colorbar=dict(title='Delta (A - B)', title_font=dict(color=text_color), tickfont=dict(color=text_color))))
        total_cols, total_rows = panel_cols * 2, panel_rows * 2
        fig.update_layout(xaxis=dict(title="Unit Index X", tickmode='linear', dtick=1, range=[-0.5, total_cols - 0.5], constrain='domain'), yaxis=dict(title="Unit Index Y", tickmode='linear', dtick=1, range=[-0.5, total_rows - 0.5]))

    apply_panel_theme(fig, "Delta Stress Map (Group A - Group B)", height=700, theme_config=theme_config)
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
    panel_height: float = PANEL_HEIGHT,
    theme_config: Optional[PlotTheme] = None,
    visual_origin_x: float = 0.0,
    visual_origin_y: float = 0.0,
    fixed_offset_x: float = 0.0,
    fixed_offset_y: float = 0.0
) -> go.Figure:
    if df.empty: return go.Figure()
    if 'Verification' in df.columns:
        df_true = df[~df['Verification'].str.upper().isin(SAFE_VERIFICATION_VALUES_UPPER)].copy()
    else:
        df_true = df.copy()
    if df_true.empty: return go.Figure(layout=dict(title="No True Defects Found"))

    if 'physical_plot_x_flipped' in df_true.columns:
        x_col_name = 'physical_plot_x_flipped' if flip_back else 'physical_plot_x_raw'
    else:
        x_col_name = 'plot_x'

    df_true['plot_x_corrected'] = df_true[x_col_name]
    df_true['plot_y_corrected'] = df_true['plot_y']
    x_col = 'plot_x_corrected'

    fig = go.Figure()
    scale_factor = 10.0 / max(1, smoothing_factor)
    bins_x = max(10, int((panel_cols * 2) * 2 * scale_factor))
    bins_y = max(10, int((panel_rows * 2) * 2 * scale_factor))
    num_bins = [bins_y, bins_x]
    x_min, x_max = offset_x, panel_width + gap_x + offset_x
    y_min, y_max = offset_y, panel_height + gap_y + offset_y

    def aggregate_quadrant(q_df, x_range, y_range):
        if q_df.empty: return None, None, None, None
        if 'X_COORDINATES' in q_df.columns:
            x_c = q_df[x_col].values + visual_origin_x
            y_c = q_df['plot_y_corrected'].values + visual_origin_y
        else:
            x_c = (q_df[x_col].values + offset_x) + visual_origin_x
            y_c = (q_df['plot_y_corrected'].values + offset_y) + visual_origin_y

        H, x_edges, y_edges = np.histogram2d(x_c, y_c, bins=num_bins, range=[x_range, y_range])
        driver_text = None

        if 'DEFECT_TYPE' in q_df.columns:
            unique_types = q_df['DEFECT_TYPE'].unique()
            if len(unique_types) > 10:
                unique_types = q_df['DEFECT_TYPE'].value_counts().nlargest(10).index.tolist()
            type_grids = []
            type_labels = []
            for dtype in unique_types:
                sub_df = q_df[q_df['DEFECT_TYPE'] == dtype]
                if not sub_df.empty:
                    if 'X_COORDINATES' in sub_df.columns:
                        sub_x = sub_df[x_col] + visual_origin_x
                        sub_y = sub_df['plot_y_corrected'] + visual_origin_y
                    else:
                        sub_x = (sub_df[x_col] + offset_x) + visual_origin_x
                        sub_y = (sub_df['plot_y_corrected'] + offset_y) + visual_origin_y
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

        x_centers = (x_edges[:-1] + x_edges[1:]) / 2
        y_centers = (y_edges[:-1] + y_edges[1:]) / 2
        return H.T, x_centers, y_centers, driver_text

    H, x_centers, y_centers, driver_text_t = aggregate_quadrant(df_true, [x_min, x_max], [y_min, y_max])
    if H is None: return go.Figure(layout=dict(title="Error in Aggregation"))
    Z = H
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
        z=Z, x=x_centers, y=y_centers, text=text_arg, colorscale='Turbo',
        contours=dict(coloring='heatmap', showlabels=True, labelfont=dict(color='white')),
        zmin=0, zmax=saturation_cap if saturation_cap > 0 else None,
        hoverinfo='x+y+z+text' if text_arg is not None else 'x+y+z', hovertemplate=hovertemplate
    ))

    if show_points:
        if 'X_COORDINATES' in df_true.columns:
            px = df_true[x_col] + visual_origin_x
            py = df_true['plot_y_corrected'] + visual_origin_y
        else:
            px = (df_true[x_col] + offset_x) + visual_origin_x
            py = (df_true['plot_y_corrected'] + offset_y) + visual_origin_y
        fig.add_trace(go.Scattergl(x=px, y=py, mode='markers', marker=dict(color='white', size=3, opacity=0.5), hoverinfo='skip', name='Defects'))

    shapes = []
    if show_grid:
        shapes = create_grid_shapes(panel_rows, panel_cols, quadrant='All', fill=False, offset_x=offset_x, offset_y=offset_y, gap_x=gap_x, gap_y=gap_y, panel_width=panel_width, panel_height=panel_height, theme_config=theme_config, visual_origin_x=0, visual_origin_y=0, fixed_offset_x=fixed_offset_x, fixed_offset_y=fixed_offset_y)

    total_cols = panel_cols * 2
    total_rows = panel_rows * 2
    quad_width = panel_width / 2
    quad_height = panel_height / 2
    cell_width = quad_width / panel_cols
    cell_height = quad_height / panel_rows
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

    x_axis_range = [0, FRAME_WIDTH]
    y_axis_range = [0, FRAME_HEIGHT]

    if quadrant_selection != 'All':
        ranges = {
            'Q1': ([offset_x, offset_x + quad_width], [offset_y, offset_y + quad_height]),
            'Q2': ([offset_x + quad_width + gap_x, offset_x + panel_width + gap_x], [offset_y, offset_y + quad_height]),
            'Q3': ([offset_x, offset_x + quad_width], [offset_y + quad_height + gap_y, offset_y + panel_height + gap_y]),
            'Q4': ([offset_x + quad_width + gap_x, offset_x + panel_width + gap_x], [offset_y + quad_height + gap_y, offset_y + panel_height + gap_y])
        }
        x_axis_range, y_axis_range = ranges[quadrant_selection]

    apply_panel_theme(fig, "Smooth Density Hotspot (Server-Side Aggregated)", height=700, theme_config=theme_config)
    fig.update_layout(xaxis=dict(title="Unit Column Index (Approx)", tickvals=x_tick_vals, ticktext=x_tick_text, range=x_axis_range, constrain='domain'), yaxis=dict(title="Unit Row Index (Approx)", tickvals=y_tick_vals, ticktext=y_tick_text, range=y_axis_range), shapes=shapes)
    return fig

def create_cross_section_heatmap(
    matrix: np.ndarray,
    layer_labels: List[str],
    axis_labels: List[str],
    slice_desc: str,
    theme_config: Optional[PlotTheme] = None
) -> go.Figure:
    if theme_config:
        bg_color = theme_config.background_color
        plot_color = theme_config.plot_area_color
        text_color = theme_config.text_color
    else:
        bg_color = BACKGROUND_COLOR
        plot_color = PLOT_AREA_COLOR
        text_color = TEXT_COLOR

    if matrix.size == 0:
         return go.Figure(layout=dict(title=dict(text="No Data for Cross-Section", font=dict(color=text_color)), paper_bgcolor=bg_color, plot_bgcolor=plot_color))

    z_data = matrix.astype(float)
    z_data[z_data == 0] = np.nan
    text_data = matrix.astype(str)
    text_data[matrix == 0] = ""

    fig = go.Figure(data=go.Heatmap(z=z_data, x=axis_labels, y=layer_labels, text=text_data, texttemplate="%{text}", textfont={"color": "white"}, colorscale='Magma', xgap=2, ygap=2, colorbar=dict(title='Defects', title_font=dict(color=text_color), tickfont=dict(color=text_color))))
    apply_panel_theme(fig, f"Virtual Cross-Section: {slice_desc}", height=600, theme_config=theme_config)
    fig.update_layout(xaxis=dict(title="Unit Index (Slice Position)", dtick=1), yaxis=dict(title="Layer Stack", autorange="reversed"))
    return fig

def create_unit_grid_heatmap(df: pd.DataFrame, panel_rows: int, panel_cols: int, theme_config: Optional[PlotTheme] = None) -> go.Figure:
    if df.empty: return go.Figure()
    if 'Verification' in df.columns:
        df_true = df[~df['Verification'].str.upper().isin(SAFE_VERIFICATION_VALUES_UPPER)].copy()
    else:
        df_true = df.copy()

    if theme_config:
        bg_color = theme_config.background_color
        plot_color = theme_config.plot_area_color
        text_color = theme_config.text_color
    else:
        bg_color = BACKGROUND_COLOR
        plot_color = PLOT_AREA_COLOR
        text_color = TEXT_COLOR

    if df_true.empty:
        return go.Figure(layout=dict(title=dict(text="No True Defects Found for Heatmap", font=dict(color=text_color)), paper_bgcolor=bg_color, plot_bgcolor=plot_color))

    global_indices = []
    for _, row in df_true.iterrows():
        u_x = int(row['UNIT_INDEX_X'])
        q = row['QUADRANT']
        u_y = int(row['UNIT_INDEX_Y'])
        g_x = u_x + (panel_cols if q in ['Q2', 'Q4'] else 0)
        g_y = u_y + (panel_rows if q in ['Q3', 'Q4'] else 0)
        global_indices.append((g_x, g_y))

    heatmap_df = pd.DataFrame(global_indices, columns=['Global_X', 'Global_Y'])
    heatmap_data = heatmap_df.groupby(['Global_X', 'Global_Y']).size().reset_index(name='Count')

    fig = go.Figure(data=go.Heatmap(x=heatmap_data['Global_X'], y=heatmap_data['Global_Y'], z=heatmap_data['Count'], colorscale='Magma', xgap=2, ygap=2, colorbar=dict(title='Defects', title_font=dict(color=text_color), tickfont=dict(color=text_color), hovertemplate='Global Unit: (%{x}, %{y})<br>Defects: %{z}<extra></extra>')))
    total_global_cols = panel_cols * 2
    total_global_rows = panel_rows * 2
    apply_panel_theme(fig, "1. Unit Grid Density (Yield Loss Map)", height=700, theme_config=theme_config)
    fig.update_layout(xaxis=dict(title="Global Unit Column", tickmode='linear', dtick=1, range=[-0.5, total_global_cols - 0.5], constrain='domain'), yaxis=dict(title="Global Unit Row", tickmode='linear', dtick=1, range=[-0.5, total_global_rows - 0.5]))
    return fig
