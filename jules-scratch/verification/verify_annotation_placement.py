from playwright.sync_api import sync_playwright, expect
import time

def run_verification():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            # 1. Navigate to the app and run the analysis
            page.goto("http://localhost:8501", timeout=60000)
            expect(page.locator("div[data-testid='stAppViewContainer']")).to_be_visible(timeout=30000)
            run_button = page.get_by_role("button", name="Run Analysis")
            expect(run_button).to_be_enabled()
            run_button.click()

            # 2. Wait for the Defect Map to be visible
            expect(page.get_by_text("Panel Defect Map")).to_be_visible(timeout=30000)

            # 3. Wait for the chart to render
            time.sleep(2)

            # 4. Take a screenshot for visual confirmation
            page.screenshot(path="jules-scratch/verification/final_annotation_placement.png")
            print("Screenshot taken successfully.")

        except Exception as e:
            print(f"An error occurred: {e}")
            page.screenshot(path="jules-scratch/verification/error.png")
        finally:
            browser.close()

if __name__ == "__main__":
    run_verification()