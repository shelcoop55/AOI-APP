"""
Configuration and Styling Module.

This module contains all configuration and styling variables for the application,
including color themes and the method for loading defect-specific styles.
"""
from dataclasses import dataclass
from typing import Dict, Any, TYPE_CHECKING
import streamlit as st
import json
from pathlib import Path

if TYPE_CHECKING:
    try:
        from xlsxwriter.workbook import Workbook
    except ImportError:
        pass

# --- Physical Constants (in mm) ---
# Hardcoded Total Frame Dimensions as per user request
FRAME_WIDTH = 510.0
FRAME_HEIGHT = 515.0

# Default Configuration Values (Copper Grid Panel Spec)
# Updated to align with specific user guide:
# Margins 13.5mm (X) and 15.0mm (Y), Gaps 3.0mm, Quadrants 235x235mm.
DEFAULT_OFFSET_X = 13.5
DEFAULT_OFFSET_Y = 15.0
DEFAULT_GAP_X = 3.0
DEFAULT_GAP_Y = 3.0

# Default Dynamic Gaps (Updated per user request)
DYNAMIC_GAP_X = 5.0
DYNAMIC_GAP_Y = 3.5

DEFAULT_PANEL_ROWS = 6
DEFAULT_PANEL_COLS = 6
INTER_UNIT_GAP = 0.25

# Active Panel Dimensions (Calculated Defaults)
# Derived from Quadrant Width 235mm * 2 = 470mm
PANEL_WIDTH = 470.0
PANEL_HEIGHT = 470.0

# Legacy Gap Constant (for backward compatibility)
GAP_SIZE = DEFAULT_GAP_X

# Derived constants
QUADRANT_WIDTH = PANEL_WIDTH / 2
QUADRANT_HEIGHT = PANEL_HEIGHT / 2

@dataclass
class PanelConfig:
    """Dataclass to group panel physical dimensions."""
    frame_width: float = FRAME_WIDTH
    frame_height: float = FRAME_HEIGHT
    offset_x: float = DEFAULT_OFFSET_X
    offset_y: float = DEFAULT_OFFSET_Y
    gap_x: float = DEFAULT_GAP_X
    gap_y: float = DEFAULT_GAP_Y
    dynamic_gap_x: float = DYNAMIC_GAP_X
    dynamic_gap_y: float = DYNAMIC_GAP_Y
    panel_rows: int = DEFAULT_PANEL_ROWS
    panel_cols: int = DEFAULT_PANEL_COLS
    panel_width: float = PANEL_WIDTH
    panel_height: float = PANEL_HEIGHT
    inter_unit_gap: float = INTER_UNIT_GAP

DEFAULT_PANEL_CONFIG = PanelConfig()

# --- Theme Configuration ---
@dataclass
class PlotTheme:
    background_color: str
    plot_area_color: str
    panel_background_color: str
    axis_color: str
    text_color: str

    # Grid colors derived from panel/axis usually
    unit_face_color: str = '#F4B486' # Light Copper/Peach
    unit_edge_color: str = '#8B4513' # Saddle Brown

    # Inner Border/Gap Color
    inner_gap_color: str = '#000000'

# Default Theme (Dark Mode / Copper)
DEFAULT_THEME = PlotTheme(
    background_color='#2C3E50',       # Dark Blue-Grey
    plot_area_color='#333333',        # Dark Grey
    panel_background_color='#C87533', # Rich Copper
    axis_color='#8B4513',             # Saddle Brown
    text_color='#FFFFFF',             # White
    inner_gap_color='#000000'         # Default Black
)

# --- Legacy Constants (Backward Compatibility) ---
# These are used if no dynamic theme is passed
PANEL_COLOR = DEFAULT_THEME.panel_background_color
PANEL_BACKGROUND_COLOR = DEFAULT_THEME.panel_background_color
UNIT_FACE_COLOR = DEFAULT_THEME.unit_face_color
UNIT_EDGE_COLOR = DEFAULT_THEME.unit_edge_color
GRID_COLOR = DEFAULT_THEME.axis_color # Often same as axis
AXIS_TEXT_COLOR = DEFAULT_THEME.text_color # Often same as text
BACKGROUND_COLOR = DEFAULT_THEME.background_color
PLOT_AREA_COLOR = DEFAULT_THEME.plot_area_color
TEXT_COLOR = DEFAULT_THEME.text_color

# Colors for the "Still Alive" yield map
ALIVE_CELL_COLOR = '#2ECC71' # A vibrant green for cells without "True" defects.
DEFECTIVE_CELL_COLOR = '#E74C3C' # A strong red for cells with "True" defects.

# Colors for Verification Status (Sankey Chart)
VERIFICATION_COLOR_SAFE = '#00FF7F'   # Spring Green (Bright Neon)
VERIFICATION_COLOR_DEFECT = '#FF3131' # Neon Red

# --- Neon Color Palette ---
# High-contrast, saturated colors for the Sankey chart in Dark Mode.
NEON_PALETTE = [
    '#00FFFF', # Cyan
    '#FF00FF', # Magenta
    '#FFFF00', # Yellow
    '#00FF00', # Lime
    '#FF4500', # OrangeRed
    '#1E90FF', # DodgerBlue
    '#FF1493', # DeepPink
    '#7FFF00', # Chartreuse
    '#FFD700', # Gold
    '#00CED1'  # DarkTurquoise
]

# --- Fallback Color Palette ---
# A list of visually distinct colors to be used for new, unrecognized defect types.
# This ensures that any defect from an uploaded file will get a color for plotting.
FALLBACK_COLORS = NEON_PALETTE + [
    '#FF6347',  # Tomato
    '#4682B4',  # SteelBlue
    '#32CD32',  # LimeGreen
    '#6A5ACD',  # SlateBlue
    '#40E0D0',  # Turquoise
    '#DA70D6',  # Orchid
    '#20B2AA',  # LightSeaGreen
    '#8A2BE2'   # BlueViolet
]

# --- Reporting Constants ---
CRITICAL_DEFECT_TYPES = ["Short", "Cut/Short"]
REPORT_HEADER_COLOR = '#DDEBF7'
CRITICAL_DEFECT_BG_COLOR = '#FFC7CE'
CRITICAL_DEFECT_FONT_COLOR = '#9C0006'

# --- Verification Logic ---
# Values in the 'Verification' column that are considered "Safe" (Non-Defects).
# Any value NOT in this list is treated as a "True Defect" that impacts yield.
# Comparisons should be case-insensitive.
SAFE_VERIFICATION_VALUES = [
    'GE57',
    'N',
    'TA',
    'FALSE',
    'FALSE ALARM',
    'F'
]

# Pre-computed set for efficient case-insensitive lookup
SAFE_VERIFICATION_VALUES_UPPER = {v.upper() for v in SAFE_VERIFICATION_VALUES}

# --- Excel Report Style Definitions ---
class ExcelReportStyle:
    """Centralized styling for Excel Reports."""

    @staticmethod
    def get_formats(workbook: Any) -> Dict[str, Any]:
        """
        Defines report formats.

        Args:
            workbook: xlsxwriter.Workbook (typed as Any to avoid hard dependency check)
        """
        return {
            'title': workbook.add_format({'bold': True, 'font_size': 18, 'font_color': PANEL_COLOR, 'valign': 'vcenter'}),
            'subtitle': workbook.add_format({'bold': True, 'font_size': 12, 'valign': 'vcenter'}),
            'header': workbook.add_format({
                'bold': True, 'text_wrap': True, 'valign': 'top',
                'fg_color': REPORT_HEADER_COLOR,
                'border': 1, 'align': 'center'
            }),
            'cell': workbook.add_format({'border': 1}),
            'percent': workbook.add_format({'num_format': '0.00%', 'border': 1}),
            'density': workbook.add_format({'num_format': '0.00', 'border': 1}),
            'critical': workbook.add_format({'bg_color': CRITICAL_DEFECT_BG_COLOR, 'font_color': CRITICAL_DEFECT_FONT_COLOR})
        }

# --- Defect Styling (Loaded from JSON) ---

@st.cache_data
def load_defect_styles() -> Dict[str, str]:
    """
    Loads the defect style mapping from an external JSON file.
    Cached to prevent repeated disk I/O.

    This function looks for 'assets/defect_styles.json' relative to the project root.
    If the file is not found or is corrupted, it prints a warning and returns a
    default, hardcoded color map to ensure the application can still run.

    Returns:
        Dict[str, str]: A dictionary mapping defect types to their corresponding colors.
    """
    style_path = Path("assets/defect_styles.json")
    try:
        with open(style_path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        # Fallback to a default map if the file is missing or corrupt
        # print(f"Warning: Could not load 'defect_styles.json' ({e}). Using default colors.")
        return {
            'Nick': '#9B59B6', 'Short': '#E74C3C', 'Missing Feature': '#2ECC71',
            'Cut': '#1ABC9C', 'Fine Short': '#BE90D4', 'Pad Violation': '#BDC3C7',
            'Island': '#F39C12', 'Cut/Short': '#3498DB', 'Nick/Protrusion': '#F1C40F'
        }

defect_style_map: Dict[str, str] = load_defect_styles()
