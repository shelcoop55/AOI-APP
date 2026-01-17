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

def test_load_data_multilayer(mock_streamlit):
    """Test loading multiple valid files."""
    # Create mock files
    file1 = MagicMock()
    file1.name = "BU-01F-Test.xlsx"
    file2 = MagicMock()
    file2.name = "BU-02B-Test.xlsx"

    # Mock pd.read_excel to return different DFs based on file
    df1 = pd.DataFrame({
        'DEFECT_ID': [1], 'DEFECT_TYPE': ['TypeA'],
        'UNIT_INDEX_X': [1], 'UNIT_INDEX_Y': [1], 'Verification': ['T']
    })
    df2 = pd.DataFrame({
        'DEFECT_ID': [2], 'DEFECT_TYPE': ['TypeB'],
        'UNIT_INDEX_X': [2], 'UNIT_INDEX_Y': [2], 'Verification': ['T']
    })

    # We need to mock read_excel. Since we reload module, we must patch pd inside data_handler or globally
    with pytest.MonkeyPatch.context() as m:
        m.setattr(pd, "read_excel", MagicMock(side_effect=[df1, df2]))

        panel_data = data_handler.load_data([file1, file2], 7, 7)

        assert isinstance(panel_data, PanelData)
        assert len(panel_data._layers) == 2
        assert 1 in panel_data._layers
        assert 2 in panel_data._layers
        assert 'F' in panel_data._layers[1]
        assert 'B' in panel_data._layers[2]

def test_load_data_sample_generation(mock_streamlit):
    """Test sample data generation when no files provided."""
    panel_data = data_handler.load_data([], 7, 7)

    assert isinstance(panel_data, PanelData)
    # Should generate 5 layers
    assert len(panel_data._layers) == 5
    # Check random layer
    assert not panel_data._layers[1]['F'].data.empty

def test_load_data_invalid_filename(mock_streamlit):
    """Test handling of invalid filenames."""
    file1 = MagicMock()
    file1.name = "InvalidName.xlsx"

    # load_data handles this by skipping and warning
    panel_data = data_handler.load_data([file1], 7, 7)

    assert isinstance(panel_data, PanelData)
    assert len(panel_data._layers) == 0 # No layers loaded
    st.warning.assert_called()

def test_load_data_missing_columns(mock_streamlit):
    """Test handling of missing columns."""
    file1 = MagicMock()
    file1.name = "BU-01F.xlsx"

    # DF missing DEFECT_ID
    df_bad = pd.DataFrame({
        'DEFECT_TYPE': ['TypeA'],
        'UNIT_INDEX_X': [1], 'UNIT_INDEX_Y': [1]
    })

    with pytest.MonkeyPatch.context() as m:
        m.setattr(pd, "read_excel", MagicMock(return_value=df_bad))

        panel_data = data_handler.load_data([file1], 7, 7)

        # Should skip file
        assert len(panel_data._layers) == 0
        st.error.assert_called()
