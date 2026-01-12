
import pytest
import pandas as pd
import zipfile
import io
from src.reporting import generate_zip_package

def test_generate_zip_with_images():
    """
    Tests that the zip package generation includes PNG images when requested.
    """
    # Mock Data
    df_front = pd.DataFrame({
        'DEFECT_TYPE': ['Short', 'Cut', 'Short'],
        'Verification': ['CU18', 'N', 'CU18'],
        'HAS_VERIFICATION_DATA': [True] * 3,
        'QUADRANT': ['Q1', 'Q2', 'Q3'],
        'UNIT_INDEX_X': [1, 2, 3],
        'UNIT_INDEX_Y': [1, 2, 3],
        'plot_x': [100, 200, 300],
        'plot_y': [100, 200, 300],
        'SOURCE_FILE': ['test_front.xlsx'] * 3,
        'DEFECT_ID': [1, 2, 3]
    })

    # Needs to be non-empty
    layer_data = {
        1: {'F': df_front}
    }

    zip_bytes = generate_zip_package(
        full_df=df_front,
        panel_rows=10,
        panel_cols=10,
        quadrant_selection='All',
        verification_selection='All',
        source_filename="test",
        true_defect_coords={(1,1)},
        include_excel=False,
        include_coords=False,
        include_map=False,
        include_insights=False,
        include_png_all_layers=True,
        include_pareto_png=True,
        layer_data=layer_data
    )

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        files = z.namelist()
        assert "Images/Layer_1_Front_DefectMap.png" in files
        assert "Images/Layer_1_Front_Pareto.png" in files
        assert "Images/Still_Alive_Map.png" in files
