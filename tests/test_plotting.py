import pytest
import pandas as pd
import plotly.graph_objects as go
from src.plotting import (
    create_grid_shapes,
    create_defect_traces,
    create_pareto_trace,
    create_grouped_pareto_trace,
    get_color_map_for_defects
)

@pytest.fixture
def sample_plot_df() -> pd.DataFrame:
    """A fixture to create a sample DataFrame for plotting tests."""
    data = {
        'DEFECT_ID': [101, 102, 103, 104],
        'DEFECT_TYPE': ['Nick', 'Short', 'Cut', 'Nick'],
        'UNIT_INDEX_X': [0, 1, 0, 1],
        'UNIT_INDEX_Y': [0, 0, 1, 1],
        'QUADRANT': ['Q1', 'Q2', 'Q3', 'Q4'],
        'plot_x': [10, 20, 10, 20],
        'plot_y': [10, 10, 20, 20],
    }
    return pd.DataFrame(data)

def test_create_grid_shapes_smoke():
    """Smoke test to ensure create_grid_shapes runs without errors."""
    shapes = create_grid_shapes(panel_rows=7, panel_cols=7, quadrant='All')
    assert isinstance(shapes, list)
    assert all(isinstance(s, dict) for s in shapes)

def test_create_defect_traces_smoke(sample_plot_df):
    """Smoke test to ensure create_defect_traces runs without errors."""
    traces = create_defect_traces(sample_plot_df)
    assert isinstance(traces, list)
    assert all(isinstance(t, go.Scatter) for t in traces)

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
