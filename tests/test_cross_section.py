
import pytest
import pandas as pd
import numpy as np
from src.data_handler import get_cross_section_matrix, PanelData, BuildUpLayer
from src.layout import LayoutParams

def create_mock_panel_data():
    panel_rows = 5
    panel_cols = 5
    layout = LayoutParams(panel_cols, panel_rows, 100, 100, 10, 10, 20, 0)
    panel_data = PanelData()

    # Layer 1
    # Defect at (2, 0) - Should show up in Y-slice 0, at X=2
    # Defect at (5, 5) - Should show up in X-slice 5, at Y=5
    df1 = pd.DataFrame({
        'DEFECT_ID': [1, 2],
        'UNIT_INDEX_X': [2, 5],
        'UNIT_INDEX_Y': [0, 5],
        'DEFECT_TYPE': ['TypeA', 'TypeB'],
        'Verification': ['TypeA', 'TypeB'], # True defects
        'SIDE': ['F', 'F']
    })
    layer1 = BuildUpLayer(1, 'F', df1, layout)
    panel_data.add_layer(layer1)

    # Layer 2
    # Defect at (2, 0) - Stack on top of Layer 1
    df2 = pd.DataFrame({
        'DEFECT_ID': [3],
        'UNIT_INDEX_X': [2],
        'UNIT_INDEX_Y': [0],
        'DEFECT_TYPE': ['TypeA'],
        'Verification': ['TypeA'],
        'SIDE': ['F']
    })
    layer2 = BuildUpLayer(2, 'F', df2, layout)
    panel_data.add_layer(layer2)

    return panel_data, panel_rows, panel_cols

def test_cross_section_y_slice():
    panel_data, rows, cols = create_mock_panel_data()

    # Test 1: Slice Y=0
    # Expected:
    # Layer 1: Defect at X=2 -> Matrix[0, 2] == 1
    # Layer 2: Defect at X=2 -> Matrix[1, 2] == 1
    matrix_y, labels_y, axis_y = get_cross_section_matrix(panel_data, 'Y', 0, rows, cols)

    assert matrix_y.shape == (2, cols * 2)
    assert matrix_y[0, 2] == 1
    assert matrix_y[1, 2] == 1

def test_cross_section_x_slice():
    panel_data, rows, cols = create_mock_panel_data()

    # Test 2: Slice X=5
    # Expected:
    # Layer 1: Defect at Y=5 -> Matrix[0, 5] == 1
    matrix_x, labels_x, axis_x = get_cross_section_matrix(panel_data, 'X', 5, rows, cols)

    assert matrix_x.shape == (2, rows * 2)
    assert matrix_x[0, 5] == 1
