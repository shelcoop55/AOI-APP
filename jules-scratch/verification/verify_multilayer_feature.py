import pytest
from playwright.sync_api import sync_playwright, expect
import pandas as pd
from io import BytesIO
import time

def create_test_excel(defect_ids, layer_num):
    """Helper function to create an in-memory Excel file for a specific layer."""
    data = {
        'DEFECT_ID': defect_ids,
        'DEFECT_TYPE': ['Nick'] * len(defect_ids),
        'UNIT_INDEX_X': [0] * len(defect_ids),
        'UNIT_INDEX_Y': [0] * len(defect_ids),
        'Verification': ['T'] * len(defect_ids),
    }
    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Defects')
    output.seek(0)
    # The filename and MIME type must match the expected format for Playwright.
    return {
        "name": f"BU-{layer_num:02d}-test-data.xlsx",
        "mimeType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "buffer": output.read()
    }

def run_verification():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            # 1. Navigate to the app
            page.goto("http://localhost:8501", timeout=30000)

            # Wait for the app to be ready by looking for the main h1 title.
            # Using a more specific locator to avoid strict mode violation.
            expect(page.get_by_role("heading", name="📊 Panel Defect Analysis Tool", level=1)).to_be_visible(timeout=20000)

            # 2. Create and upload files for three layers
            file1 = create_test_excel([101, 102], 1)
            file2 = create_test_excel([201, 202, 203], 2)
            file3 = create_test_excel([301], 3)

            # Use the file chooser to upload multiple files
            with page.expect_file_chooser() as fc_info:
                page.get_by_test_id("stFileUploaderDropzone").locator("button").click()
            file_chooser = fc_info.value
            file_chooser.set_files([file1, file2, file3])

            # Verify that the file names are visible in the uploader
            expect(page.get_by_text(file1["name"])).to_be_visible()
            expect(page.get_by_text(file2["name"])).to_be_visible()
            expect(page.get_by_text(file3["name"])).to_be_visible()

            # 3. Run analysis
            page.get_by_role("button", name="Run Analysis").click()

            # 4. Verify Layer 3 is selected by default (highest number)
            # The title of the plot should contain the layer number
            expect(page.get_by_text("Panel Defect Map - Layer 3")).to_be_visible(timeout=15000)

            # 5. Click the "Layer 1" button to switch views
            page.get_by_role("button", name="Layer 1").click()

            # 6. Assert that the view has updated to Layer 1
            expect(page.get_by_text("Panel Defect Map - Layer 1")).to_be_visible(timeout=15000)

            # 7. Take screenshot
            page.screenshot(path="jules-scratch/verification/verification.png")
            print("Screenshot captured successfully.")

        except Exception as e:
            print(f"An error occurred: {e}")
            page.screenshot(path="jules-scratch/verification/error.png")
        finally:
            browser.close()

if __name__ == "__main__":
    run_verification()