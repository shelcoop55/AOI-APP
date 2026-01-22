import pytest
import pandas as pd
import numpy as np
from src.analysis.calculations import aggregate_stress_data, calculate_yield_killers, get_cross_section_matrix, FilterContext
from src.models import PanelData, BuildUpLayer, StressMapData, YieldKillerMetrics

def create_mock_panel():
    panel = PanelData()
    # Layer 1 Front: Defect at (1,1)
    df1 = pd.DataFrame({
        'DEFECT_ID': [1],
        'UNIT_INDEX_X': [1], 'UNIT_INDEX_Y': [1],
        'DEFECT_TYPE': ['TypeA'],
        'Verification': ['TypeA'],
        'SIDE': ['F']
    })
    panel.add_layer(BuildUpLayer(1, 'F', df1, 5, 5))

    # Layer 1 Back: Defect at (1,1)
    df2 = pd.DataFrame({
        'DEFECT_ID': [2],
        'UNIT_INDEX_X': [1], 'UNIT_INDEX_Y': [1],
        'DEFECT_TYPE': ['TypeB'],
        'Verification': ['TypeB'],
        'SIDE': ['B']
    })
    panel.add_layer(BuildUpLayer(1, 'B', df2, 5, 5))
    return panel

def test_aggregate_stress_data_cumulative():
    panel = create_mock_panel()
    # Context
    # select layer 1, sides F and B
    context = FilterContext(
        selected_layers=[1],
        selected_sides=['F', 'B']
    )

    result = aggregate_stress_data(panel, context, 5, 5)

    assert isinstance(result, StressMapData)
    assert result.total_defects == 2
    assert result.grid_counts[1, 1] == 2

def test_calculate_yield_killers():
    panel = create_mock_panel()
    context = FilterContext(
        selected_layers=[1],
        selected_sides=['F', 'B']
    )

    metrics = calculate_yield_killers(panel, 5, 5, context)

    assert isinstance(metrics, YieldKillerMetrics)
    assert metrics.top_killer_layer == "Layer 1"
    assert metrics.worst_unit_count == 2 # Both at (1,1)
