from playwright.sync_api import sync_playwright, expect
import time

def run_verification():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            # 1. Navigate to the app
            page.goto("http://localhost:8501", timeout=30000)

            # Wait for the app to be ready
            expect(page.get_by_role("heading", name="📊 Panel Defect Analysis Tool", level=1)).to_be_visible(timeout=20000)

            # 2. Run analysis with default sample data
            page.get_by_role("button", name="Run Analysis").click()

            # 3. Click the "Still Alive" button
            still_alive_button = page.get_by_role("button", name="Still Alive")
            expect(still_alive_button).to_be_visible(timeout=15000)
            still_alive_button.click()

            # 4. Verify the legend is visible
            expect(page.get_by_text("Defect-Free Cell")).to_be_visible(timeout=15000)
            expect(page.get_by_text("Defective Cell")).to_be_visible()

            # 5. Take screenshot for visual confirmation
            page.screenshot(path="jules-scratch/verification/legend_verification.png")
            print("Screenshot of 'Still Alive' view with legend captured successfully.")

        except Exception as e:
            print(f"An error occurred during verification: {e}")
            page.screenshot(path="jules-scratch/verification/error.png")
        finally:
            browser.close()

if __name__ == "__main__":
    run_verification()