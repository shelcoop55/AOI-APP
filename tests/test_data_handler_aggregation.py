import pytest
import pandas as pd
import numpy as np
from src.data_handler import normalize_coordinates, GAP_SIZE, PANEL_WIDTH

def test_normalize_coordinates_direct_mapping():
    """Test direct mapping from microns to mm WITHOUT gap insertion (new logic)."""
    # PANEL_WIDTH is 510mm.
    # Logic now assumes coordinates are absolute.

    df = pd.DataFrame({
        'X_COORDINATES': [0, 100000, 255000, 300000], # 0mm, 100mm, 255mm, 300mm
        'Y_COORDINATES': [0, 100000, 257500, 300000], # 0mm, 100mm, 257.5mm, 300mm
        'SIDE': ['F', 'F', 'F', 'F']
    })

    result = normalize_coordinates(df, 10, 10)

    # Point 1: 0mm -> 0
    assert result['plot_x_coord'].iloc[0] == pytest.approx(0.0)

    # Point 2: 100mm -> 100
    assert result['plot_x_coord'].iloc[1] == pytest.approx(100.0)

    # Point 3: 255mm -> 255 (No Gap Added)
    assert result['plot_x_coord'].iloc[2] == pytest.approx(255.0)

    # Point 4: 300mm -> 300
    assert result['plot_x_coord'].iloc[3] == pytest.approx(300.0)

def test_normalize_coordinates_back_no_flip():
    """Test NO coordinate mirroring for Back side (new logic)."""

    df = pd.DataFrame({
        'X_COORDINATES': [10000, 400000], # 10mm, 400mm
        'Y_COORDINATES': [0, 0],
        'SIDE': ['B', 'B']
    })

    result = normalize_coordinates(df, 10, 10)

    # Point 1: 10mm -> Should stay 10mm (No Flip)
    assert result['plot_x_coord'].iloc[0] == pytest.approx(10.0)

    # Point 2: 400mm -> Should stay 400mm (No Flip)
    assert result['plot_x_coord'].iloc[1] == pytest.approx(400.0)

def test_normalize_coordinates_fallback():
    """Test fallback if coordinates are missing."""
    df = pd.DataFrame({
        'plot_x': [1, 2],
        'plot_y': [3, 4]
    })

    result = normalize_coordinates(df, 10, 10)
    assert 'plot_x_coord' in result.columns
    assert result['plot_x_coord'].iloc[0] == 1
    assert result['plot_x_coord'].iloc[1] == 2
