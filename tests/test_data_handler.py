import pytest
import pandas as pd
from io import BytesIO
from src.data_handler import load_data, get_defective_coordinates_by_status, QUADRANT_WIDTH, QUADRANT_HEIGHT
from src.config import GAP_SIZE
import streamlit as st
import importlib
from src import data_handler
from unittest.mock import MagicMock

@pytest.fixture
def test_excel_file() -> list[BytesIO]:
    """Creates an in-memory Excel file with a valid 'BU-XX' name."""
    data = {
        'DEFECT_ID': [101, 102, 103, 104], 'DEFECT_TYPE': ['Nick', 'Short', 'Cut', 'Nick'],
        'UNIT_INDEX_X': [0, 1, 0, 1], 'UNIT_INDEX_Y': [0, 0, 1, 1],
        'Verification': ['T', 'F', 'T', 'TA'],
    }
    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Defects')
    output.seek(0)
    output.name = "BU-01-test-data.xlsx"
    return [output]

@pytest.fixture
def test_excel_file_missing_cols() -> list[BytesIO]:
    """Creates an in-memory Excel file with missing columns and a valid 'BU-XX' name."""
    data = {'DEFECT_ID': [101], 'DEFECT_TYPE': ['Nick']}
    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Defects')
    output.seek(0)
    output.name = "BU-02-missing-cols.xlsx"
    return [output]

@pytest.fixture
def test_excel_file_invalid_name() -> list[BytesIO]:
    """Creates an in-memory Excel file with an invalid name."""
    df = pd.DataFrame({'DEFECT_ID': [101]})
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Defects')
    output.seek(0)
    output.name = "invalid_name.xlsx"
    return [output]

def test_load_data_multilayer(test_excel_file, monkeypatch):
    """Tests that load_data correctly processes a valid multi-layer file."""
    monkeypatch.setattr(st, "cache_data", lambda func: func)
    monkeypatch.setattr(st.sidebar, "success", lambda *args, **kwargs: None)
    importlib.reload(data_handler)

    layer_data = data_handler.load_data(test_excel_file, 1, 1)

    assert isinstance(layer_data, dict)
    assert 1 in layer_data
    df = layer_data[1]
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 4
    assert 'QUADRANT' in df.columns

def test_load_data_sample_generation(monkeypatch):
    """Tests that sample data is generated correctly for multiple layers."""
    monkeypatch.setattr(st, "cache_data", lambda func: func)
    monkeypatch.setattr(st.sidebar, "info", lambda *args, **kwargs: None)
    importlib.reload(data_handler)

    layer_data = data_handler.load_data([], panel_rows=7, panel_cols=7)

    assert isinstance(layer_data, dict)
    assert set(layer_data.keys()) == {1, 2, 3}
    assert len(layer_data[1]) == 75
    assert len(layer_data[2]) == 120
    assert len(layer_data[3]) == 50
    assert 'plot_x' in layer_data[1].columns

def test_load_data_invalid_filename(test_excel_file_invalid_name, monkeypatch):
    """Tests that a file with an invalid name is ignored."""
    monkeypatch.setattr(st, "cache_data", lambda func: func)
    mock_error = MagicMock()
    monkeypatch.setattr(st, "error", mock_error)
    importlib.reload(data_handler)

    layer_data = data_handler.load_data(test_excel_file_invalid_name, 1, 1)
    assert not layer_data
    mock_error.assert_called_once()

def test_load_data_missing_columns(test_excel_file_missing_cols, monkeypatch):
    """Tests that a file with missing required columns is skipped."""
    monkeypatch.setattr(st, "cache_data", lambda func: func)
    mock_error = MagicMock()
    monkeypatch.setattr(st, "error", mock_error)
    importlib.reload(data_handler)

    layer_data = data_handler.load_data(test_excel_file_missing_cols, 1, 1)
    assert not layer_data
    mock_error.assert_called_once()

def test_get_defective_coordinates_by_status():
    """Tests the aggregation of defect coordinates based on specified verification statuses."""
    layer_1 = pd.DataFrame({'UNIT_INDEX_X': [1, 2, 3], 'UNIT_INDEX_Y': [1, 2, 3], 'Verification': ['T', 'F', 'T']})
    layer_2 = pd.DataFrame({'UNIT_INDEX_X': [1, 4, 5], 'UNIT_INDEX_Y': [1, 4, 5], 'Verification': ['T', 'T', 'TA']})
    layer_3 = pd.DataFrame({'UNIT_INDEX_X': [2, 6, 7], 'UNIT_INDEX_Y': [2, 6, 7], 'Verification': ['F', 'T', 'TA']})
    layer_data = {1: layer_1, 2: layer_2, 3: layer_3}

    # Test for 'T' status
    t_coords = get_defective_coordinates_by_status(layer_data, ['T'])
    expected_t_coords = {(1, 1), (3, 3), (4, 4), (6, 6)}
    assert t_coords == expected_t_coords

    # Test for 'F' status
    f_coords = get_defective_coordinates_by_status(layer_data, ['F'])
    expected_f_coords = {(2, 2)}
    assert f_coords == expected_f_coords

    # Test for 'TA' status
    ta_coords = get_defective_coordinates_by_status(layer_data, ['TA'])
    expected_ta_coords = {(5, 5), (7, 7)}
    assert ta_coords == expected_ta_coords

    # Test for multiple statuses ('T' and 'TA')
    t_ta_coords = get_defective_coordinates_by_status(layer_data, ['T', 'TA'])
    expected_t_ta_coords = {(1, 1), (3, 3), (4, 4), (5, 5), (6, 6), (7, 7)}
    assert t_ta_coords == expected_t_ta_coords

    # Test for all statuses
    all_coords = get_defective_coordinates_by_status(layer_data, ['T', 'F', 'TA'])
    expected_all_coords = {(1, 1), (2, 2), (3, 3), (4, 4), (5, 5), (6, 6), (7, 7)}
    assert all_coords == expected_all_coords

    # Test for empty status list
    empty_coords = get_defective_coordinates_by_status(layer_data, [])
    assert empty_coords == set()

    # Test for non-existent status
    non_existent_coords = get_defective_coordinates_by_status(layer_data, ['X'])
    assert non_existent_coords == set()