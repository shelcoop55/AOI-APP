from playwright.sync_api import sync_playwright, expect

def run_verification(playwright):
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page()

    try:
        # Navigate to the Streamlit app
        page.goto("http://localhost:8501", timeout=60000)

        # Wait for the file uploader to be present
        file_uploader_locator = page.locator('input[type="file"]')
        expect(file_uploader_locator).to_be_visible(timeout=30000)

        # Upload the sample data file
        file_uploader_locator.set_input_files("sample_defect_data.xlsx")

        # Click the "Run Analysis" button
        run_button = page.get_by_role("button", name="Run Analysis")
        expect(run_button).to_be_enabled(timeout=10000)
        run_button.click()

        # Wait for the page to reload and network to be idle after the st.rerun()
        page.wait_for_load_state('networkidle', timeout=30000)

        # Wait for the plot to appear
        # The plot container is identified by class "stPlotlyChart"
        plot_locator = page.locator(".stPlotlyChart")
        expect(plot_locator).to_be_visible(timeout=30000)

        # Take a screenshot for visual verification
        page.screenshot(path="jules-scratch/verification/verification.png")

    finally:
        browser.close()

with sync_playwright() as playwright:
    run_verification(playwright)