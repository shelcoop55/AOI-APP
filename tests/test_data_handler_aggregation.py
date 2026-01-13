import pytest
import pandas as pd
import numpy as np
from src.data_handler import prepare_multi_layer_data, normalize_coordinates
from src.config import PANEL_WIDTH, PANEL_HEIGHT, GAP_SIZE

def test_normalize_coordinates_direct_mapping():
    """Test direct mapping from microns to mm with gap insertion."""
    # PANEL_WIDTH is 510mm. Center is 255mm.
    # GAP_SIZE is 20mm.

    df = pd.DataFrame({
        'X_COORDINATES': [0, 100000, 255000, 300000], # 0mm, 100mm, 255mm, 300mm
        'Y_COORDINATES': [0, 100000, 257500, 300000], # 0mm, 100mm, 257.5mm, 300mm
        'SIDE': ['F', 'F', 'F', 'F']
    })

    # Dimensions (rows/cols) don't affect normalization now, only gap logic which uses constants
    result = normalize_coordinates(df, 10, 10)

    # Point 1: 0mm -> < 255 -> 0
    assert result['plot_x_coord'].iloc[0] == pytest.approx(0.0)

    # Point 2: 100mm -> < 255 -> 100
    assert result['plot_x_coord'].iloc[1] == pytest.approx(100.0)

    # Point 3: 255mm -> >= 255 -> 255 + 20 = 275
    assert result['plot_x_coord'].iloc[2] == pytest.approx(255.0 + GAP_SIZE)

    # Point 4: 300mm -> >= 255 -> 300 + 20 = 320
    assert result['plot_x_coord'].iloc[3] == pytest.approx(300.0 + GAP_SIZE)

    # Check Y Axis (PANEL_HEIGHT=515, Center=257.5)
    # Point 1: 0mm
    assert result['plot_y_coord'].iloc[0] == pytest.approx(0.0)
    # Point 3: 257.5mm -> >= 257.5 -> 257.5 + 20
    assert result['plot_y_coord'].iloc[2] == pytest.approx(257.5 + GAP_SIZE)

def test_normalize_coordinates_back_flip():
    """Test coordinate mirroring for Back side."""
    # PANEL_WIDTH = 510mm.

    df = pd.DataFrame({
        'X_COORDINATES': [10000, 400000], # 10mm, 400mm
        'Y_COORDINATES': [0, 0],
        'SIDE': ['B', 'B']
    })

    result = normalize_coordinates(df, 10, 10)

    # Point 1: 10mm
    # Flip: 510 - 10 = 500mm.
    # Gap: 500 >= 255 -> 500 + 20 = 520.
    assert result['plot_x_coord'].iloc[0] == pytest.approx(520.0)

    # Point 2: 400mm
    # Flip: 510 - 400 = 110mm.
    # Gap: 110 < 255 -> 110.
    assert result['plot_x_coord'].iloc[1] == pytest.approx(110.0)

def test_prepare_multi_layer_data_integration():
    """Test full pipeline integration."""
    df = pd.DataFrame({
        'UNIT_INDEX_X': [0], 'X_COORDINATES': [100000], # 100mm
        'UNIT_INDEX_Y': [0], 'Y_COORDINATES': [200000], # 200mm
        'DEFECT_ID': [1], 'Verification': ['True'],
        'SIDE': ['F']
    })

    layer_data = {1: {'F': df}}

    result = prepare_multi_layer_data(layer_data, 5, 5)

    assert not result.empty
    assert 'plot_x_coord' in result.columns
    assert result['plot_x_coord'].iloc[0] == pytest.approx(100.0)
