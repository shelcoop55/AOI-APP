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
    create_defect_map_figure,
    create_pareto_figure,
    create_still_alive_map,
    create_still_alive_figure,
    create_defect_sankey,
    create_density_contour_map,
    create_stress_heatmap
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

def test_create_defect_map_figure_smoke(sample_plot_df):
    """Test full figure creation."""
    fig = create_defect_map_figure(sample_plot_df, 7, 7)
    assert isinstance(fig, go.Figure)
    assert len(fig.data) > 0
    assert len(fig.layout.shapes) > 0

def test_create_pareto_figure_smoke(sample_plot_df):
    """Test Pareto chart creation."""
    fig = create_pareto_figure(sample_plot_df)
    assert isinstance(fig, go.Figure)
    # Check if bar trace exists
    assert fig.data[0].type == 'bar'

def test_create_still_alive_map_logic():
    """Test shape generation for Still Alive map."""
    true_defects = {
        (0, 0): {'first_killer_layer': 1, 'defect_summary': 'L1: 1'},
        (1, 1): {'first_killer_layer': 2, 'defect_summary': 'L2: 1'}
    }
    shapes, traces = create_still_alive_map(2, 2, true_defects)

    assert len(shapes) > 0
    # Should have shapes for cells + grid lines
    # 2x2 = 4 cells. Grid lines extra.

    # Check if red color is used for defective
    red_shapes = [s for s in shapes if s.get('fillcolor') == '#E74C3C'] # DEFECTIVE_CELL_COLOR constant check
    # We might need to import constant if it changes, but hardcode check is fragile.
    # Just check count
    assert len(red_shapes) == 2

def test_create_density_contour_map_smoke(sample_plot_df):
    """Test contour map generation."""
    fig = create_density_contour_map(sample_plot_df, 7, 7)
    assert isinstance(fig, go.Figure)
    # Should contain Histogram2dContour or Contour
    # UPDATED: We use go.Contour now with server-side aggregation
    assert fig.data[0].type in ['histogram2dcontour', 'contour']

def test_create_stress_heatmap_smoke():
    """Test cumulative stress heatmap."""
    # Create dummy data
    grid = np.zeros((14, 14), dtype=int)
    grid[0,0] = 5
    hover = np.empty((14,14), dtype=object)
    hover[:] = ""

    data = StressMapData(grid_counts=grid, hover_text=hover, total_defects=5, max_count=5)

    fig = create_stress_heatmap(data, 7, 7)
    assert isinstance(fig, go.Figure)
    assert fig.data[0].type == 'heatmap'

def test_create_defect_sankey_smoke(sample_plot_df):
    """Test Sankey diagram."""
    fig = create_defect_sankey(sample_plot_df)
    # Might return None if no verification data, but sample has mixed.
    # Logic requires HAS_VERIFICATION_DATA flag true on first row
    # Sample has false on first row.

    # Let's fix sample for Sankey test
    sample_plot_df['HAS_VERIFICATION_DATA'] = True
    fig = create_defect_sankey(sample_plot_df)

    assert isinstance(fig, go.Figure)
    assert fig.data[0].type == 'sankey'
