"""
Analysis Calculations Module.

This module contains functions for performing defect analysis calculations,
separating business logic from data loading and UI concerns.
"""
import pandas as pd
import numpy as np
import streamlit as st
from dataclasses import dataclass
from typing import Dict, Tuple, Any, Optional, List
from src.models import PanelData, StressMapData, YieldKillerMetrics
from src.config import SAFE_VERIFICATION_VALUES_UPPER

@dataclass
class FilterContext:
    """Encapsulates filter parameters for analysis functions."""
    selected_layers: Optional[List[int]] = None
    selected_sides: Optional[List[str]] = None
    verification_filter: Optional[List[str]] = None
    quadrant_filter: str = "All"
    # Legacy/Specific filters
    excluded_layers: Optional[List[int]] = None
    excluded_defect_types: Optional[List[str]] = None

@st.cache_data
def get_true_defect_coordinates(
    _panel_data: PanelData,
    filter_context: Optional[FilterContext] = None
) -> Dict[Tuple[int, int], Dict[str, Any]]:
    """
    Aggregates all "True" defects to find unique defective cell coordinates.
    """
    if not _panel_data:
        return {}

    all_layers_df = _panel_data.get_combined_dataframe()
    if all_layers_df.empty or 'Verification' not in all_layers_df.columns:
        return {}

    # Apply Filters if context provided
    if filter_context:
        # Excluded Layers (What-If)
        if filter_context.excluded_layers:
            all_layers_df = all_layers_df[~all_layers_df['LAYER_NUM'].isin(filter_context.excluded_layers)]

        # Selected Sides (Included)
        # Note: 'selected_sides' usually ['F', 'B']. If None, assume all?
        # get_true_defect_coordinates usually takes "included_sides".
        # Mapping: selected_sides IS included_sides
        if filter_context.selected_sides:
             all_layers_df = all_layers_df[all_layers_df['SIDE'].isin(filter_context.selected_sides)]

        # Excluded Defect Types (What-If)
        if filter_context.excluded_defect_types:
            all_layers_df = all_layers_df[~all_layers_df['Verification'].isin(filter_context.excluded_defect_types)]

    if all_layers_df.empty:
        return {}

    # Filter for True Defects
    is_true_defect = ~all_layers_df['Verification'].isin(SAFE_VERIFICATION_VALUES_UPPER)
    true_defects_df = all_layers_df[is_true_defect].copy()

    if true_defects_df.empty:
        return {}

    if 'PHYSICAL_X' not in true_defects_df.columns:
        true_defects_df['PHYSICAL_X'] = true_defects_df['UNIT_INDEX_X']

    # Vectorized string creation for summary
    # We need "L{num}: {count}" per unit
    # Group by [PX, PY, LayerNum] -> count
    layer_counts = true_defects_df.groupby(['PHYSICAL_X', 'UNIT_INDEX_Y', 'LAYER_NUM']).size().reset_index(name='Count')

    # Create string "Ln: c"
    layer_counts['Summary'] = "L" + layer_counts['LAYER_NUM'].astype(str) + ": " + layer_counts['Count'].astype(str)

    # Group by Unit and join
    unit_summary = layer_counts.groupby(['PHYSICAL_X', 'UNIT_INDEX_Y'])['Summary'].apply(lambda x: ", ".join(x))

    # First Killer: Min Layer Num per unit
    first_killer = true_defects_df.groupby(['PHYSICAL_X', 'UNIT_INDEX_Y'])['LAYER_NUM'].min()

    # Combine
    result = {}
    # Iterate over the index (which is PX, PY)
    # This is much faster than iterating rows if N is large, but still Python loop.
    # Given output is a Dict, we must loop eventually or use to_dict.

    # Align indices
    combined = pd.DataFrame({'first': first_killer, 'summary': unit_summary})

    for (px, py), row in combined.iterrows():
        result[(px, py)] = {
            'first_killer_layer': int(row['first']),
            'defect_summary': row['summary']
        }

    return result

@st.cache_data
def prepare_multi_layer_data(_panel_data: PanelData, panel_uid: str = "") -> pd.DataFrame:
    """
    Aggregates and filters defect data from all layers for the Multi-Layer Defect View.
    """
    if not _panel_data:
        return pd.DataFrame()

    def true_defect_filter(df):
        if 'Verification' in df.columns:
            return df[~df['Verification'].isin(SAFE_VERIFICATION_VALUES_UPPER)]
        return df

    return _panel_data.get_combined_dataframe(filter_func=true_defect_filter)

def aggregate_stress_data_from_df(
    df: pd.DataFrame,
    panel_rows: int,
    panel_cols: int
) -> StressMapData:
    """
    Core logic to aggregate a DataFrame into a StressMapData object.
    """
    total_cols = panel_cols * 2
    total_rows = panel_rows * 2

    grid_counts = np.zeros((total_rows, total_cols), dtype=int)
    hover_text = np.empty((total_rows, total_cols), dtype=object)
    hover_text[:] = "No Defects"

    if df.empty:
         return StressMapData(grid_counts, hover_text, 0, 0)

    if 'UNIT_INDEX_X' not in df.columns or 'UNIT_INDEX_Y' not in df.columns:
        return StressMapData(grid_counts, hover_text, 0, 0)

    x_coords = df['UNIT_INDEX_X'].values
    y_coords = df['UNIT_INDEX_Y'].values

    valid_mask = (x_coords >= 0) & (x_coords < total_cols) & (y_coords >= 0) & (y_coords < total_rows)
    x_coords = x_coords[valid_mask]
    y_coords = y_coords[valid_mask]

    if len(x_coords) == 0:
        return StressMapData(grid_counts, hover_text, 0, 0)

    # 1. Grid Counts (Vectorized)
    hist, _, _ = np.histogram2d(
        y_coords, x_coords,
        bins=[total_rows, total_cols],
        range=[[0, total_rows], [0, total_cols]]
    )
    grid_counts = hist.astype(int)
    total_defects_acc = int(grid_counts.sum())
    max_count_acc = int(grid_counts.max()) if total_defects_acc > 0 else 0

    # 2. Hover Text (Vectorized String Ops)
    valid_df = df[valid_mask]

    if 'DEFECT_TYPE' in valid_df.columns:
        # Count by Cell + Type
        type_counts = valid_df.groupby(['UNIT_INDEX_Y', 'UNIT_INDEX_X', 'DEFECT_TYPE'], observed=True).size().reset_index(name='Count')

        # Calculate Total per Cell (for Header)
        cell_totals = type_counts.groupby(['UNIT_INDEX_Y', 'UNIT_INDEX_X'])['Count'].sum()

        # Sort and take top 3
        type_counts.sort_values(['UNIT_INDEX_Y', 'UNIT_INDEX_X', 'Count'], ascending=[True, True, False], inplace=True)
        top_3 = type_counts.groupby(['UNIT_INDEX_Y', 'UNIT_INDEX_X']).head(3)

        # Create line strings: "Type: Count"
        top_3['line'] = top_3['DEFECT_TYPE'].astype(str) + ": " + top_3['Count'].astype(str)

        # Aggregate lines into list per cell
        lines_series = top_3.groupby(['UNIT_INDEX_Y', 'UNIT_INDEX_X'])['line'].apply(list)

        # Count types per cell (to show "+ X types")
        types_per_cell = type_counts.groupby(['UNIT_INDEX_Y', 'UNIT_INDEX_X']).size()

        # Build final string (Iterate only over populated cells, much faster than all cells)
        # Using a dictionary map

        # We need to map (Y, X) to string.
        # Let's iterate the grouped object which is aligned.

        # Merge cell_totals, lines_series, types_per_cell
        # Index is (Y, X)
        summary_df = pd.DataFrame({
            'Total': cell_totals,
            'Lines': lines_series,
            'TypeCount': types_per_cell
        })

        for (y, x), row in summary_df.iterrows():
            total = row['Total']
            lines = row['Lines']
            count = row['TypeCount']

            tooltip = f"<b>Total: {total}</b><br>" + "<br>".join(lines)
            if count > 3:
                tooltip += f"<br>... (+{count - 3} types)"

            hover_text[int(y), int(x)] = tooltip

    else:
        grouped = valid_df.groupby(['UNIT_INDEX_Y', 'UNIT_INDEX_X']).size()
        for (y, x), count in grouped.items():
            hover_text[int(y), int(x)] = f"<b>Total: {count}</b>"

    return StressMapData(
        grid_counts=grid_counts,
        hover_text=hover_text,
        total_defects=total_defects_acc,
        max_count=max_count_acc
    )

@st.cache_data
def aggregate_stress_data(
    _panel_data: PanelData,
    filter_context: Optional[FilterContext],
    panel_rows: int,
    panel_cols: int,
    panel_uid: str = ""
) -> StressMapData:
    """
    Aggregates data for the Cumulative Stress Map using filters.
    """
    # Use the combined dataframe with filters
    if not _panel_data:
        return StressMapData(np.zeros((panel_rows*2, panel_cols*2), int), np.empty((panel_rows*2, panel_cols*2), object), 0, 0)

    # 1. Base DF (All layers/sides potentially)
    # We need to respect "selected_layers" and "selected_sides" in context

    # Construct filter function? Or just filter the big DF.
    # get_combined_dataframe copies data. If we pass filter_func it might save memory?
    # But get_combined_dataframe implementation iterates and copies.

    df = _panel_data.get_combined_dataframe()

    if df.empty:
        return StressMapData(np.zeros((panel_rows*2, panel_cols*2), int), np.empty((panel_rows*2, panel_cols*2), object), 0, 0)

    if filter_context:
        # Filter Layers
        if filter_context.selected_layers:
            df = df[df['LAYER_NUM'].isin(filter_context.selected_layers)]

        # Filter Sides
        if filter_context.selected_sides:
            df = df[df['SIDE'].isin(filter_context.selected_sides)]

        # Filter Verif
        if filter_context.verification_filter and 'Verification' in df.columns:
             df = df[df['Verification'].astype(str).isin(filter_context.verification_filter)]

        # Filter Quadrant
        if filter_context.quadrant_filter != "All" and 'QUADRANT' in df.columns:
             df = df[df['QUADRANT'] == filter_context.quadrant_filter]

    # Standard True Defect Filter
    if 'Verification' in df.columns:
        df = df[~df['Verification'].isin(SAFE_VERIFICATION_VALUES_UPPER)]

    return aggregate_stress_data_from_df(df, panel_rows, panel_cols)

@st.cache_data
def calculate_yield_killers(
    _panel_data: PanelData,
    panel_rows: int,
    panel_cols: int,
    filter_context: Optional[FilterContext] = None
) -> Optional[YieldKillerMetrics]:
    """
    Calculates the 'Yield Killer' KPIs. Respects filters if provided.
    """
    if not _panel_data: return None

    df = _panel_data.get_combined_dataframe()

    # Apply Filters (Logic similar to aggregate_stress_data)
    if filter_context:
        if filter_context.selected_layers:
            df = df[df['LAYER_NUM'].isin(filter_context.selected_layers)]
        if filter_context.selected_sides:
            df = df[df['SIDE'].isin(filter_context.selected_sides)]
        if filter_context.verification_filter and 'Verification' in df.columns:
             df = df[df['Verification'].astype(str).isin(filter_context.verification_filter)]
        if filter_context.quadrant_filter != "All" and 'QUADRANT' in df.columns:
             df = df[df['QUADRANT'] == filter_context.quadrant_filter]

    if df.empty: return None

    # Filter True Defects
    if 'Verification' in df.columns:
        df = df[~df['Verification'].isin(SAFE_VERIFICATION_VALUES_UPPER)]

    if df.empty: return None

    # 1. Worst Layer
    layer_counts = df['LAYER_NUM'].value_counts()
    if layer_counts.empty: return None
    top_killer_layer_id = layer_counts.idxmax()
    top_killer_count = layer_counts.max()
    top_killer_label = f"Layer {top_killer_layer_id}"

    # 2. Worst Unit
    unit_counts = df.groupby(['UNIT_INDEX_X', 'UNIT_INDEX_Y']).size()
    if unit_counts.empty:
        worst_unit_label = "N/A"
        worst_unit_count = 0
    else:
        worst_unit_coords = unit_counts.idxmax()
        worst_unit_count = unit_counts.max()
        worst_unit_label = f"X:{worst_unit_coords[0]}, Y:{worst_unit_coords[1]}"

    # 3. Side Bias
    side_counts = df['SIDE'].value_counts()
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

@st.cache_data
def get_cross_section_matrix(
    _panel_data: PanelData,
    slice_axis: str,
    slice_index: int,
    panel_rows: int,
    panel_cols: int,
    filter_context: Optional[FilterContext] = None
) -> Tuple[np.ndarray, List[str], List[str]]:
    """
    Constructs the 2D cross-section matrix.
    """
    # Optimized implementation: Use filtered DF directly instead of iterating
    sorted_layers = _panel_data.get_all_layer_nums()
    if not sorted_layers:
        return np.zeros((0,0)), [], []

    total_cols = panel_cols * 2
    total_rows = panel_rows * 2

    if slice_axis == 'Y':
        width_dim = total_cols
        axis_labels = [str(i) for i in range(width_dim)]
    else:
        width_dim = total_rows
        axis_labels = [str(i) for i in range(width_dim)]

    matrix = np.zeros((len(sorted_layers), width_dim), dtype=int)
    layer_map = {num: i for i, num in enumerate(sorted_layers)}
    layer_labels = [f"L{num}" for num in sorted_layers]

    # Get Data
    df = _panel_data.get_combined_dataframe()

    # Apply Filters (Context)
    if filter_context:
        if filter_context.selected_layers:
            df = df[df['LAYER_NUM'].isin(filter_context.selected_layers)]
        if filter_context.selected_sides:
            df = df[df['SIDE'].isin(filter_context.selected_sides)]
        if filter_context.verification_filter and 'Verification' in df.columns:
             df = df[df['Verification'].astype(str).isin(filter_context.verification_filter)]

    if df.empty: return matrix, layer_labels, axis_labels

    # True Defect Filter
    if 'Verification' in df.columns:
        df = df[~df['Verification'].isin(SAFE_VERIFICATION_VALUES_UPPER)]

    # Slice Filter
    if slice_axis == 'Y':
        # Slice by Y (Row), X is the axis
        sliced = df[df['UNIT_INDEX_Y'] == slice_index]
        target_col = 'UNIT_INDEX_X'
    else:
        sliced = df[df['UNIT_INDEX_X'] == slice_index]
        target_col = 'UNIT_INDEX_Y'

    if sliced.empty:
        return matrix, layer_labels, axis_labels

    # Aggregate
    # Group by Layer and Target Coordinate
    counts = sliced.groupby(['LAYER_NUM', target_col]).size()

    # Fill Matrix
    for (layer_num, coord), count in counts.items():
        if layer_num in layer_map and 0 <= coord < width_dim:
            row_idx = layer_map[layer_num]
            matrix[row_idx, int(coord)] = count

    return matrix, layer_labels, axis_labels

@st.cache_data
def calculate_layer_summary(
    # We pass necessary dataframes or identifiers
    # Passing layer_info dict might be heavy if not careful, but it's references to DFs
    # layer_info is {side: df}
    layer_info_data: Dict[str, pd.DataFrame],
    panel_rows: int,
    panel_cols: int,
    quadrant_selection: str
) -> Dict[str, Any]:
    """
    Calculates summary metrics for the Layer View.
    """
    summary = {}

    # Concatenate sides
    dfs = list(layer_info_data.values())
    if not dfs:
        return {}

    full_layer_df = pd.concat(dfs, ignore_index=True)

    # 1. Yield Data (True Defects only)
    is_true_defect = ~full_layer_df['Verification'].isin(SAFE_VERIFICATION_VALUES_UPPER) if 'Verification' in full_layer_df.columns else pd.Series([True]*len(full_layer_df))
    yield_df = full_layer_df[is_true_defect]

    total_cells_panel = panel_rows * panel_cols

    # Panel Wide Yield (All 4 quadrants)
    # Total units = rows * cols * 4
    total_units_board = total_cells_panel * 4

    # Defective cells board
    defective_cells_board = len(yield_df[['UNIT_INDEX_X', 'UNIT_INDEX_Y']].drop_duplicates())
    yield_board = (total_units_board - defective_cells_board) / total_units_board if total_units_board > 0 else 0

    summary['yield_board'] = yield_board
    summary['defective_cells_board'] = defective_cells_board

    # Quadrant Specific
    if quadrant_selection != "All":
        quad_yield_df = yield_df[yield_df['QUADRANT'] == quadrant_selection]
        defective_cells_quad = len(quad_yield_df[['UNIT_INDEX_X', 'UNIT_INDEX_Y']].drop_duplicates())
        yield_quad = (total_cells_panel - defective_cells_quad) / total_cells_panel if total_cells_panel > 0 else 0

        summary['yield_quad'] = yield_quad
        summary['defective_cells_quad'] = defective_cells_quad

    return summary
