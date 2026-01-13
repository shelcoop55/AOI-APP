import pandas as pd
import os

files = ['BU-02B.xlsx', 'BU-02F.xlsx']

for file in files:
    print(f"--- Inspecting {file} ---")
    if not os.path.exists(file):
        print(f"File {file} not found.")
        continue

    try:
        xl = pd.ExcelFile(file, engine='openpyxl')
        print(f"Sheet names: {xl.sheet_names}")

        if 'Defects' in xl.sheet_names:
            df = pd.read_excel(file, sheet_name='Defects', engine='openpyxl')
            print(f"Columns: {df.columns.tolist()}")
            print(f"Shape: {df.shape}")
            print("First 5 rows:")
            print(df.head())
            print("Data Types:")
            print(df.dtypes)

            # Check for required columns
            required_columns = ['DEFECT_TYPE', 'UNIT_INDEX_X', 'UNIT_INDEX_Y']
            missing = [col for col in required_columns if col not in df.columns]
            if missing:
                print(f"WARNING: Missing required columns: {missing}")
            else:
                print("All required columns present.")

            # Check coordinate ranges if possible
            if 'UNIT_INDEX_X' in df.columns and 'UNIT_INDEX_Y' in df.columns:
                print(f"X Range: {df['UNIT_INDEX_X'].min()} - {df['UNIT_INDEX_X'].max()}")
                print(f"Y Range: {df['UNIT_INDEX_Y'].min()} - {df['UNIT_INDEX_Y'].max()}")

        else:
            print("WARNING: Sheet 'Defects' not found.")

    except Exception as e:
        print(f"Error reading {file}: {e}")
    print("\n")
