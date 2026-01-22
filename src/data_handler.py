"""
Data Handling Module.
This version calculates defect locations based on a true-to-scale simulation
of a fixed-size 510x510mm physical panel.
"""
import streamlit as st
import pandas as pd
import numpy as np
import re
from typing import List, Dict, Set, Tuple, Any, Optional

# Import constants from the configuration file
from .config import PANEL_WIDTH, PANEL_HEIGHT, GAP_SIZE, SAFE_VERIFICATION_VALUES_UPPER, DEFAULT_OFFSET_X, DEFAULT_OFFSET_Y, INTER_UNIT_GAP
from .models import PanelData, BuildUpLayer, StressMapData, YieldKillerMetrics

# --- DEFECT DEFINITIONS ---
# List of (Code, Description) tuples for data generation
DEFECT_DEFINITIONS = [
    # Copper-related (CU)
    ("CU10", "Copper Void (Nick)"),
    ("CU14", "Copper Void on Copper Ground"),
    ("CU18", "Short on the Surface (AOI)"),
    ("CU17", "Plating Under Resist (Fine Short)"),
    ("CU22", "Copper Residue"),
    ("CU16", "Open on the Surface (AOI)"),
    ("CU54", "Copper Distribution Not Even / Nodule"),
    ("CU25", "Rough Trace"),
    ("CU15", "Fine Short (Burr)"),
    ("CU94", "Global Copper Thickness Out of Spec – Copper Sting"),
    ("CU19", "Eless Remaining (Chemical Copper Residue)"),
    ("CU20", "Circle Defect"),
    ("CU41", "Copper Coloration or Spots"),
    ("CU80", "Risk to Via Integrity (Core)"),
    # Base Material (BM)
    ("BM31", "Base Material Defect (Irregular Shape)"),
    ("BM01", "Base Material Defect (Crack)"),
    ("BM10", "Base Material Defect (Crack)"), # Duplicate fix? Kept as original logic
    ("BM34", "Measling / Crazing (White Spots)"),
    # General (GE)
    ("GE01", "Scratch"),
    ("GE32", "ABF Wrinkle"),
    ("GE57", "Foreign Material"),
    ("GE22", "Process Residue"),
    # Hole-related (HO)
    ("HO31", "Via Not Completely Filled"),
    ("HO12", "Hole Shift")
]

# Simple Defect Types to be used as descriptions/types
SIMPLE_DEFECT_TYPES = [
    'Nick', 'Short', 'Cut', 'Island', 'Space',
    'Minimum Line', 'Line Nick', 'Deformation',
    'Protrusion', 'Added Feature'
]

FALSE_ALARMS = ["N", "FALSE"]

# Use st.cache_data with a hash function for the files to avoid re-reading
@st.cache_data(show_spinner="Loading Data...")
def load_data(
    uploaded_files: List[Any], # Changed to Any to handle potential Streamlit UploadedFile wrapper changes
    panel_rows: int,
    panel_cols: int,
    panel_width: float = PANEL_WIDTH, # Default to config if not provided
    panel_height: float = PANEL_HEIGHT,
    gap_x: float = GAP_SIZE,
    gap_y: float = GAP_SIZE
) -> PanelData:
    """
    Loads defect data from multiple build-up layer files, validates filenames
    (e.g., BU-01F..., BU-01B...), and processes each layer's data.
    Returns a PanelData object containing all layers.
    """
    panel_data = PanelData()

    if uploaded_files:
        # Temporary storage for concatenation
        temp_data: Dict[int, Dict[str, List[pd.DataFrame]]] = {}

        for uploaded_file in uploaded_files:
            file_name = uploaded_file.name
            match = re.match(r"BU-(\d{2})\s*([FB])", file_name, re.IGNORECASE)

            if not match:
                st.warning(f"Skipping file: '{file_name}'. Name must follow 'BU-XXF' or 'BU-XXB' format (e.g., 'BU-01F-...).")
                continue

            layer_num, side = int(match.group(1)), match.group(2).upper()

            try:
                # OPTIMIZATION: Use calamine engine for faster loading
                df = pd.read_excel(uploaded_file, sheet_name='Defects', engine='calamine')
                df.rename(columns={'VERIFICATION': 'Verification'}, inplace=True)
                df['SOURCE_FILE'] = file_name
                df['SIDE'] = side

                # --- VERIFICATION LOGIC UPDATE ---
                # Check if we have real verification data
                has_verification_data = 'Verification' in df.columns

                # 1. If 'Verification' column is missing, create it and mark as "Under Verification".
                # 2. If it exists, fill NaN/Blanks with 'N' (Safe).
                if not has_verification_data:
                    df['Verification'] = 'Under Verification'
                else:
                    # OPTIMIZATION: Normalize to uppercase once here
                    df['Verification'] = df['Verification'].fillna('N').astype(str).str.strip().str.upper()
                    # Also handle empty strings that might result from stripping
                    df['Verification'] = df['Verification'].replace('', 'N')

                # Store the flag in the DataFrame for use in plotting
                df['HAS_VERIFICATION_DATA'] = has_verification_data

                required_columns = ['DEFECT_ID', 'DEFECT_TYPE', 'UNIT_INDEX_X', 'UNIT_INDEX_Y']
                if not all(col in df.columns for col in required_columns):
                    st.error(f"File '{file_name}' is missing required columns: {required_columns}. It has been skipped.")
                    continue

                df.dropna(subset=required_columns, inplace=True)

                # OPTIMIZATION: Type Hygiene to reduce memory usage
                df['UNIT_INDEX_X'] = df['UNIT_INDEX_X'].astype('int32')
                df['UNIT_INDEX_Y'] = df['UNIT_INDEX_Y'].astype('int32')
                df['DEFECT_ID'] = pd.to_numeric(df['DEFECT_ID'], errors='coerce').fillna(-1).astype('int32')

                # Convert string columns to categorical if cardinality is low
                df['DEFECT_TYPE'] = df['DEFECT_TYPE'].str.strip().astype('category')
                df['Verification'] = df['Verification'].astype('category')
                df['SIDE'] = df['SIDE'].astype('category')
                df['SOURCE_FILE'] = df['SOURCE_FILE'].astype('category')

                # --- COORDINATE HANDLING (RAW vs PHYSICAL) ---
                # RAW: UNIT_INDEX_X from the file (used for Individual Layer View).
                # PHYSICAL: Flipped for Back side to align with Front side (used for Yield/Heatmaps).

                df['PHYSICAL_X'] = df['UNIT_INDEX_X'] # Default to Raw

                if side == 'B':
                    # Back side is mirrored. Calculate Physical X.
                    total_width_units = 2 * panel_cols
                    df['PHYSICAL_X'] = (total_width_units - 1) - df['UNIT_INDEX_X']

                if layer_num not in temp_data: temp_data[layer_num] = {}
                if side not in temp_data[layer_num]: temp_data[layer_num][side] = []

                temp_data[layer_num][side].append(df)

            except ValueError:
                st.error(f"Error in '{file_name}': A sheet named 'Defects' was not found.")
                continue
            except Exception as e:
                st.error(f"An unexpected error occurred while reading '{file_name}': {e}")
                continue
        
        # Build PanelData
        for layer_num, sides in temp_data.items():
            for side, dfs in sides.items():
                merged_df = pd.concat(dfs, ignore_index=True)
                # Pass gap_x and gap_y to BuildUpLayer
                layer_obj = BuildUpLayer(layer_num, side, merged_df, panel_rows, panel_cols, panel_width, panel_height, gap_x, gap_y)
                panel_data.add_layer(layer_obj)

        if panel_data:
            # Avoid sidebar updates in cached function to prevent st.fragment errors
            pass

    else:
        # Avoid sidebar updates in cached function to prevent st.fragment errors
        # st.sidebar.info("No file uploaded. Displaying sample data for 5 layers (all with Front/Back).")
        total_units_x = 2 * panel_cols
        total_units_y = 2 * panel_rows

        # 4. Define a Seed (Set it once before generation)
        np.random.seed(55)

        # 1. Add two more layers (5 total)
        layers_to_generate = [1, 2, 3, 4, 5]

        # 2. Define custom ranges for data points per layer
        # Ranges: 1 (80-100), 2 (200-300), 3 (50-60), 4 (40-80), 5 (100-200)
        layer_counts = {
            1: (80, 101),
            2: (200, 301),
            3: (50, 61),
            4: (40, 81),
            5: (100, 201)
        }

        # Calculate Grid Parameters for accurate physical simulation
        quad_w = panel_width / 2
        quad_h = panel_height / 2

        # New Logic: (n+1) gaps
        cell_w = (quad_w - (panel_cols + 1) * INTER_UNIT_GAP) / panel_cols
        cell_h = (quad_h - (panel_rows + 1) * INTER_UNIT_GAP) / panel_rows

        stride_x = cell_w + INTER_UNIT_GAP
        stride_y = cell_h + INTER_UNIT_GAP

        for layer_num in layers_to_generate:
            # Random False Alarm Rate for this layer (50% - 60%)
            false_alarm_rate = np.random.uniform(0.5, 0.6)

            for side in ['F', 'B']:
                # Random number of points based on layer
                low, high = layer_counts.get(layer_num, (100, 151))
                num_points = np.random.randint(low, high)

                # 3. Define Random X and Y coordinates fully respecting the Grid Guide
                # The user guide specifies margins (18.5) and gaps (3.0).
                # To simulate this correctly, we must pick a valid Unit Cell first,
                # then generate a random coordinate WITHIN that cell's physical bounds.

                rand_x_coords_mm = []
                rand_y_coords_mm = []
                final_unit_x = []
                final_unit_y = []

                for _ in range(num_points):
                    # Pick a random Unit Index
                    ux = np.random.randint(0, total_units_x)
                    uy = np.random.randint(0, total_units_y)

                    final_unit_x.append(ux)
                    final_unit_y.append(uy)

                    # Determine Quadrant and Local Index
                    # Q1/Q3 are Columns 0-(panel_cols-1). Q2/Q4 are Columns panel_cols-...
                    qx = 1 if ux >= panel_cols else 0
                    qy = 1 if uy >= panel_rows else 0

                    lx = ux % panel_cols
                    ly = uy % panel_rows

                    # Calculate Min/Max Physical Bounds for this Cell
                    # Formula: Offset + (QuadrantOffset) + (LocalOffset)
                    # Quadrant Offset includes the Gap if qx=1 or qy=1
                    # Local Offset now includes initial INTER_UNIT_GAP

                    quad_off_x = qx * (quad_w + gap_x)
                    quad_off_y = qy * (quad_h + gap_y)

                    local_off_x = INTER_UNIT_GAP + lx * stride_x
                    local_off_y = INTER_UNIT_GAP + ly * stride_y

                    x_start = DEFAULT_OFFSET_X + quad_off_x + local_off_x
                    y_start = DEFAULT_OFFSET_Y + quad_off_y + local_off_y

                    x_end = x_start + cell_w
                    y_end = y_start + cell_h

                    # Generate uniform random coord within this cell
                    rx = np.random.uniform(x_start, x_end)
                    ry = np.random.uniform(y_start, y_end)

                    rand_x_coords_mm.append(rx)
                    rand_y_coords_mm.append(ry)

                rand_x_coords_mm = np.array(rand_x_coords_mm)
                rand_y_coords_mm = np.array(rand_y_coords_mm)

                # Convert mm to microns
                rand_x_coords = rand_x_coords_mm * 1000
                rand_y_coords = rand_y_coords_mm * 1000

                unit_x = np.array(final_unit_x)
                unit_y = np.array(final_unit_y)

                # Generate Defect Types and Verification statuses
                defect_types = []
                verifications = []

                for _ in range(num_points):
                    # Always use Simple Defect Types for the "Machine" view (DEFECT_TYPE)
                    desc = np.random.choice(SIMPLE_DEFECT_TYPES)
                    defect_types.append(desc)

                    # Decide Verification Status
                    if np.random.rand() < false_alarm_rate:
                        # False Alarm: Machine saw 'desc', verification is 'N' or 'FALSE'
                        verifications.append(np.random.choice(FALSE_ALARMS))
                    else:
                        # True Defect: Verification confirms a specific Code (e.g., CU10)
                        # We pick a random code from the definitions
                        code, _ = DEFECT_DEFINITIONS[np.random.randint(len(DEFECT_DEFINITIONS))]
                        verifications.append(code)

                defect_data = {
                    'DEFECT_ID': range(layer_num * 1000 + (0 if side == 'F' else 500), layer_num * 1000 + (0 if side == 'F' else 500) + num_points),
                    'UNIT_INDEX_X': unit_x,
                    'UNIT_INDEX_Y': unit_y,
                    'DEFECT_TYPE': defect_types,
                    'Verification': verifications,
                    'SOURCE_FILE': [f'Sample Data Layer {layer_num}{side}'] * num_points,
                    'SIDE': side,
                    'HAS_VERIFICATION_DATA': [True] * num_points,
                    'X_COORDINATES': rand_x_coords,
                    'Y_COORDINATES': rand_y_coords
                }

                df = pd.DataFrame(defect_data)
                layer_obj = BuildUpLayer(layer_num, side, df, panel_rows, panel_cols, panel_width, panel_height, gap_x, gap_y)
                panel_data.add_layer(layer_obj)

    return panel_data

# Kept for backward compatibility if other modules import directly,
# but they should use src.analysis.calculations
def get_true_defect_coordinates(
    panel_data: PanelData,
    excluded_layers: Optional[List[int]] = None,
    excluded_defect_types: Optional[List[str]] = None,
    included_sides: Optional[List[str]] = None
) -> Dict[Tuple[int, int], Dict[str, Any]]:
    from .analysis.calculations import get_true_defect_coordinates as _get_true_coords
    return _get_true_coords(panel_data, excluded_layers, excluded_defect_types, included_sides)

@st.cache_data
def prepare_multi_layer_data(_panel_data: PanelData, panel_uid: str = "") -> pd.DataFrame:
    """
    Aggregates and filters defect data from all layers for the Multi-Layer Defect View.
    """
    if not _panel_data:
        return pd.DataFrame()

    def true_defect_filter(df):
        if 'Verification' in df.columns:
            # Verification is already normalized to upper in load_data
            return df[~df['Verification'].isin(SAFE_VERIFICATION_VALUES_UPPER)]
        return df

    return _panel_data.get_combined_dataframe(filter_func=true_defect_filter)

@st.cache_data
def aggregate_stress_data(
    _panel_data: PanelData,
    selected_keys: List[Tuple[int, str]],
    panel_rows: int,
    panel_cols: int,
    panel_uid: str = "",
    verification_filter: Optional[List[str]] = None,
    quadrant_filter: str = "All"
) -> StressMapData:
    """
    Aggregates data for the Cumulative Stress Map using specific (Layer, Side) keys.
    """
    # OPTIMIZATION: Vectorized Aggregation
    dfs_to_agg = []
    for layer_num, side in selected_keys:
        layer = _panel_data.get_layer(layer_num, side)
        if layer and not layer.data.empty:
            dfs_to_agg.append(layer.data)

    if not dfs_to_agg:
        return StressMapData(np.zeros((panel_rows*2, panel_cols*2), int), np.empty((panel_rows*2, panel_cols*2), object), 0, 0)

    combined_df = pd.concat(dfs_to_agg, ignore_index=True)

    # Filter True Defects (Standard)
    if 'Verification' in combined_df.columns:
        # Verification is already normalized to upper in load_data
        is_true = ~combined_df['Verification'].astype(str).isin(SAFE_VERIFICATION_VALUES_UPPER)
        combined_df = combined_df[is_true]

    # Filter by Specific Selection (if provided)
    if verification_filter and 'Verification' in combined_df.columns and not combined_df.empty:
        combined_df = combined_df[combined_df['Verification'].astype(str).isin(verification_filter)]

    # Filter by Quadrant (if provided)
    if quadrant_filter != "All" and 'QUADRANT' in combined_df.columns and not combined_df.empty:
        combined_df = combined_df[combined_df['QUADRANT'] == quadrant_filter]

    from .analysis.calculations import aggregate_stress_data_from_df
    return aggregate_stress_data_from_df(combined_df, panel_rows, panel_cols)

@st.cache_data
def calculate_yield_killers(_panel_data: PanelData, panel_rows: int, panel_cols: int) -> Optional[YieldKillerMetrics]:
    """
    Calculates the 'Yield Killer' KPIs: Worst Layer, Worst Unit, Side Bias.
    """
    from .analysis.calculations import calculate_yield_killers as _calc_yield
    return _calc_yield(_panel_data, panel_rows, panel_cols)

@st.cache_data
def get_cross_section_matrix(
    _panel_data: PanelData,
    slice_axis: str,
    slice_index: int,
    panel_rows: int,
    panel_cols: int
) -> Tuple[np.ndarray, List[str], List[str]]:
    """
    Constructs the 2D cross-section matrix for Root Cause Analysis based on a single slice.

    slice_axis: 'Y' (By Row) or 'X' (By Column)
    slice_index: The index of the row or column to slice.
    """
    sorted_layers = _panel_data.get_all_layer_nums()
    num_layers = len(sorted_layers)
    if num_layers == 0:
        return np.zeros((0,0)), [], []

    total_cols = panel_cols * 2
    total_rows = panel_rows * 2

    # If Slicing by Row (Y), we show all Columns (X) -> width = total_cols
    # If Slicing by Column (X), we show all Rows (Y) -> width = total_rows

    if slice_axis == 'Y':
        width_dim = total_cols
        axis_labels = [str(i) for i in range(width_dim)]
    else:
        width_dim = total_rows
        axis_labels = [str(i) for i in range(width_dim)]

    matrix = np.zeros((num_layers, width_dim), dtype=int)
    layer_labels = [f"L{num}" for num in sorted_layers]

    for i, layer_num in enumerate(sorted_layers):
        sides = _panel_data._layers[layer_num] # Direct access to dict for now
        for side, layer_obj in sides.items():
            df = layer_obj.data
            if df.empty: continue

            # Optimization: Avoid full copy
            if 'Verification' in df.columns:
                is_true = ~df['Verification'].isin(SAFE_VERIFICATION_VALUES_UPPER)
                df_copy = df[is_true].copy() # Filter first then copy
            else:
                df_copy = df.copy()

            if df_copy.empty: continue

            # Filter by Slice
            if slice_axis == 'Y':
                # Fixed Y, variable X
                relevant_defects = df_copy[df_copy['UNIT_INDEX_Y'] == slice_index]
            else:
                # Fixed X, variable Y
                relevant_defects = df_copy[df_copy['UNIT_INDEX_X'] == slice_index]

            if relevant_defects.empty: continue

            # Aggregate
            if slice_axis == 'Y':
                # Group by X to fill columns of matrix
                counts = relevant_defects.groupby('UNIT_INDEX_X').size()
                for x_idx, count in counts.items():
                    if 0 <= x_idx < width_dim:
                        matrix[i, int(x_idx)] += count
            else:
                # Group by Y to fill columns of matrix (which represent Rows in the plot)
                counts = relevant_defects.groupby('UNIT_INDEX_Y').size()
                for y_idx, count in counts.items():
                    if 0 <= y_idx < width_dim:
                        matrix[i, int(y_idx)] += count

    return matrix, layer_labels, axis_labels
