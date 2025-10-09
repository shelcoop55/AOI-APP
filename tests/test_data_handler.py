import pytest
import pandas as pd
from io import BytesIO
from src.data_handler import load_data, QUADRANT_WIDTH, QUADRANT_HEIGHT
from src.config import GAP_SIZE

# To run tests, use `pytest` in the root directory.

@pytest.fixture
def test_excel_file() -> list[BytesIO]:
    """
    A pytest fixture that creates an in-memory Excel file for testing.
    This simulates a file upload without needing a physical file on disk.
    It uses a standard BytesIO object and adds a .name attribute to mimic
    Streamlit's UploadedFile object.
    The filename is updated to match the new 'BU-XX' format.
    """
    data = {
        'DEFECT_ID': [101, 102, 103, 104],
        'DEFECT_TYPE': ['Nick', 'Short', 'Cut', 'Nick'],
        'UNIT_INDEX_X': [0, 1, 0, 1],
        'UNIT_INDEX_Y': [0, 0, 1, 1],
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
    """A pytest fixture that creates an in-memory Excel file with missing columns."""
    data = {
        'DEFECT_ID': [101, 102],
        'DEFECT_TYPE': ['Nick', 'Short'],
        # 'UNIT_INDEX_X' is missing
        'UNIT_INDEX_Y': [0, 1],
    }
    df = pd.DataFrame(data)

    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Defects')
    output.seek(0)
    output.name = "BU-02-missing-cols.xlsx"
    return [output]

@pytest.fixture
def test_excel_file_with_extra_cols() -> list[BytesIO]:
    """A pytest fixture that creates an in-memory Excel file with an extra column."""
    data = {
        'DEFECT_ID': [101, 102],
        'DEFECT_TYPE': ['Nick', 'Short'],
        'UNIT_INDEX_X': [0, 1],
        'UNIT_INDEX_Y': [0, 1],
        'Verification': ['T', 'F'],
        'Job Name': ['JobA', 'JobB']
    }
    df = pd.DataFrame(data)

    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Defects')
    output.seek(0)
    output.name = "BU-03-extra-cols.xlsx"
    return [output]

@pytest.fixture
def test_excel_file_invalid_name() -> list[BytesIO]:
    """A pytest fixture for a file with an invalid name that doesn't match 'BU-XX'."""
    df = pd.DataFrame({'DEFECT_ID': [101]})
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Defects')
    output.seek(0)
    output.name = "invalid_name.xlsx"
    return [output]


import streamlit as st
import importlib
from src import data_handler
from unittest.mock import MagicMock

def test_load_data_quadrant_assignment(test_excel_file, monkeypatch):
    """
    Tests that load_data correctly reads a file and assigns quadrants.
    Updated to handle the dictionary return type.
    """
    monkeypatch.setattr(st, "cache_data", lambda func: func)
    importlib.reload(data_handler)
    panel_rows, panel_cols = 1, 1

    layer_data = data_handler.load_data(test_excel_file, panel_rows, panel_cols)

    assert isinstance(layer_data, dict), "load_data should return a dictionary"
    assert 1 in layer_data, "Dictionary should contain key for layer 1"

    df = layer_data[1]
    assert not df.empty, "DataFrame for layer 1 should not be empty"
    assert len(df) == 4, "DataFrame should have 4 rows"

    assert df[df['DEFECT_ID'] == 101]['QUADRANT'].iloc[0] == 'Q1'
    assert df[df['DEFECT_ID'] == 102]['QUADRANT'].iloc[0] == 'Q2'
    assert df[df['DEFECT_ID'] == 103]['QUADRANT'].iloc[0] == 'Q3'
    assert df[df['DEFECT_ID'] == 104]['QUADRANT'].iloc[0] == 'Q4'

def test_load_data_coordinate_calculation(test_excel_file, monkeypatch):
    """
    Tests that load_data correctly calculates physical plot coordinates.
    Updated to handle the dictionary return type.
    """
    monkeypatch.setattr(st, "cache_data", lambda func: func)
    importlib.reload(data_handler)
    panel_rows, panel_cols = 1, 1

    layer_data = data_handler.load_data(test_excel_file, panel_rows, panel_cols)
    df = layer_data[1]

    q1_defect = df[df['DEFECT_ID'] == 101]
    q2_defect = df[df['DEFECT_ID'] == 102]
    q3_defect = df[df['DEFECT_ID'] == 103]
    q4_defect = df[df['DEFECT_ID'] == 104]

    assert 'plot_x' in df.columns and pd.api.types.is_float_dtype(df['plot_x'])
    assert 'plot_y' in df.columns and pd.api.types.is_float_dtype(df['plot_y'])

    assert 0 < q1_defect['plot_x'].iloc[0] < QUADRANT_WIDTH
    assert 0 < q1_defect['plot_y'].iloc[0] < QUADRANT_HEIGHT

    assert QUADRANT_WIDTH + GAP_SIZE < q2_defect['plot_x'].iloc[0] < (QUADRANT_WIDTH * 2) + GAP_SIZE
    assert 0 < q2_defect['plot_y'].iloc[0] < QUADRANT_HEIGHT

    assert 0 < q3_defect['plot_x'].iloc[0] < QUADRANT_WIDTH
    assert QUADRANT_HEIGHT + GAP_SIZE < q3_defect['plot_y'].iloc[0] < (QUADRANT_HEIGHT * 2) + GAP_SIZE

    assert QUADRANT_WIDTH + GAP_SIZE < q4_defect['plot_x'].iloc[0] < (QUADRANT_WIDTH * 2) + GAP_SIZE
    assert QUADRANT_HEIGHT + GAP_SIZE < q4_defect['plot_y'].iloc[0] < (QUADRANT_HEIGHT * 2) + GAP_SIZE

def test_load_data_sample_generation(monkeypatch):
    """
    Tests that sample data is generated correctly as a dictionary.
    """
    monkeypatch.setattr(st, "cache_data", lambda func: func)
    monkeypatch.setattr(st.sidebar, "info", lambda *args, **kwargs: None)
    importlib.reload(data_handler)

    layer_data = data_handler.load_data([], panel_rows=7, panel_cols=7)

    assert isinstance(layer_data, dict)
    assert 1 in layer_data
    df = layer_data[1]

    assert not df.empty
    assert len(df) == 150

    expected_cols = ['DEFECT_ID', 'DEFECT_TYPE', 'UNIT_INDEX_X', 'UNIT_INDEX_Y', 'QUADRANT', 'plot_x', 'plot_y']
    assert all(col in df.columns for col in expected_cols)
    assert df['SOURCE_FILE'].iloc[0] == 'Sample Data'

def test_load_data_missing_columns(test_excel_file_missing_cols, monkeypatch):
    """
    Tests that an empty dictionary is returned if the file has missing columns.
    """
    monkeypatch.setattr(st, "cache_data", lambda func: func)
    monkeypatch.setattr(st, "error", lambda *args, **kwargs: None)
    monkeypatch.setattr(st.sidebar, "success", lambda *args, **kwargs: None)
    importlib.reload(data_handler)

    layer_data = data_handler.load_data(test_excel_file_missing_cols, panel_rows=1, panel_cols=1)

    assert isinstance(layer_data, dict)
    assert not layer_data, "Expected an empty dictionary for file with missing columns"

def test_load_data_with_extra_columns(test_excel_file_with_extra_cols, monkeypatch):
    """
    Tests that data loads correctly from a file with extra columns.
    Updated to handle the dictionary return type.
    """
    monkeypatch.setattr(st, "cache_data", lambda func: func)
    monkeypatch.setattr(st.sidebar, "success", lambda *args, **kwargs: None)
    importlib.reload(data_handler)

    layer_data = data_handler.load_data(test_excel_file_with_extra_cols, panel_rows=1, panel_cols=1)

    assert isinstance(layer_data, dict)
    assert 3 in layer_data, "Dictionary should contain key for layer 3"
    df = layer_data[3]

    assert not df.empty, "Dataframe should not be empty"
    assert len(df) == 2, "Should contain 2 rows of data"
    assert "Job Name" in df.columns
    assert df['Job Name'].tolist() == ['JobA', 'JobB']

def test_load_data_invalid_filename(test_excel_file_invalid_name, monkeypatch):
    """
    Tests that a file with an invalid name is ignored and an empty dictionary is returned.
    """
    monkeypatch.setattr(st, "cache_data", lambda func: func)
    mock_error = MagicMock()
    monkeypatch.setattr(st, "error", mock_error)
    importlib.reload(data_handler)

    layer_data = data_handler.load_data(test_excel_file_invalid_name, panel_rows=1, panel_cols=1)

    assert isinstance(layer_data, dict)
    assert not layer_data, "Expected an empty dictionary for invalid filename"
    mock_error.assert_called_once()
