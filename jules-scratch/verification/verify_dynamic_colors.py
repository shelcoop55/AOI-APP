from playwright.sync_api import sync_playwright, expect

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("http://localhost:8501")

        # Wait for the main chart to be visible
        expect(page.locator(".stPlotlyChart")).to_be_visible(timeout=60000)

        # Take a screenshot of the defect map
        page.screenshot(path="jules-scratch/verification/defect_map.png")

        # Navigate to the Pareto chart view
        page.get_by_role("radio", name="Pareto").click()

        # Wait for the pareto chart to be visible
        expect(page.locator(".stPlotlyChart")).to_be_visible(timeout=60000)

        # Take a screenshot of the pareto chart
        page.screenshot(path="jules-scratch/verification/pareto_chart.png")

        browser.close()

if __name__ == "__main__":
    run()