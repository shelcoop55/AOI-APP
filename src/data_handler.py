"""
Data Handling Module.
This version calculates defect locations based on a true-to-scale simulation
of a fixed-size 510x510mm physical panel.
"""
import streamlit as st
import pandas as pd
import numpy as np
import re
from typing import List, Dict, Set, Tuple, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from streamlit.runtime.uploaded_file_manager import UploadedFile

# Import constants from the configuration file
from .config import PANEL_WIDTH, PANEL_HEIGHT, GAP_SIZE, SAFE_VERIFICATION_VALUES_UPPER, DEFAULT_OFFSET_X, DEFAULT_OFFSET_Y, INTER_UNIT_GAP, DEFAULT_PANEL_ROWS, DEFAULT_PANEL_COLS
from .models import PanelData, BuildUpLayer

# --- DEFECT DEFINITIONS ---
DEFECT_DEFINITIONS = [
    ("CU10", "Copper Void (Nick)"), ("CU14", "Copper Void on Copper Ground"),
    ("CU18", "Short on the Surface (AOI)"), ("CU17", "Plating Under Resist (Fine Short)"),
    ("CU22", "Copper Residue"), ("CU16", "Open on the Surface (AOI)"),
    ("CU54", "Copper Distribution Not Even / Nodule"), ("CU25", "Rough Trace"),
    ("CU15", "Fine Short (Burr)"), ("CU94", "Global Copper Thickness Out of Spec – Copper Sting"),
    ("CU19", "Eless Remaining (Chemical Copper Residue)"), ("CU20", "Circle Defect"),
    ("CU41", "Copper Coloration or Spots"), ("CU80", "Risk to Via Integrity (Core)"),
    ("BM31", "Base Material Defect (Irregular Shape)"), ("BM01", "Base Material Defect (Crack)"),
    ("BM10", "Base Material Defect (Crack)"), ("BM34", "Measling / Crazing (White Spots)"),
    ("GE01", "Scratch"), ("GE32", "ABF Wrinkle"), ("GE57", "Foreign Material"),
    ("GE22", "Process Residue"), ("HO31", "Via Not Completely Filled"), ("HO12", "Hole Shift")
]

SIMPLE_DEFECT_TYPES = [
    'Nick', 'Short', 'Cut', 'Island', 'Space', 'Minimum Line', 'Line Nick', 'Deformation', 'Protrusion', 'Added Feature'
]

FALSE_ALARMS = ["N", "FALSE"]

@st.cache_data(show_spinner="Loading Data...")
def load_data(
    uploaded_files: List[Any], # Using Any to be safe across Streamlit versions, though UploadedFile is ideal
    panel_rows: int,
    panel_cols: int,
    panel_width: float = PANEL_WIDTH,
    panel_height: float = PANEL_HEIGHT,
    gap_x: float = GAP_SIZE,
    gap_y: float = GAP_SIZE
) -> PanelData:
    """
    Loads defect data from multiple build-up layer files, validates filenames,
    and processes each layer's data. Returns a PanelData object.
    """
    panel_data = PanelData()

    if uploaded_files:
        temp_data: Dict[int, Dict[str, List[pd.DataFrame]]] = {}

        for uploaded_file in uploaded_files:
            file_name = uploaded_file.name
            match = re.match(r"BU-(\d{2})\s*([FB])", file_name, re.IGNORECASE)

            if not match:
                st.warning(f"Skipping file: '{file_name}'. Name must follow 'BU-XXF' or 'BU-XXB' format.")
                continue

            layer_num, side = int(match.group(1)), match.group(2).upper()

            try:
                # Use calamine for speed
                df = pd.read_excel(uploaded_file, sheet_name='Defects', engine='calamine')
                df.rename(columns={'VERIFICATION': 'Verification'}, inplace=True)
                df['SOURCE_FILE'] = file_name
                df['SIDE'] = side

                has_verification_data = 'Verification' in df.columns
                if not has_verification_data:
                    df['Verification'] = 'Under Verification'
                else:
                    df['Verification'] = df['Verification'].fillna('N').astype(str).str.strip().str.upper()
                    df['Verification'] = df['Verification'].replace('', 'N')

                df['HAS_VERIFICATION_DATA'] = has_verification_data

                required_columns = ['DEFECT_ID', 'DEFECT_TYPE', 'UNIT_INDEX_X', 'UNIT_INDEX_Y']
                if not all(col in df.columns for col in required_columns):
                    st.error(f"File '{file_name}' is missing columns: {required_columns}.")
                    continue

                df.dropna(subset=required_columns, inplace=True)

                # Type Hygiene
                df['UNIT_INDEX_X'] = df['UNIT_INDEX_X'].astype('int32')
                df['UNIT_INDEX_Y'] = df['UNIT_INDEX_Y'].astype('int32')
                df['DEFECT_ID'] = pd.to_numeric(df['DEFECT_ID'], errors='coerce').fillna(-1).astype('int32')

                df['DEFECT_TYPE'] = df['DEFECT_TYPE'].str.strip().astype('category')
                df['Verification'] = df['Verification'].astype('category')
                df['SIDE'] = df['SIDE'].astype('category')
                df['SOURCE_FILE'] = df['SOURCE_FILE'].astype('category')

                # Coordinate Handling
                df['PHYSICAL_X'] = df['UNIT_INDEX_X']
                if side == 'B':
                    total_width_units = 2 * panel_cols
                    df['PHYSICAL_X'] = (total_width_units - 1) - df['UNIT_INDEX_X']

                if layer_num not in temp_data: temp_data[layer_num] = {}
                if side not in temp_data[layer_num]: temp_data[layer_num][side] = []
                temp_data[layer_num][side].append(df)

            except ValueError:
                st.error(f"Error in '{file_name}': 'Defects' sheet not found.")
                continue
            except Exception as e:
                st.error(f"Error reading '{file_name}': {e}")
                continue
        
        for layer_num, sides in temp_data.items():
            for side, dfs in sides.items():
                merged_df = pd.concat(dfs, ignore_index=True)
                layer_obj = BuildUpLayer(layer_num, side, merged_df, panel_rows, panel_cols, panel_width, panel_height, gap_x, gap_y)
                panel_data.add_layer(layer_obj)

    else:
        # Vectorized Sample Data Generation
        total_units_x = 2 * panel_cols
        total_units_y = 2 * panel_rows
        np.random.seed(55)
        layers_to_generate = [1, 2, 3, 4, 5]

        # Grid Params
        quad_w = panel_width / 2
        quad_h = panel_height / 2
        cell_w = (quad_w - (panel_cols + 1) * INTER_UNIT_GAP) / panel_cols
        cell_h = (quad_h - (panel_rows + 1) * INTER_UNIT_GAP) / panel_rows
        stride_x = cell_w + INTER_UNIT_GAP
        stride_y = cell_h + INTER_UNIT_GAP

        layer_counts = {1: (80, 101), 2: (200, 301), 3: (50, 61), 4: (40, 81), 5: (100, 201)}

        for layer_num in layers_to_generate:
            false_alarm_rate = np.random.uniform(0.5, 0.6)
            for side in ['F', 'B']:
                low, high = layer_counts.get(layer_num, (100, 151))
                num_points = np.random.randint(low, high)

                # Vectorized generation of unit indices
                unit_x = np.random.randint(0, total_units_x, num_points)
                unit_y = np.random.randint(0, total_units_y, num_points)

                # Vectorized Quadrant and Local Index Calc
                qx = (unit_x >= panel_cols).astype(int)
                qy = (unit_y >= panel_rows).astype(int)
                lx = unit_x % panel_cols
                ly = unit_y % panel_rows

                # Calculate Bounds
                quad_off_x = qx * (quad_w + gap_x)
                quad_off_y = qy * (quad_h + gap_y)
                local_off_x = INTER_UNIT_GAP + lx * stride_x
                local_off_y = INTER_UNIT_GAP + ly * stride_y

                x_start = DEFAULT_OFFSET_X + quad_off_x + local_off_x
                y_start = DEFAULT_OFFSET_Y + quad_off_y + local_off_y

                # Generate Random Coords (Vectorized)
                rx = np.random.uniform(x_start, x_start + cell_w)
                ry = np.random.uniform(y_start, y_start + cell_h)

                rand_x_coords = rx * 1000 # microns
                rand_y_coords = ry * 1000

                # Defect Types and Verifications (Vectorized Choice)
                defect_types = np.random.choice(SIMPLE_DEFECT_TYPES, num_points)

                # Verification Logic
                is_false = np.random.rand(num_points) < false_alarm_rate
                verifications = np.empty(num_points, dtype=object)

                # Fill False Alarms
                verifications[is_false] = np.random.choice(FALSE_ALARMS, size=np.sum(is_false))

                # Fill True Defects
                # Create definitions array for choice
                def_codes = [d[0] for d in DEFECT_DEFINITIONS]
                verifications[~is_false] = np.random.choice(def_codes, size=np.sum(~is_false))

                start_id = layer_num * 1000 + (0 if side == 'F' else 500)

                defect_data = {
                    'DEFECT_ID': np.arange(start_id, start_id + num_points),
                    'UNIT_INDEX_X': unit_x,
                    'UNIT_INDEX_Y': unit_y,
                    'DEFECT_TYPE': defect_types,
                    'Verification': verifications,
                    'SOURCE_FILE': [f'Sample Data Layer {layer_num}{side}'] * num_points,
                    'SIDE': [side] * num_points,
                    'HAS_VERIFICATION_DATA': [True] * num_points,
                    'X_COORDINATES': rand_x_coords,
                    'Y_COORDINATES': rand_y_coords
                }

                df = pd.DataFrame(defect_data)
                layer_obj = BuildUpLayer(layer_num, side, df, panel_rows, panel_cols, panel_width, panel_height, gap_x, gap_y)
                panel_data.add_layer(layer_obj)

    return panel_data

# NOTE: aggregate_stress_data, calculate_yield_killers, get_true_defect_coordinates, prepare_multi_layer_data, get_cross_section_matrix
# have been moved to src/analysis/calculations.py or src/analysis/services.py to avoid circular dependencies and consolidate logic.
