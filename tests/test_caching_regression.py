import pytest
import streamlit as st
import importlib
from src.models import PanelData
from src.analysis import calculations
from src.analysis.calculations import FilterContext

def test_get_true_defect_coordinates_caching_behavior():
    """
    Regression test for UnhashableParamError.
    Ensures that get_true_defect_coordinates handles PanelData without
    Streamlit trying to hash it (due to the leading underscore fix).
    """
    # Force reload of calculations to ensure we are using the real st.cache_data
    # and not a mock from another test file.
    importlib.reload(calculations)

    panel_data = PanelData()

    try:
        # Case 1: Only PanelData (Original crash)
        result = calculations.get_true_defect_coordinates(panel_data)
        assert isinstance(result, dict)

        # Case 2: PanelData + FilterContext (Potential secondary crash)
        # Verify that passing a FilterContext (which contains lists) works fine
        # and doesn't trigger hashing errors now that the first argument is fixed.
        context = FilterContext(
            selected_layers=[1, 2],
            selected_sides=['F'],
            excluded_defect_types=['TypeA']
        )
        result_with_context = calculations.get_true_defect_coordinates(panel_data, context)
        assert isinstance(result_with_context, dict)

    except Exception as e:
        pytest.fail(f"get_true_defect_coordinates raised an exception: {e}")
