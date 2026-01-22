import pytest
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from unittest.mock import MagicMock
from src.plotting import (
    create_grid_shapes,
    create_defect_traces,
    create_defect_map_figure,
    create_stress_heatmap,
    create_pareto_figure
)
from src.config import PANEL_WIDTH, PANEL_HEIGHT, GAP_SIZE, PlotTheme
from src.models import StressMapData

def test_create_grid_shapes():
    shapes = create_grid_shapes(5, 5)
    assert len(shapes) > 0
    # Outer frame + 4 quadrants + cells
    # Check if a shape is a dict
    assert isinstance(shapes[0], dict)

def test_create_defect_traces():
    df = pd.DataFrame({
        'plot_x': [10, 20],
        'plot_y': [10, 20],
        'DEFECT_TYPE': ['TypeA', 'TypeB'],
        'Verification': ['TypeA', 'TypeB'],
        'UNIT_INDEX_X': [1, 2],
        'UNIT_INDEX_Y': [1, 2],
        'DEFECT_ID': [1, 2],
        'HAS_VERIFICATION_DATA': [True, True]
    })
    traces = create_defect_traces(df)
    assert len(traces) == 2
    assert isinstance(traces[0], go.Scattergl)

def test_create_stress_heatmap():
    # Create dummy stress data
    rows = 10
    cols = 10
    grid = np.zeros((rows, cols), dtype=int)
    grid[1, 1] = 5
    hover = np.empty((rows, cols), dtype=object)
    hover[:] = ""
    hover[1, 1] = "5 defects"

    data = StressMapData(grid, hover, 5, 5)

    fig = create_stress_heatmap(data, 5, 5)
    assert isinstance(fig, go.Figure)
    assert len(fig.data) > 0
    assert fig.data[0].type == 'heatmap'
