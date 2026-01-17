from playwright.sync_api import sync_playwright, expect
import time

def verify_app(page):
    print("Navigating to app...")
    page.goto("http://localhost:8501")

    # Wait for the app to load
    print("Waiting for app to load...")
    # Streamlit apps often have a loading state. We can wait for the main container or specific elements.
    # We will wait for the text "Control Panel" in the sidebar which indicates the app has initialized.
    expect(page.get_by_text("Control Panel")).to_be_visible(timeout=20000)

    # Expand the "Advanced Configuration" expander if necessary, but the inputs might be hidden.
    # The code says `with st.expander("⚙️ Advanced Configuration", expanded=False):`
    # So we need to click it to see the inputs.

    print("Expanding Advanced Configuration...")
    # Look for the expander summary
    expander = page.get_by_text("Advanced Configuration")
    expander.click()

    # Wait for the inputs to be visible
    print("Waiting for inputs...")
    expect(page.get_by_label("X Origin (mm)")).to_be_visible()
    expect(page.get_by_label("Y Origin (mm)")).to_be_visible()

    # Take a screenshot
    print("Taking screenshot...")
    page.screenshot(path="verification/app_verification.png")
    print("Screenshot saved.")

if __name__ == "__main__":
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            verify_app(page)
        except Exception as e:
            print(f"Error: {e}")
            page.screenshot(path="verification/error_screenshot.png")
        finally:
            browser.close()
