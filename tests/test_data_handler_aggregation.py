import pytest
import pandas as pd
from src.data_handler import prepare_multi_layer_data, normalize_coordinates
from src.config import PANEL_WIDTH, PANEL_HEIGHT, GAP_SIZE

def test_normalize_coordinates_simple():
    """Test basic normalization logic."""
    # Mock data: perfect linear correlation
    # Index 0 -> Coord 0
    # Index 10 -> Coord 100
    # So m=10, c=0.
    # We want to check if normalize_coordinates produces correct 'normalized_unit_x'

    df = pd.DataFrame({
        'UNIT_INDEX_X': [0, 10],
        'X_COORDINATES': [0, 100],
        'UNIT_INDEX_Y': [0, 10],
        'Y_COORDINATES': [0, 100],
        # Add required columns for dropna
        'DEFECT_ID': [1, 2],
        'DEFECT_TYPE': ['A', 'B']
    })

    panel_rows, panel_cols = 5, 5 # Quadrant size 5x5
    # Total Global size 10x10 units.

    result = normalize_coordinates(df, panel_rows, panel_cols)

    assert 'normalized_unit_x' in result.columns
    assert 'plot_x_coord' in result.columns

    # Check normalized unit indices
    # Should be exactly equal to UNIT_INDEX because input was perfectly linear with index
    assert result['normalized_unit_x'].iloc[0] == pytest.approx(0.0)
    assert result['normalized_unit_x'].iloc[1] == pytest.approx(10.0)

    # Check Plot Coordinates
    # Cell Width = QUADRANT_WIDTH / 5. (PANEL_WIDTH=600, QUAD=300). Width = 60.
    cell_width = 300 / 5

    # Point 0: Unit 0. plot_x = 0 * 60 = 0.
    assert result['plot_x_coord'].iloc[0] == pytest.approx(0.0)

    # Point 1: Unit 10. This is in Q2 (Right side).
    # Norm Unit 10 >= panel_cols (5).
    # Base = 10 * 60 = 600.
    # Gap = GAP_SIZE (20).
    # Total = 620.
    assert result['plot_x_coord'].iloc[1] == pytest.approx(600.0 + GAP_SIZE)

def test_normalize_coordinates_jitter():
    """Test normalization with jitter (residuals)."""
    # Index 0 -> Coord 10 (Jitter +10)
    # Index 1 -> Coord 110 (Jitter +10)
    # m should be 100. c should be 10.
    # Normalized unit should be 0 and 1.

    df = pd.DataFrame({
        'UNIT_INDEX_X': [0, 1],
        'X_COORDINATES': [10, 110],
        'UNIT_INDEX_Y': [0, 1],
        'Y_COORDINATES': [10, 110],
        'DEFECT_ID': [1, 2],
        'DEFECT_TYPE': ['A', 'B']
    })

    result = normalize_coordinates(df, 5, 5)

    assert result['normalized_unit_x'].iloc[0] == pytest.approx(0.0)
    assert result['normalized_unit_x'].iloc[1] == pytest.approx(1.0)

def test_prepare_multi_layer_data_normalization():
    """Test that prepare_multi_layer_data calls normalization."""
    df = pd.DataFrame({
        'UNIT_INDEX_X': [0], 'X_COORDINATES': [0],
        'UNIT_INDEX_Y': [0], 'Y_COORDINATES': [0],
        'DEFECT_ID': [1], 'Verification': ['True'],
        'SIDE': ['F']
    })

    layer_data = {1: {'F': df}}

    # Pass dimensions
    result = prepare_multi_layer_data(layer_data, 5, 5)

    assert 'plot_x_coord' in result.columns
