"""
Analysis Calculations Module.

This module contains pure functions for performing defect analysis calculations,
separating business logic from data loading and UI concerns.
"""
import pandas as pd
import numpy as np
from typing import Dict, Tuple, Any, Optional, List
from src.models import PanelData, StressMapData, YieldKillerMetrics
from src.config import SAFE_VERIFICATION_VALUES_UPPER

def get_true_defect_coordinates(
    panel_data: PanelData,
    excluded_layers: Optional[List[int]] = None,
    excluded_defect_types: Optional[List[str]] = None,
    included_sides: Optional[List[str]] = None
) -> Dict[Tuple[int, int], Dict[str, Any]]:
    """
    Aggregates all "True" defects from all layers and sides to find unique
    defective cell coordinates for the Still Alive map.

    Returns:
        Dict mapping (physical_x, physical_y) -> {
            'first_killer_layer': int,
            'defects': List[str] # List of "L{num}: {count}"
        }
    """
    if not panel_data:
        return {}

    all_layers_df = panel_data.get_combined_dataframe()

    if all_layers_df.empty or 'Verification' not in all_layers_df.columns:
        return {}

    # Filter Excluded Layers ("What-If" Logic)
    if excluded_layers:
        all_layers_df = all_layers_df[~all_layers_df['LAYER_NUM'].isin(excluded_layers)]

    # Filter Included Sides
    if included_sides:
        all_layers_df = all_layers_df[all_layers_df['SIDE'].isin(included_sides)]

    if all_layers_df.empty:
        return {}

    # Filter Excluded Defect Types ("What-If" Logic) - Uses Verification Codes
    if excluded_defect_types:
        if 'Verification' in all_layers_df.columns:
            all_layers_df = all_layers_df[~all_layers_df['Verification'].isin(excluded_defect_types)]

    if all_layers_df.empty:
        return {}

    # Filter for True Defects
    # Verification is already normalized to upper in load_data
    is_true_defect = ~all_layers_df['Verification'].isin(SAFE_VERIFICATION_VALUES_UPPER)
    true_defects_df = all_layers_df[is_true_defect].copy()

    if true_defects_df.empty:
        return {}

    if 'PHYSICAL_X' not in true_defects_df.columns:
        true_defects_df['PHYSICAL_X'] = true_defects_df['UNIT_INDEX_X']

    # Aggregate Metadata per Unit
    # We want: First Killer Layer, and a Summary string

    # Group by Unit
    grouped = true_defects_df.groupby(['PHYSICAL_X', 'UNIT_INDEX_Y'])

    result = {}

    for (px, py), group in grouped:
        # Sort by Layer Num to find first killer
        sorted_group = group.sort_values('LAYER_NUM')
        first_killer = sorted_group.iloc[0]['LAYER_NUM']

        # Summarize defects: "L1: 5, L2: 3"
        layer_counts = sorted_group['LAYER_NUM'].value_counts().sort_index()
        summary_parts = [f"L{l}: {c}" for l, c in layer_counts.items()]

        result[(px, py)] = {
            'first_killer_layer': first_killer,
            'defect_summary': ", ".join(summary_parts)
        }

    return result

def aggregate_stress_data_from_df(
    df: pd.DataFrame,
    panel_rows: int,
    panel_cols: int
) -> StressMapData:
    """
    Core logic to aggregate a DataFrame into a StressMapData object.
    Accepts a pre-filtered DataFrame.
    """
    total_cols = panel_cols * 2
    total_rows = panel_rows * 2

    grid_counts = np.zeros((total_rows, total_cols), dtype=int)
    hover_text = np.empty((total_rows, total_cols), dtype=object)
    hover_text[:] = "No Defects" # Default

    if df.empty:
         return StressMapData(grid_counts, hover_text, 0, 0)

    # Vectorized Histogram
    # Use RAW COORDINATES (UNIT_INDEX_X)
    if 'UNIT_INDEX_X' not in df.columns or 'UNIT_INDEX_Y' not in df.columns:
        return StressMapData(grid_counts, hover_text, 0, 0)

    x_coords = df['UNIT_INDEX_X'].values
    y_coords = df['UNIT_INDEX_Y'].values

    # Filter out of bounds
    valid_mask = (x_coords >= 0) & (x_coords < total_cols) & (y_coords >= 0) & (y_coords < total_rows)
    x_coords = x_coords[valid_mask]
    y_coords = y_coords[valid_mask]

    if len(x_coords) == 0:
        return StressMapData(grid_counts, hover_text, 0, 0)

    # 1. Grid Counts
    hist, _, _ = np.histogram2d(
        y_coords, x_coords,
        bins=[total_rows, total_cols],
        range=[[0, total_rows], [0, total_cols]]
    )
    grid_counts = hist.astype(int)
    total_defects_acc = int(grid_counts.sum())
    max_count_acc = int(grid_counts.max()) if total_defects_acc > 0 else 0

    # 2. Hover Text (Group By Optimization)
    valid_df = df[valid_mask]

    if 'DEFECT_TYPE' in valid_df.columns:
        # Optimization: Avoid iterating through every cell group if possible
        # Use a vectorized approach or simplified tooltip for massive data

        # 1. Count by Cell + Type
        type_counts = valid_df.groupby(['UNIT_INDEX_Y', 'UNIT_INDEX_X', 'DEFECT_TYPE'], observed=True).size().reset_index(name='Count')

        # 2. Sort by Count descending within each cell (Y, X)
        type_counts.sort_values(['UNIT_INDEX_Y', 'UNIT_INDEX_X', 'Count'], ascending=[True, True, False], inplace=True)

        # 3. Calculate Total per Cell
        cell_totals = type_counts.groupby(['UNIT_INDEX_Y', 'UNIT_INDEX_X'])['Count'].sum()

        # 4. Get Top 3 per Cell
        top_3 = type_counts.groupby(['UNIT_INDEX_Y', 'UNIT_INDEX_X']).head(3)

        # 5. Count how many types per cell
        types_per_cell = type_counts.groupby(['UNIT_INDEX_Y', 'UNIT_INDEX_X']).size()

        # 6. Build Tooltip parts
        # Iterate over the groups of 'top_3' (simplified dataset)
        top_3_dict = {}
        for (y, x), group in top_3.groupby(['UNIT_INDEX_Y', 'UNIT_INDEX_X']):
             lines = [f"{row.DEFECT_TYPE}: {row.Count}" for row in group.itertuples()]
             top_3_dict[(y, x)] = lines

        for (y, x), total in cell_totals.items():
            lines = top_3_dict.get((y,x), [])
            tooltip = f"<b>Total: {total}</b><br>" + "<br>".join(lines)

            total_types = types_per_cell.get((y,x), 0)
            if total_types > 3:
                tooltip += f"<br>... (+{total_types - 3} types)"

            hover_text[y, x] = tooltip
    else:
        # Fallback if no Defect Type
        # Just show total count
        grouped = valid_df.groupby(['UNIT_INDEX_Y', 'UNIT_INDEX_X']).size()
        for (gy, gx), count in grouped.items():
            hover_text[gy, gx] = f"<b>Total: {count}</b>"

    return StressMapData(
        grid_counts=grid_counts,
        hover_text=hover_text,
        total_defects=total_defects_acc,
        max_count=max_count_acc
    )

def calculate_yield_killers(panel_data: PanelData, panel_rows: int, panel_cols: int) -> Optional[YieldKillerMetrics]:
    """
    Calculates the 'Yield Killer' KPIs: Worst Layer, Worst Unit, Side Bias.
    """
    if not panel_data: return None

    def true_defect_filter(df):
        if 'Verification' in df.columns:
            # Verification is already normalized to upper in load_data
            return df[~df['Verification'].isin(SAFE_VERIFICATION_VALUES_UPPER)]
        return df

    combined_df = panel_data.get_combined_dataframe(filter_func=true_defect_filter)

    if combined_df.empty: return None

    # 1. Worst Layer
    layer_counts = combined_df['LAYER_NUM'].value_counts()
    top_killer_layer_id = layer_counts.idxmax()
    top_killer_count = layer_counts.max()
    top_killer_label = f"Layer {top_killer_layer_id}"

    # 2. Worst Unit (Use RAW COORDINATES - UNIT_INDEX_X as per request)
    unit_counts = combined_df.groupby(['UNIT_INDEX_X', 'UNIT_INDEX_Y']).size()
    worst_unit_coords = unit_counts.idxmax() # Tuple (x, y)
    worst_unit_count = unit_counts.max()
    worst_unit_label = f"X:{worst_unit_coords[0]}, Y:{worst_unit_coords[1]}"

    # 3. Side Bias
    side_counts = combined_df['SIDE'].value_counts()
    f_count = side_counts.get('F', 0)
    b_count = side_counts.get('B', 0)

    diff = abs(f_count - b_count)
    if f_count > b_count:
        bias = "Front Side"
    elif b_count > f_count:
        bias = "Back Side"
    else:
        bias = "Balanced"

    return YieldKillerMetrics(
        top_killer_layer=top_killer_label,
        top_killer_count=int(top_killer_count),
        worst_unit=worst_unit_label,
        worst_unit_count=int(worst_unit_count),
        side_bias=bias,
        side_bias_diff=int(diff)
    )
