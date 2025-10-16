from playwright.sync_api import sync_playwright

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("http://localhost:8501")

        # Wait for the "Still Alive" button to be visible and then click it
        still_alive_button = page.get_by_role("button", name="Still Alive")
        still_alive_button.wait_for(state="visible", timeout=60000)
        still_alive_button.click()

        # Wait for the multiselect to be visible
        multiselect = page.get_by_text("Select Defect Statuses for Still Alive Map")
        multiselect.wait_for(state="visible")

        # Select 'F' and 'TA' in the multiselect
        page.get_by_text("Select Defect Statuses for Still Alive Map").click()
        page.get_by_role("option", name="F").click()
        page.get_by_role("option", name="TA").click()

        # Click outside the multiselect to close it
        page.get_by_role("heading", name="Still Alive Panel Yield Map").click()


        page.screenshot(path="jules-scratch/verification/verification.png")
        browser.close()

if __name__ == "__main__":
    run()