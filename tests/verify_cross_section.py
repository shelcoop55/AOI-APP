import pandas as pd
import numpy as np
from src.data_handler import get_cross_section_matrix

def verify_cross_section():
    # Mock Data
    df = pd.DataFrame({
        'UNIT_INDEX_X': [2, 2, 3, 5],
        'UNIT_INDEX_Y': [3, 4, 3, 5],
        'Verification': ['Cu10', 'Cu10', 'Cu10', 'Cu10']
    })

    layer_data = {
        1: {'F': df}
    }

    panel_rows = 10
    panel_cols = 10

    # Test 1: Full ROI Coverage
    # X Range: 2-3, Y Range: 3-4
    x_range = (2, 3)
    y_range = (3, 4)
    slice_axis = 'Y' # Project onto X

    matrix, layer_labels, axis_labels = get_cross_section_matrix(
        layer_data, slice_axis, x_range, y_range, panel_rows, panel_cols
    )

    print("Test 1 Matrix:\n", matrix)
    print("Test 1 Labels:", axis_labels)

    # Expected: [2, 1]
    assert matrix[0, 0] == 2 # X=2
    assert matrix[0, 1] == 1 # X=3
    assert axis_labels == ['2', '3']

    # Test 2: Restricted Y Range
    # X Range: 2-3, Y Range: 3-3
    y_range_restrict = (3, 3)

    matrix2, _, _ = get_cross_section_matrix(
        layer_data, slice_axis, x_range, y_range_restrict, panel_rows, panel_cols
    )

    print("Test 2 Matrix:\n", matrix2)

    # Expected: [1, 1] (Defect at 2,4 excluded)
    assert matrix2[0, 0] == 1
    assert matrix2[0, 1] == 1

    # Test 3: View by Column (Project onto Y)
    # ROI: X 2-2, Y 3-4
    x_range_restrict = (2, 2)
    y_range = (3, 4)
    slice_axis = 'X'

    matrix3, _, axis_labels3 = get_cross_section_matrix(
        layer_data, slice_axis, x_range_restrict, y_range, panel_rows, panel_cols
    )

    print("Test 3 Matrix:\n", matrix3)
    print("Test 3 Labels:", axis_labels3)

    # Width = 4-3+1 = 2 (Y=3, Y=4)
    # At X=2:
    # Y=3: 1 defect
    # Y=4: 1 defect

    assert matrix3[0, 0] == 1 # Y=3
    assert matrix3[0, 1] == 1 # Y=4
    assert axis_labels3 == ['3', '4']

    print("All verification tests passed!")

if __name__ == "__main__":
    verify_cross_section()
