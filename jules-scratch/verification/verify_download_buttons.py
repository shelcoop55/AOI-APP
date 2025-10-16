from playwright.sync_api import sync_playwright, expect

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("http://localhost:8501")

        # Navigate to the "Still Alive" view
        page.get_by_role("button", name="Still Alive").click()

        # Wait for the download buttons to be visible
        expect(page.get_by_role("button", name="Download Visual Map Report")).to_be_visible(timeout=60000)
        expect(page.get_by_role("button", name="Download Coordinate List")).to_be_visible(timeout=60000)

        # Take a screenshot of the summary section
        page.screenshot(path="jules-scratch/verification/still_alive_summary_with_downloads.png")

        browser.close()

if __name__ == "__main__":
    run()