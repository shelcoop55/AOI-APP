
import os
import time
from playwright.sync_api import sync_playwright

def verify_new_layout():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1600, "height": 900})

        try:
            print("Navigating...")
            page.goto("http://localhost:8501")

            # Wait for main app
            page.wait_for_selector("h1:has-text('Panel Defect Analysis Tool')", timeout=15000)

            # Click Run Analysis if needed
            if page.is_visible("text=Welcome to the Panel Defect Analysis Tool!"):
                print("Clicking Run Analysis...")
                page.get_by_role("button", name="Run Analysis").click()
                time.sleep(3)

            # Wait for data load
            page.wait_for_selector("button:has-text('BU-01')", timeout=10000)

            # 1. Switch to Analysis View
            print("Switching to Analysis...")
            page.get_by_role("button", name="Analysis", exact=True).click()
            time.sleep(2)

            # 2. Verify Layout: Controls should be in Main Content, not Sidebar
            # We look for "Analysis Controls" subheader which was added to the left column
            print("Verifying Controls Layout...")

            # Check if "Analysis Controls" is visible
            # It uses st.subheader("⚙️ Analysis Controls")
            controls_header = page.get_by_role("heading", name="Analysis Controls")

            if controls_header.is_visible():
                print("SUCCESS: 'Analysis Controls' header found in main content.")
            else:
                raise Exception("FAIL: 'Analysis Controls' header not found.")

            # 3. Switch to Root Cause
            print("Switching to Root Cause...")
            # The radio button is now in the main content.
            # Label "Select Analysis Module"
            page.get_by_text("Root Cause Analysis").click()
            time.sleep(1)

            # 4. Verify Root Cause Controls (Sliders) are visible in main area
            print("Verifying Sliders...")
            # Look for "Region of Interest (ROI)" caption
            roi_caption = page.get_by_text("Region of Interest (ROI)")
            if roi_caption.is_visible():
                print("SUCCESS: ROI controls visible.")
            else:
                raise Exception("FAIL: ROI controls not found.")

            # 5. Screenshot
            os.makedirs("verification_screenshots", exist_ok=True)
            page.screenshot(path="verification_screenshots/new_layout_root_cause.png", full_page=True)
            print("Done.")

        except Exception as e:
            print(f"Error: {e}")
            page.screenshot(path="verification_screenshots/layout_error.png")
            raise e
        finally:
            browser.close()

if __name__ == "__main__":
    verify_new_layout()
