import time
from playwright.sync_api import sync_playwright

def verify_app():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1280, 'height': 1024}) # Larger viewport
        try:
            page.goto("http://localhost:8599")

            # Wait for sidebar
            page.wait_for_selector("[data-testid='stSidebar']", timeout=10000)

            # Find the Run button. It's a form submit button.
            # Often rendered as a button with text.
            # Using a more specific locator.
            # Note: The button text includes the emoji.
            run_btn = page.get_by_role("button", name="🚀 Run")

            # Wait for it to be attached
            run_btn.wait_for(state="attached", timeout=5000)

            # Scroll into view if needed
            run_btn.scroll_into_view_if_needed()

            run_btn.click()
            print("Clicked Run button")

            # Wait for the chart to appear
            # The chart replaces the "Please upload..." message.
            page.wait_for_selector(".stPlotlyChart", timeout=30000)

            # Give it a bit more time to fully render
            time.sleep(5)

            page.screenshot(path="verification/app_screenshot.png")
            print("Screenshot saved to verification/app_screenshot.png")

        except Exception as e:
            print(f"Error: {e}")
            page.screenshot(path="verification/error_screenshot.png")
        finally:
            browser.close()

if __name__ == "__main__":
    verify_app()
