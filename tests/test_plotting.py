import pytest
import pandas as pd
import plotly.graph_objects as go
from src.plotting import (
    create_grid_shapes,
    create_defect_traces,
    create_pareto_trace,
    create_grouped_pareto_trace,
    create_still_alive_map
)
from src.config import ALIVE_CELL_COLOR, DEFECTIVE_CELL_COLOR

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

def test_create_still_alive_map():
    """
    Tests that the still alive map correctly colors cells based on defect coordinates.
    """
    # For a 1x1 grid per quadrant, the total grid is 2x2.
    panel_rows, panel_cols = 1, 1
    total_cells = (panel_rows * 2) * (panel_cols * 2)

    # Define two cells as having "True" defects.
    true_defect_coords = {(0, 0), (1, 1)}

    # Generate the shapes for the map
    shapes = create_still_alive_map(panel_rows, panel_cols, true_defect_coords)

    # The function should return a list of shapes (dictionaries)
    assert isinstance(shapes, list)

    # Extract just the colored cell rectangles, which are now drawn with a line width of 0.
    colored_cells = [s for s in shapes if s.get('type') == 'rect' and s.get('line', {}).get('width') == 0]

    # There should be one rectangle for each cell in the grid
    assert len(colored_cells) == total_cells, "Should be one shape per cell"

    # Count how many cells are colored defective vs. alive
    defective_count = sum(1 for s in colored_cells if s['fillcolor'] == DEFECTIVE_CELL_COLOR)
    alive_count = sum(1 for s in colored_cells if s['fillcolor'] == ALIVE_CELL_COLOR)

    assert defective_count == len(true_defect_coords), "Number of defective cells is incorrect"
    assert alive_count == total_cells - len(true_defect_coords), "Number of alive cells is incorrect"
