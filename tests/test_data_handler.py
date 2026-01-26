import pytest
import pandas as pd
from unittest.mock import MagicMock
import streamlit as st
import importlib
from src import data_handler
from src.data_handler import load_data
from src.models import PanelData

# Mock Cache Decorator properly to handle arguments
def mock_cache_data(*args, **kwargs):
    def decorator(func):
        return func
    return decorator

@pytest.fixture(autouse=True)
def mock_streamlit(monkeypatch):
    """Mocks streamlit functions."""
    monkeypatch.setattr(st, "warning", MagicMock())
    monkeypatch.setattr(st, "error", MagicMock())
    monkeypatch.setattr(st, "sidebar", MagicMock())
    monkeypatch.setattr(st, "cache_data", mock_cache_data)
    # Reload module to apply mock
    importlib.reload(data_handler)

    df = data_handler.load_data(test_excel_file_missing_cols, panel_rows=1, panel_cols=1)

    assert isinstance(df, pd.DataFrame)
    assert df.empty

def test_load_data_with_extra_columns(test_excel_file_with_extra_cols, monkeypatch):
    """
    Tests that data loads correctly from a file with extra, non-required columns.
    This verifies the fix for the user-reported bug.
    """
    monkeypatch.setattr(st, "cache_data", lambda func: func)
    monkeypatch.setattr(st.sidebar, "success", lambda *args, **kwargs: None)
    importlib.reload(data_handler)

    df = data_handler.load_data(test_excel_file_with_extra_cols, panel_rows=1, panel_cols=1)

    assert isinstance(df, pd.DataFrame)
    assert not df.empty, "Dataframe should not be empty"
    assert len(df) == 2, "Should contain 2 rows of data"

    # Crucially, assert that the extra column is preserved
    assert "Job Name" in df.columns
    assert df['Job Name'].tolist() == ['JobA', 'JobB']

# ==============================================================================
# --- Test Suite for calculate_yield_metrics ---
# ==============================================================================
from src.data_handler import calculate_yield_metrics

class TestYieldMetrics:
    """
    Test suite for the calculate_yield_metrics function.
    This suite validates the core business logic for identifying defective cells
    and calculating the overall panel yield.
    """

    def test_empty_dataframe(self):
        """
        GIVEN: An empty DataFrame.
        WHEN: calculate_yield_metrics is called.
        THEN: It should return 0 defective cells and a perfect yield of 1.0.
        """
        df = pd.DataFrame(columns=['UNIT_INDEX_X', 'UNIT_INDEX_Y', 'Verification'])
        defective_cells, yield_estimate = calculate_yield_metrics(df, 100)
        assert defective_cells == 0
        assert yield_estimate == 1.0

    def test_no_true_defects(self):
        """
        GIVEN: A DataFrame with defects, but none are marked as 'T'.
        WHEN: calculate_yield_metrics is called.
        THEN: It should return 0 defective cells and a perfect yield of 1.0.
        """
        data = {'UNIT_INDEX_X': [1, 2], 'UNIT_INDEX_Y': [1, 2], 'Verification': ['F', 'TA']}
        df = pd.DataFrame(data)
        defective_cells, yield_estimate = calculate_yield_metrics(df, 100)
        assert defective_cells == 0
        assert yield_estimate == 1.0

    def test_one_defective_cell(self):
        """
        GIVEN: A DataFrame with one defect marked as 'T'.
        WHEN: calculate_yield_metrics is called.
        THEN: It should return 1 defective cell and the correct yield.
        """
        data = {'UNIT_INDEX_X': [1], 'UNIT_INDEX_Y': [1], 'Verification': ['T']}
        df = pd.DataFrame(data)
        total_cells = 100
        defective_cells, yield_estimate = calculate_yield_metrics(df, total_cells)
        assert defective_cells == 1
        assert yield_estimate == (total_cells - 1) / total_cells

    def test_multiple_defects_in_one_cell(self):
        """
        GIVEN: A DataFrame with multiple 'T' defects in the same cell.
        WHEN: calculate_yield_metrics is called.
        THEN: It should count them as only one defective cell.
        """
        data = {
            'UNIT_INDEX_X': [1, 1, 2],
            'UNIT_INDEX_Y': [1, 1, 2],
            'Verification': ['T', 'T', 'F']
        }
        df = pd.DataFrame(data)
        total_cells = 100
        defective_cells, yield_estimate = calculate_yield_metrics(df, total_cells)
        assert defective_cells == 1
        assert yield_estimate == (total_cells - 1) / total_cells

    def test_multiple_defective_cells(self):
        """
        GIVEN: A DataFrame with 'T' defects in multiple different cells.
        WHEN: calculate_yield_metrics is called.
        THEN: It should correctly count all unique defective cells.
        """
        data = {
            'UNIT_INDEX_X': [1, 2, 3, 1],
            'UNIT_INDEX_Y': [1, 2, 3, 1],
            'Verification': ['T', 'T', 'T', 'F']
        }
        df = pd.DataFrame(data)
        total_cells = 100
        defective_cells, yield_estimate = calculate_yield_metrics(df, total_cells)
        assert defective_cells == 3
        assert yield_estimate == (total_cells - 3) / total_cells

    def test_zero_total_cells(self):
        """
        GIVEN: A valid DataFrame but total_cells is 0.
        WHEN: calculate_yield_metrics is called.
        THEN: It should return 0 defective cells and a yield of 1.0 to avoid division by zero.
        """
        data = {'UNIT_INDEX_X': [1], 'UNIT_INDEX_Y': [1], 'Verification': ['T']}
        df = pd.DataFrame(data)
        defective_cells, yield_estimate = calculate_yield_metrics(df, 0)
        assert defective_cells == 0
        assert yield_estimate == 1.0
