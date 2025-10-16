import pytest
import pandas as pd
import plotly.graph_objects as go
from src.plotting import (
    create_grid_shapes,
    create_defect_traces,
    create_pareto_trace,
    create_grouped_pareto_trace
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
    trace = create_pareto_trace(sample_plot_df)
    assert isinstance(trace, go.Bar)

def test_create_grouped_pareto_trace_smoke(sample_plot_df):
    """Smoke test to ensure create_grouped_pareto_trace runs without errors."""
    traces = create_grouped_pareto_trace(sample_plot_df)
    assert isinstance(traces, list)
    assert all(isinstance(t, go.Bar) for t in traces)

def test_create_defect_traces_handles_unknown_defects(sample_plot_df):
    """
    Tests that create_defect_traces correctly handles defect types that are
    not in the predefined style map.
    """
    # 1. Add a new, unknown defect type to the sample data
    new_defect = pd.DataFrame({
        'DEFECT_ID': [105],
        'DEFECT_TYPE': ['New Defect'],
        'UNIT_INDEX_X': [2], 'UNIT_INDEX_Y': [2],
        'QUADRANT': ['Q1'], 'plot_x': [30], 'plot_y': [30],
    })
    df_with_unknown = pd.concat([sample_plot_df, new_defect], ignore_index=True)

    # 2. Generate the traces
    traces = create_defect_traces(df_with_unknown)

    # 3. Assert that all unique defect types have been plotted
    unique_types_in_data = df_with_unknown['DEFECT_TYPE'].unique()
    assert len(traces) == len(unique_types_in_data), "Should create one trace per unique defect type"

    # 4. Find the trace for the new defect and check its color
    new_defect_trace = next((t for t in traces if t.name == 'New Defect'), None)
    assert new_defect_trace is not None, "A trace for 'New Defect' should exist"
    assert new_defect_trace.marker.color == '#808080', "Unknown defects should be assigned the default grey color"
