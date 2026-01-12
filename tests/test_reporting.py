import pytest
import pandas as pd
from io import BytesIO
from src.reporting import generate_excel_report
from src.data_handler import load_data
import streamlit as st
import importlib
from src import data_handler
from tests.test_data_handler import test_excel_file

@pytest.fixture
def sample_report_df(test_excel_file, monkeypatch) -> pd.DataFrame:
    """
    Uses the load_data function to generate a realistic DataFrame for testing reporting.
    Now returns the combined DataFrame for a layer, simulating what the app does.
    """
    monkeypatch.setattr(st, "cache_data", lambda func: func)
    monkeypatch.setattr(st.sidebar, "success", lambda *args, **kwargs: None)
    monkeypatch.setattr(st, "warning", lambda *args, **kwargs: None)
    importlib.reload(data_handler)

    layer_data = data_handler.load_data(test_excel_file, panel_rows=1, panel_cols=1)
    # The report combines all sides of a layer
    return pd.concat(layer_data[1].values(), ignore_index=True)

def test_generate_excel_report_structure(sample_report_df):
    """
    Tests that the generated Excel report has the correct structure (sheets).
    """
    report_bytes = generate_excel_report(sample_report_df, 1, 1, "test_file.xlsx")

    assert isinstance(report_bytes, bytes) and len(report_bytes) > 0

    with pd.ExcelFile(BytesIO(report_bytes), engine='openpyxl') as xls:
        expected_sheets = ['Quarterly Summary', 'Panel-Wide Top Defects', 'Q1 Top Defects', 'Q2 Top Defects', 'Q3 Top Defects', 'Q4 Top Defects', 'Full Defect List']
        assert all(sheet in xls.sheet_names for sheet in expected_sheets)

def test_generate_excel_report_summary_content(sample_report_df):
    """
    Tests the content of the 'Quarterly Summary' sheet.
    """
    report_bytes = generate_excel_report(sample_report_df, 1, 1, "test_file.xlsx")
    # The KPI table header is on row 11, so we skip 11 rows to read it as the header.
    kpi_df = pd.read_excel(BytesIO(report_bytes), sheet_name='Quarterly Summary', skiprows=11)

    expected_columns = ['Quadrant', 'Total Defects', 'Defect Density']
    assert all(col in kpi_df.columns for col in expected_columns)
    assert len(kpi_df) == 5

    total_row = kpi_df[kpi_df['Quadrant'] == 'Total']
    assert total_row['Total Defects'].iloc[0] == 4

    q1_row = kpi_df[kpi_df['Quadrant'] == 'Q1']
    assert q1_row['Total Defects'].iloc[0] == 1
    assert q1_row['Defect Density'].iloc[0] == 1.0

def test_generate_excel_report_top_defects_content(sample_report_df):
    """
    Tests the content of a 'Top Defects' sheet (e.g., for Q1).
    """
    report_bytes = generate_excel_report(sample_report_df, 1, 1, "test_file.xlsx")
    q1_defects_df = pd.read_excel(BytesIO(report_bytes), sheet_name='Q1 Top Defects')

    expected_columns = ['Defect Type', 'Count', 'Percentage']
    assert all(col in q1_defects_df.columns for col in expected_columns)

    assert len(q1_defects_df) == 1
    assert q1_defects_df['Defect Type'].iloc[0] == 'Nick'
    assert q1_defects_df['Count'].iloc[0] == 1
    assert q1_defects_df['Percentage'].iloc[0] == 1.0

def test_generate_excel_report_full_list_content(sample_report_df):
    """
    Tests the content of the 'Full Defect List' sheet.
    """
    report_bytes = generate_excel_report(sample_report_df, 1, 1, "test_file.xlsx")
    full_list_df = pd.read_excel(BytesIO(report_bytes), sheet_name='Full Defect List')

    expected_columns = ['UNIT_INDEX_X', 'UNIT_INDEX_Y', 'DEFECT_TYPE', 'QUADRANT', 'SIDE', 'SOURCE_FILE']
    assert all(col in full_list_df.columns for col in expected_columns)
    assert len(full_list_df) == 4

    short_defect = full_list_df[full_list_df['DEFECT_TYPE'] == 'Short']
    assert not short_defect.empty
    assert short_defect['QUADRANT'].iloc[0] == 'Q2'
    assert short_defect['SIDE'].iloc[0] == 'F'
    assert short_defect['UNIT_INDEX_X'].iloc[0] == 1
    assert short_defect['UNIT_INDEX_Y'].iloc[0] == 0