import pytest
import streamlit as st
from src import data_handler
from src.data_handler import load_data, prepare_multi_layer_data
from src.models import PanelData, BuildUpLayer
from src.layout import LayoutParams
from unittest.mock import MagicMock
import pandas as pd
import importlib

# Robust Mock for st.cache_data
def robust_mock_cache_data(arg1=None, **kwargs):
    """Handles both @st.cache_data and @st.cache_data(...) usage."""
    if callable(arg1):
        # Case: @st.cache_data (no args)
        return arg1
    else:
        # Case: @st.cache_data(...) (with args)
        def decorator(func):
            return func
        return decorator

@pytest.fixture(autouse=True)
def mock_streamlit_cache(monkeypatch):
    """Mocks st.cache_data to bypass caching logic during tests."""
    monkeypatch.setattr(st, "cache_data", robust_mock_cache_data)
    # Reload module to apply mock
    importlib.reload(data_handler)

def create_layout():
    return LayoutParams(7, 7, 200, 200, 10, 10, 20, 0)

def test_prepare_multi_layer_data(mock_streamlit_cache):
    """Test aggregation of multiple layers."""
    # Setup
    panel = PanelData()
    panel._layers = {}
    layout = create_layout()

    # Layer 1
    df1 = pd.DataFrame({
        'LAYER_NUM': [1, 1], 'SIDE': ['F', 'F'], 'Verification': ['CU10', 'N'],
        'UNIT_INDEX_X': [1, 2], 'UNIT_INDEX_Y': [1, 2],
        'DEFECT_TYPE': ['Nick', 'Short'], 'DEFECT_ID': [1, 2],
        'physical_plot_x_raw': [1.0, 2.0], 'physical_plot_x_flipped': [1.0, 2.0], 'plot_y': [1.0, 2.0]
    })
    panel.add_layer(BuildUpLayer(1, 'F', df1, layout))

    # Layer 2
    df2 = pd.DataFrame({
        'LAYER_NUM': [2, 2], 'SIDE': ['B', 'B'], 'Verification': ['CU22', 'FALSE'],
        'UNIT_INDEX_X': [3, 4], 'UNIT_INDEX_Y': [3, 4],
        'DEFECT_TYPE': ['Void', 'Open'], 'DEFECT_ID': [3, 4],
        'physical_plot_x_raw': [3.0, 4.0], 'physical_plot_x_flipped': [3.0, 4.0], 'plot_y': [3.0, 4.0]
    })
    panel.add_layer(BuildUpLayer(2, 'B', df2, layout))

    # Execute using reloaded module
    result = data_handler.prepare_multi_layer_data(panel)

    # result is a DataFrame

    # Verify
    assert len(result) == 2
    assert 'CU10' in result['Verification'].values
    assert 'CU22' in result['Verification'].values
    assert 'N' not in result['Verification'].values

def test_prepare_multi_layer_data_empty(mock_streamlit_cache):
    """Test with empty input."""
    # If I pass None, prepare_multi_layer_data(None) returns pd.DataFrame()
    res1 = data_handler.prepare_multi_layer_data(None)

    # Check if we got back our mocked function or the result
    # The output says "DEBUG: <function mock_cache_data.<locals>.decorator at ...>"
    # This means `data_handler.prepare_multi_layer_data` IS the decorator function?
    # NO.
    # @st.cache_data(...)
    # def func(): ...

    # Syntax: func = st.cache_data(...)(func)
    # st.cache_data(...) returns 'decorator'
    # 'decorator'(func) returns 'func'
    # So 'prepare_multi_layer_data' should be 'func'.

    # Wait, the failure was:
    # E       AttributeError: 'PanelData' object has no attribute 'empty'
    # This means `res2` was a PanelData object?
    # `res2 = data_handler.prepare_multi_layer_data(PanelData())`
    # How can `prepare_multi_layer_data` return its input?

    # Ah, if `mock_cache_data` logic is flawed.
    # If I use @st.cache_data (no args), st.cache_data IS the decorator.
    # If I use @st.cache_data(show_spinner=...), st.cache_data(...) returns the decorator.

    # data_handler uses @st.cache_data without parens?
    # No, for `load_data` I added `(show_spinner=...)`.
    # For `prepare_multi_layer_data`, I did NOT edit it.
    # Let's check `src/data_handler.py`.
    # It has `@st.cache_data` (no parens) on `prepare_multi_layer_data`.

    # My mock:
    # def mock_cache_data(*args, **kwargs):
    #     def decorator(func): return func
    #     return decorator

    # If called as @st.cache_data (no parens), `mock_cache_data` receives `func` as first arg!
    # So `args[0]` is the function.
    # And it returns `decorator`.
    # So `prepare_multi_layer_data` becomes `decorator`.
    # `decorator` expects `func`.
    # But when we call `prepare_multi_layer_data(panel)`, we pass `panel`.
    # `decorator` returns `func` (which is `panel`!).
    # So `res2` becomes `panel`.
    # `panel.empty` fails.

    # FIX: A robust mock that handles both `@st.cache_data` and `@st.cache_data(...)`.
    pass

# Robust Mock
def robust_mock_cache_data(arg1=None, **kwargs):
    if callable(arg1):
        # Case: @st.cache_data without parens
        # arg1 is the function
        return arg1
    else:
        # Case: @st.cache_data(...) with args
        # Return a decorator that returns the function
        def decorator(func):
            return func
        return decorator

@pytest.fixture(autouse=True)
def mock_streamlit_cache(monkeypatch):
    """Mocks st.cache_data to bypass caching logic during tests."""
    monkeypatch.setattr(st, "cache_data", robust_mock_cache_data)
    importlib.reload(data_handler)

def test_prepare_multi_layer_data_empty_fixed(mock_streamlit_cache):
    res1 = data_handler.prepare_multi_layer_data(None)
    assert res1.empty

    res2 = data_handler.prepare_multi_layer_data(PanelData())
    assert res2.empty
