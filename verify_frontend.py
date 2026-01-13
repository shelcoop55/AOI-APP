import time
from playwright.sync_api import sync_playwright, expect
import os

def run_verification():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # Navigate to the Streamlit app
        print("Navigating to app...")
        page.goto("http://localhost:8501")

        # Wait for the app to load. Use exact text for the main title H1.
        print("Waiting for app to load...")
        expect(page.get_by_role("heading", name="📊 Panel Defect Analysis Tool", exact=True)).to_be_visible(timeout=10000)

        print("Clicking 'Run Analysis' to load sample data...")
        # Locate the button. Streamlit buttons are often inside form submit buttons.
        page.get_by_role("button", name="🚀 Run Analysis").click()

        # Wait for data to load and sidebar to update
        # We expect "Multi-Layer Defects" button to appear.
        print("Waiting for analysis to complete...")
        # It might take a moment.
        multi_layer_btn = page.get_by_role("button", name="Multi-Layer Defects")
        expect(multi_layer_btn).to_be_visible(timeout=15000)

        # Click the Multi-Layer Defects button
        print("Clicking 'Multi-Layer Defects' button...")
        multi_layer_btn.click()

        # Wait for the header "Multi-Layer Combined Defect Map"
        print("Waiting for view to render...")
        expect(page.get_by_role("heading", name="Multi-Layer Combined Defect Map")).to_be_visible(timeout=10000)

        # Take a screenshot
        screenshot_path = "/home/jules/verification/multi_layer_view.png"
        page.screenshot(path=screenshot_path, full_page=True)
        print(f"Screenshot saved to {screenshot_path}")

        browser.close()

if __name__ == "__main__":
    run_verification()
