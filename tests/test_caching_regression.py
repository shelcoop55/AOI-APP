import pytest
import streamlit as st
import importlib
from src.models import PanelData
from src.analysis import calculations

def test_get_true_defect_coordinates_caching_behavior():
    """
    Regression test for UnhashableParamError.
    Ensures that get_true_defect_coordinates handles PanelData without
    Streamlit trying to hash it (due to the leading underscore fix).
    """
    # Force reload of calculations to ensure we are using the real st.cache_data
    # and not a mock from another test file (since pytest shares the process).
    importlib.reload(calculations)

    # Create a PanelData instance (which is unhashable)
    panel_data = PanelData()

    # Call the function.
    # If the argument is not prefixed with '_', Streamlit's cache_data
    # will attempt to hash 'panel_data' and raise UnhashableParamError
    # (or TypeError: cannot pickle 'function' object depending on recursion).
    try:
        # We don't need actual data, just the call to trigger the cache logic check.
        result = calculations.get_true_defect_coordinates(panel_data)
        assert isinstance(result, dict)
    except Exception as e:
        pytest.fail(f"get_true_defect_coordinates raised an exception with PanelData: {e}")
