"""
Configuration and Styling Module.

This module contains all configuration and styling variables for the application,
including color themes and the method for loading defect-specific styles.
"""

# --- Physical Constants (in mm) ---
# These define the real-world dimensions of the panel being simulated.
PANEL_WIDTH = 600
PANEL_HEIGHT = 600
# The physical gap between the quadrants on the panel.
GAP_SIZE = 20


# --- Style Theme: Post-Etch AOI Panel ---
# This palette is designed to look like a copper-clad panel from the PCB/IC Substrate industry.

PANEL_COLOR = '#B87333'      # A metallic, classic copper color for the panels.
GRID_COLOR = '#000000'       # Black for the main grid lines for high contrast.
BACKGROUND_COLOR = '#212121' # A dark charcoal grey for the app background, mimicking an inspection machine.
PLOT_AREA_COLOR = '#333333'  # A slightly lighter grey for the plot area to create subtle depth.
TEXT_COLOR = '#FFFFFF'       # White text for readability on the dark background.

# --- Reporting Constants ---
CRITICAL_DEFECT_TYPES = ["Short", "Cut/Short"]

