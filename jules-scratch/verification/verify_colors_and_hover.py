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

            # 2. Verify the hovertext on the Defect Map
            expect(page.get_by_text("Panel Defect Map")).to_be_visible(timeout=30000)
            # Find a specific point on the scatter plot and hover over it, forcing the event
            defect_point = page.locator("path.point").first
            defect_point.hover(force=True)
            time.sleep(1) # Wait for hover text to appear
            page.screenshot(path="jules-scratch/verification/defect_map_hover.png")
            print("Screenshot of Defect Map with hovertext taken successfully.")

            # 3. Switch to Summary View
            summary_radio = page.get_by_text("Summary View", exact=True)
            expect(summary_radio).to_be_visible()
            summary_radio.click()

            # 4. Verify the new chart is present and scroll it into view
            new_chart_title = page.get_by_text("Defect Verification Status by Quadrant")
            expect(new_chart_title).to_be_visible()
            new_chart_title.scroll_into_view_if_needed()

            # 5. Wait for the chart to render and take the final screenshot
            time.sleep(2)
            page.screenshot(path="jules-scratch/verification/summary_chart_colors.png")
            print("Screenshot of new Summary View chart with updated colors taken successfully.")

        except Exception as e:
            print(f"An error occurred: {e}")
            page.screenshot(path="jules-scratch/verification/error.png")
        finally:
            browser.close()

if __name__ == "__main__":
    run_verification()