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

            # 2. Defect View is the default, so the summary should be visible.
            expect(page.get_by_text("Panel Defect Map")).to_be_visible(timeout=30000)
            summary_expander = page.locator("div[data-testid='stExpander']", has_text="Verification Summary")
            expect(summary_expander).to_be_visible()

            # 3. ** SCROLL to the summary and take the screenshot **
            summary_expander.scroll_into_view_if_needed()
            time.sleep(1) # Allow for render
            page.screenshot(path="jules-scratch/verification/sidebar_summary_visible.png")
            print("Screenshot with summary visible taken successfully.")

            # 4. Switch to Summary View
            summary_radio = page.get_by_text("Summary View", exact=True)
            expect(summary_radio).to_be_visible()
            summary_radio.click()

            # 5. Assert that the verification summary is now hidden
            expect(summary_expander).to_be_hidden()
            print("Successfully verified that the summary is hidden in other views.")

        except Exception as e:
            print(f"An error occurred: {e}")
            page.screenshot(path="jules-scratch/verification/error.png")
        finally:
            browser.close()

if __name__ == "__main__":
    run_verification()