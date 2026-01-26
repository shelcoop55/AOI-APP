"""
Tests for the plotting module.
Checks if Plotly figure generation logic runs without errors and produces expected structures.
"""
import pytest
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from src.plotting import (
    create_grid_shapes,
    create_defect_traces,
    create_pareto_trace,
    create_grouped_pareto_trace,
    get_color_map_for_defects
)
from src.data_handler import StressMapData
from src.enums import Quadrant
from src.config import PANEL_WIDTH, PANEL_HEIGHT, GAP_SIZE

@pytest.fixture
def sample_plot_df():
    """Creates a sample DataFrame formatted for plotting (with plot_x/y)."""
    return pd.DataFrame({
        'DEFECT_ID': [101, 102, 103, 104],
        'DEFECT_TYPE': ['Nick', 'Short', 'Open', 'Nick'],
        'Verification': ['Under Verification', 'CU10', 'N', 'Under Verification'],
        'HAS_VERIFICATION_DATA': [False, True, True, False],
        'UNIT_INDEX_X': [1, 2, 3, 4],
        'UNIT_INDEX_Y': [1, 2, 3, 4],
        'QUADRANT': ['Q1', 'Q2', 'Q3', 'Q4'],
        'plot_x': [10, 100, 10, 20],
        'plot_y': [10, 10, 20, 20]
    })

def test_create_grid_shapes():
    """Test grid shape generation."""
    shapes = create_grid_shapes(7, 7, Quadrant.ALL.value)
    assert isinstance(shapes, list)
    assert len(shapes) > 0
    # Check if shapes are dicts (Plotly shape spec)
    assert isinstance(shapes[0], dict)
    assert 'type' in shapes[0]

def test_create_defect_traces_smoke(sample_plot_df):
    """Smoke test to ensure create_defect_traces runs without errors."""
    traces = create_defect_traces(sample_plot_df)
    assert isinstance(traces, list)
    # UPDATED: We now use Scattergl or Scatter
    assert all(isinstance(t, (go.Scatter, go.Scattergl)) for t in traces)

def test_create_pareto_trace_smoke(sample_plot_df):
    """Smoke test to ensure create_pareto_trace runs without errors."""
    color_map = get_color_map_for_defects(sample_plot_df['DEFECT_TYPE'].unique())
    trace = create_pareto_trace(sample_plot_df, color_map)
    assert isinstance(trace, go.Bar)

def test_create_grouped_pareto_trace_smoke(sample_plot_df):
    """Smoke test to ensure create_grouped_pareto_trace runs without errors."""
    color_map = get_color_map_for_defects(sample_plot_df['DEFECT_TYPE'].unique())
    traces = create_grouped_pareto_trace(sample_plot_df, color_map)
    assert isinstance(traces, list)
    assert all(isinstance(t, go.Bar) for t in traces)

def test_dynamic_color_assignment(sample_plot_df):
    """
    Tests that different defect types are assigned unique colors dynamically.
    """
    # 1. Generate traces from the sample data
    traces = create_defect_traces(sample_plot_df)

    # 2. Assert that the correct number of traces were created
    unique_types_in_data = sample_plot_df['DEFECT_TYPE'].unique()
    assert len(traces) == len(unique_types_in_data), "Should create one trace per unique defect type"

    # 3. Extract the colors assigned to each trace
    assigned_colors = [t.marker.color for t in traces]

    # 4. Assert that all assigned colors are unique
    assert len(assigned_colors) == len(set(assigned_colors)), "Each unique defect type should have a unique color"
