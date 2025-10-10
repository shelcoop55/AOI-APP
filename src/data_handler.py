"""
Data Handling Module.
This version calculates defect locations based on a true-to-scale simulation
of a fixed-size 510x510mm physical panel.
"""
import streamlit as st
import pandas as pd
import numpy as np
import re
from typing import List, Dict, Set, Tuple
from io import BytesIO

# Import constants from the configuration file
from .config import PANEL_WIDTH, PANEL_HEIGHT, GAP_SIZE

# --- DERIVED PHYSICAL CONSTANTS ---
# These constants are calculated from the primary dimensions in config.py
QUADRANT_WIDTH = PANEL_WIDTH / 2
QUADRANT_HEIGHT = PANEL_HEIGHT / 2

@st.cache_data
def load_data(
    uploaded_files: List[BytesIO],
    panel_rows: int,
    panel_cols: int,
) -> Dict[int, pd.DataFrame]:
    """
    Loads defect data from multiple build-up layer files, validates filenames,
    and processes each layer's data separately.
    Returns a dictionary mapping layer numbers to their corresponding DataFrames.
    """
    layer_data = {}

    if uploaded_files:
        for uploaded_file in uploaded_files:
            file_name = uploaded_file.name
            match = re.match(r"BU-(\d{2})", file_name, re.IGNORECASE)

            if not match:
                st.error(f"Invalid filename format: '{file_name}'. File was ignored. "
                         f"Filename must start with 'BU-XX' (e.g., 'BU-01-...).")
                continue

            layer_num = int(match.group(1))

            try:
                df = pd.read_excel(uploaded_file, sheet_name='Defects', engine='openpyxl')
                df['SOURCE_FILE'] = file_name

                if 'Verification' not in df.columns:
                    df['Verification'] = 'T'
                else:
                    df['Verification'] = df['Verification'].astype(str).fillna('T').str.strip()

                required_columns = ['DEFECT_ID', 'DEFECT_TYPE', 'UNIT_INDEX_X', 'UNIT_INDEX_Y']
                if not all(col in df.columns for col in required_columns):
                    st.error(f"File '{file_name}' is missing required columns: {required_columns}. It has been skipped.")
                    continue

                df.dropna(subset=required_columns, inplace=True)
                df['UNIT_INDEX_X'] = df['UNIT_INDEX_X'].astype(int)
                df['UNIT_INDEX_Y'] = df['UNIT_INDEX_Y'].astype(int)
                df['DEFECT_TYPE'] = df['DEFECT_TYPE'].str.strip()

                if layer_num in layer_data:
                    layer_data[layer_num] = pd.concat([layer_data[layer_num], df], ignore_index=True)
                else:
                    layer_data[layer_num] = df

            except ValueError:
                st.error(f"Error in '{uploaded_file.name}': A sheet named 'Defects' was not found. Please ensure the file contains a 'Defects' sheet.")
                continue
            except Exception as e:
                st.error(f"An unexpected error occurred while reading '{uploaded_file.name}': {e}")
                continue
        
        if layer_data:
            st.sidebar.success(f"{len(layer_data)} layer(s) loaded successfully!")

    else:
        st.sidebar.info("No file uploaded. Displaying sample data for 3 layers.")
        total_units_x = 2 * panel_cols
        total_units_y = 2 * panel_rows
        layer_data = {}

        layer_properties = {
            1: {'num_defects': 75, 'defect_types': ['Nick', 'Short', 'Cut']},
            2: {'num_defects': 120, 'defect_types': ['Fine Short', 'Pad Violation', 'Island', 'Short']},
            3: {'num_defects': 50, 'defect_types': ['Missing Feature', 'Cut/Short', 'Nick/Protrusion']}
        }

        for layer_num, props in layer_properties.items():
            number_of_defects = props['num_defects']
            defect_types = props['defect_types']

            defect_data = {
                'DEFECT_ID': range(layer_num * 1000, layer_num * 1000 + number_of_defects),
                'UNIT_INDEX_X': np.random.randint(0, total_units_x, size=number_of_defects),
                'UNIT_INDEX_Y': np.random.randint(0, total_units_y, size=number_of_defects),
                'DEFECT_TYPE': np.random.choice(defect_types, size=number_of_defects),
                'Verification': np.random.choice(['T', 'F', 'TA'], size=number_of_defects, p=[0.7, 0.15, 0.15]),
                'SOURCE_FILE': [f'Sample Data Layer {layer_num}'] * number_of_defects
            }
            sample_df = pd.DataFrame(defect_data)
            layer_data[layer_num] = sample_df

    for layer_num, df in layer_data.items():
        conditions = [
            (df['UNIT_INDEX_X'] < panel_cols) & (df['UNIT_INDEX_Y'] < panel_rows),
            (df['UNIT_INDEX_X'] >= panel_cols) & (df['UNIT_INDEX_Y'] < panel_rows),
            (df['UNIT_INDEX_X'] < panel_cols) & (df['UNIT_INDEX_Y'] >= panel_rows),
            (df['UNIT_INDEX_X'] >= panel_cols) & (df['UNIT_INDEX_Y'] >= panel_rows)
        ]
        choices = ['Q1', 'Q2', 'Q3', 'Q4']
        df['QUADRANT'] = np.select(conditions, choices, default='Other')

        cell_width = QUADRANT_WIDTH / panel_cols
        cell_height = QUADRANT_HEIGHT / panel_rows

        local_index_x = df['UNIT_INDEX_X'] % panel_cols
        local_index_y = df['UNIT_INDEX_Y'] % panel_rows

        plot_x_base = local_index_x * cell_width
        plot_y_base = local_index_y * cell_height

        x_offset = np.where(df['UNIT_INDEX_X'] >= panel_cols, QUADRANT_WIDTH + GAP_SIZE, 0)
        y_offset = np.where(df['UNIT_INDEX_Y'] >= panel_rows, QUADRANT_HEIGHT + GAP_SIZE, 0)

        jitter_x = np.random.rand(len(df)) * cell_width * 0.8 + (cell_width * 0.1)
        jitter_y = np.random.rand(len(df)) * cell_height * 0.8 + (cell_height * 0.1)

        df['plot_x'] = plot_x_base + x_offset + jitter_x
        df['plot_y'] = plot_y_base + y_offset + jitter_y

        layer_data[layer_num] = df
    
    return layer_data

def get_true_defect_coordinates(layer_data: Dict[int, pd.DataFrame]) -> Set[Tuple[int, int]]:
    """
    Aggregates all "True" defects from all layers to find unique defective cell coordinates.
    """
    if not isinstance(layer_data, dict) or not layer_data:
        return set()

    all_layers_df = pd.concat(layer_data.values(), ignore_index=True)

    if all_layers_df.empty or 'Verification' not in all_layers_df.columns:
        return set()

    true_defects_df = all_layers_df[all_layers_df['Verification'] == 'T']

    if true_defects_df.empty:
        return set()

    defect_coords_df = true_defects_df[['UNIT_INDEX_X', 'UNIT_INDEX_Y']].drop_duplicates()

    return set(map(tuple, defect_coords_df.to_numpy()))