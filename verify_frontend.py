
from playwright.sync_api import sync_playwright, expect
import time

def verify_app():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Set viewport to ensure we see the chart
        page = browser.new_page(viewport={'width': 1280, 'height': 1024})

        # 1. Navigate
        print("Navigating to app...")
        page.goto("http://localhost:3000")

        # 2. Wait for Load
        print("Waiting for page load...")
        expect(page.get_by_text("Control Panel")).to_be_visible(timeout=20000)

        # 3. Click "Run" button
        print("Clicking Run...")
        run_btn = page.get_by_role("button", name="🚀 Run")
        # Ensure it's ready
        run_btn.wait_for(state="visible")
        run_btn.click()

        # 4. Wait for Results
        # Sample data loading might take a moment.
        # We can look for the Plotly chart container or some text that appears after run.
        # "Panel Defect Map" title in the chart.
        print("Waiting for chart to render...")
        time.sleep(5) # Give it time to render the chart

        # 5. Take Screenshot
        print("Taking screenshot...")
        page.screenshot(path="/home/jules/verification/verification.png")

        browser.close()
        print("Done.")

if __name__ == "__main__":
    verify_app()
