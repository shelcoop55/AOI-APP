import pytest
import streamlit as st
import pandas as pd
import importlib
from src import data_handler
from src.analysis import calculations
from src.models import PanelData, BuildUpLayer

# Robust Mock
def robust_mock_cache_data(arg1=None, **kwargs):
    if callable(arg1):
        return arg1
    else:
        def decorator(func):
            return func
        return decorator

@pytest.fixture(autouse=True)
def mock_streamlit_cache(monkeypatch):
    """Mocks st.cache_data to bypass caching logic during tests."""
    monkeypatch.setattr(st, "cache_data", robust_mock_cache_data)
    # Reload modules to apply mock
    importlib.reload(data_handler)
    importlib.reload(calculations)

def test_prepare_multi_layer_data(mock_streamlit_cache):
    """Test aggregation of multiple layers."""
    # Setup
    panel = PanelData()
    panel._layers = {}

    # Layer 1
    df1 = pd.DataFrame({
        'LAYER_NUM': [1, 1], 'SIDE': ['F', 'F'], 'Verification': ['CU10', 'N'],
        'UNIT_INDEX_X': [1, 2], 'UNIT_INDEX_Y': [1, 2],
        'DEFECT_TYPE': ['Nick', 'Short'], 'DEFECT_ID': [1, 2],
        'physical_plot_x_raw': [1.0, 2.0], 'physical_plot_x_flipped': [1.0, 2.0], 'plot_y': [1.0, 2.0]
    })
    layer1 = BuildUpLayer(1, 'F', df1, 7, 7)
    panel.add_layer(layer1)

    # Layer 2
    df2 = pd.DataFrame({
        'LAYER_NUM': [2, 2], 'SIDE': ['B', 'B'], 'Verification': ['CU22', 'FALSE'],
        'UNIT_INDEX_X': [3, 4], 'UNIT_INDEX_Y': [3, 4],
        'DEFECT_TYPE': ['Void', 'Open'], 'DEFECT_ID': [3, 4],
        'physical_plot_x_raw': [3.0, 4.0], 'physical_plot_x_flipped': [3.0, 4.0], 'plot_y': [3.0, 4.0]
    })
    panel.add_layer(BuildUpLayer(2, 'B', df2, 7, 7))

    # Execute using module access to ensure we get the reloaded/mocked version
    result = calculations.prepare_multi_layer_data(panel)

    # Verify
    assert len(result) == 2
    assert 'CU10' in result['Verification'].values
    assert 'CU22' in result['Verification'].values
    assert 'N' not in result['Verification'].values

def test_prepare_multi_layer_data_empty(mock_streamlit_cache):
    res1 = calculations.prepare_multi_layer_data(None)
    assert res1.empty

    res2 = calculations.prepare_multi_layer_data(PanelData())
    assert res2.empty
