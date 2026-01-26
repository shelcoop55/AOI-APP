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
from io import BytesIO
from dataclasses import dataclass

# Import constants from the configuration file
from .config import PANEL_WIDTH, PANEL_HEIGHT, GAP_SIZE, SAFE_VERIFICATION_VALUES, DEFAULT_OFFSET_X, DEFAULT_OFFSET_Y, INTER_UNIT_GAP
from .models import PanelData, BuildUpLayer

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

@dataclass
class StressMapData:
    """Container for stress map aggregation results."""
    grid_counts: np.ndarray          # 2D array of total defect counts
    hover_text: np.ndarray           # 2D array of hover text strings
    total_defects: int               # Total defects in selection
    max_count: int                   # Max count in any single cell

@dataclass
class YieldKillerMetrics:
    """Container for Root Cause Analysis KPIs."""
    top_killer_layer: str
    top_killer_count: int
    worst_unit: str  # Format "X:col, Y:row"
    worst_unit_count: int
    side_bias: str   # "Front Side", "Back Side", or "Balanced"
    side_bias_diff: int

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

        df = pd.concat(all_dfs, ignore_index=True)
        st.sidebar.success(f"{len(uploaded_files)} file(s) loaded successfully!")
        df.rename(columns={'VERIFICATION': 'Verification'}, inplace=True)
        # Handle the new 'Verification' column for backward compatibility
        if 'Verification' not in df.columns:
            df['Verification'] = 'T'
        else:
            # Clean up the verification column, filling NaNs with 'T'
            df['Verification'] = df['Verification'].astype(str).fillna('T').str.strip()

        required_columns = ['DEFECT_ID', 'DEFECT_TYPE', 'UNIT_INDEX_X', 'UNIT_INDEX_Y']
        if not all(col in df.columns for col in required_columns):
            st.error(f"One or more uploaded files are missing required columns: {required_columns}")
            return pd.DataFrame()
            
        # No longer strictly filtering columns. This allows extra columns from the
        # source file to be preserved in the dataframe. The required columns check
        # above already ensures we have what we need.
        df.dropna(subset=required_columns, inplace=True)
        df['UNIT_INDEX_X'] = df['UNIT_INDEX_X'].astype(int)
        df['UNIT_INDEX_Y'] = df['UNIT_INDEX_Y'].astype(int)
        df['DEFECT_TYPE'] = df['DEFECT_TYPE'].str.strip()
        
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
    safe_values_upper = {v.upper() for v in SAFE_VERIFICATION_VALUES}
    # Verification is already normalized to upper in load_data
    is_true_defect = ~all_layers_df['Verification'].isin(safe_values_upper)
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
        df = pd.DataFrame(defect_data)

    # --- SIMULATION LOGIC ---

    # 1. Assign Quadrant based on UNIT_INDEX and user-defined grid resolution
    conditions = [
        (df['UNIT_INDEX_X'] < panel_cols) & (df['UNIT_INDEX_Y'] < panel_rows),    # Q1 (Bottom-Left)
        (df['UNIT_INDEX_X'] >= panel_cols) & (df['UNIT_INDEX_Y'] < panel_rows),   # Q2 (Bottom-Right)
        (df['UNIT_INDEX_X'] < panel_cols) & (df['UNIT_INDEX_Y'] >= panel_rows),   # Q3 (Top-Left)
        (df['UNIT_INDEX_X'] >= panel_cols) & (df['UNIT_INDEX_Y'] >= panel_rows)    # Q4 (Top-Right)
    ]
    choices = ['Q1', 'Q2', 'Q3', 'Q4']
    df['QUADRANT'] = np.select(conditions, choices, default='Other')
    
    # 2. Calculate the physical size (in mm) of a single grid cell
    cell_width = QUADRANT_WIDTH / panel_cols
    cell_height = QUADRANT_HEIGHT / panel_rows

    # 3. Translate UNIT_INDEX into physical coordinates
    
    # Find the local unit index (e.g., the 2nd column within its own quadrant)
    local_index_x = df['UNIT_INDEX_X'] % panel_cols
    local_index_y = df['UNIT_INDEX_Y'] % panel_rows

    # Calculate the base physical position (bottom-left corner of the cell in mm)
    plot_x_base = local_index_x * cell_width
    plot_y_base = local_index_y * cell_height

    # Determine the physical offset (in mm) for the quadrant itself
    x_offset = np.where(df['UNIT_INDEX_X'] >= panel_cols, QUADRANT_WIDTH + GAP_SIZE, 0)
    y_offset = np.where(df['UNIT_INDEX_Y'] >= panel_rows, QUADRANT_HEIGHT + GAP_SIZE, 0)

    # 4. Calculate the final plot coordinate with scaled jitter
    # The jitter places the defect randomly *inside* its cell, not just on the corner.
    jitter_x = np.random.rand(len(df)) * cell_width * 0.8 + (cell_width * 0.1)
    jitter_y = np.random.rand(len(df)) * cell_height * 0.8 + (cell_height * 0.1)

    df['plot_x'] = plot_x_base + x_offset + jitter_x
    df['plot_y'] = plot_y_base + y_offset + jitter_y
    
    return df

def calculate_yield_metrics(df: pd.DataFrame, total_cells: int) -> tuple[int, float]:
    """
    Calculates the number of defective cells and the yield estimate based on 'T' defects.

    A cell is defined as a unique combination of 'UNIT_INDEX_X' and 'UNIT_INDEX_Y'.
    It is considered defective if it contains at least one defect with a 'Verification'
    status of 'T'.

    Args:
        df: The input DataFrame containing defect data. Must include 'Verification',
            'UNIT_INDEX_X', and 'UNIT_INDEX_Y' columns.
        total_cells: The total number of cells in the area being analyzed.

    Returns:
        A tuple containing:
        - defective_cells (int): The count of unique cells with 'T' defects.
        - yield_estimate (float): The calculated yield (e.g., 0.95 for 95%).
    """
    if df.empty or total_cells <= 0:
        return 0, 1.0  # No defects and perfect yield if no data or no cells

    # Filter for defects that are verified as "True"
    true_defects = df[df['Verification'] == 'T']

    # Identify unique cells with at least one "True" defect
    if true_defects.empty:
        defective_cells = 0
    else:
        # Count the number of unique (X, Y) pairs
        defective_cells = len(true_defects[['UNIT_INDEX_X', 'UNIT_INDEX_Y']].drop_duplicates())

    # Calculate yield estimate
    yield_estimate = (total_cells - defective_cells) / total_cells

    return defective_cells, yield_estimate
