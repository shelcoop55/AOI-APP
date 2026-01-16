"""
Configuration and Styling Module.

This module contains all configuration and styling variables for the application,
including color themes and the method for loading defect-specific styles.
"""

# --- Physical Constants (in mm) ---
# Default dimensions based on "12x12 Copper Grid Panel" spec
# Defaults updated to 410x452mm Total Panel Size with 13mm Gap.
# Quad Width = (410 - 13) / 2 = 198.5
# Quad Height = (452 - 13) / 2 = 219.5
DEFAULT_QUAD_WIDTH = 198.5
DEFAULT_QUAD_HEIGHT = 219.5
DEFAULT_MARGIN_X = 35.0  # Default Origin/Offset (User requested ~35mm in examples)
DEFAULT_MARGIN_Y = 35.0
DEFAULT_GAP_MID = 13.0
DEFAULT_GAP_UNIT = 0.0   # Default Gap 0 (Contiguous)

# Legacy constants kept for compatibility but should be overridden by dynamic logic
# Total Active Width (approx)
PANEL_WIDTH = (DEFAULT_QUAD_WIDTH * 2) + DEFAULT_GAP_MID
PANEL_HEIGHT = (DEFAULT_QUAD_HEIGHT * 2) + DEFAULT_GAP_MID
GAP_SIZE = DEFAULT_GAP_MID

# --- Style Theme: Copper Aesthetic ---
PANEL_COLOR = '#C87533'      # Rich Copper (Background/Border)
GRID_COLOR = '#8B4513'       # Saddle Brown (Unit Edge/Stroke)
UNIT_FACE_COLOR = '#F4B486'  # Light Copper/Peach (Unit Face)
TEXT_COLOR = '#5A2D0C'       # Dark Bronze (Text)

BACKGROUND_COLOR = '#F5F5F5' # Light grey background for the app to contrast with copper?
                             # Or keep dark? The user didn't specify APP background, only PANEL background.
                             # Keeping dark mode for app usually looks better with copper/orange.
                             # But TEXT_COLOR #5A2D0C is dark. Dark text on Dark background is bad.
                             # If Text is Dark Bronze, Background should be Light.
                             # Switching App Background to Light Grey to support Dark Bronze text.

PLOT_AREA_COLOR = '#FFFFFF'  # Plot background (behind the copper panel)

# Colors for the "Still Alive" yield map
ALIVE_CELL_COLOR = '#2ECC71' # Green (Good) - Keep standard or adjust?
                             # Spec didn't change logic colors, only Panel colors.
DEFECTIVE_CELL_COLOR = '#E74C3C' # Red (Bad)

# Colors for Verification Status (Sankey Chart)
VERIFICATION_COLOR_SAFE = '#00FF7F'   # Spring Green
VERIFICATION_COLOR_DEFECT = '#FF3131' # Neon Red

# --- Neon Color Palette ---
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

# --- Verification Logic ---
SAFE_VERIFICATION_VALUES = [
    'GE57',
    'N',
    'TA',
    'FALSE',
    'FALSE ALARM',
    'F'
]

# --- Defect Styling (Loaded from JSON) ---
import json
from pathlib import Path
from typing import Dict

def load_defect_styles() -> Dict[str, str]:
    style_path = Path(__file__).parent.parent / "assets/defect_styles.json"
    try:
        with open(style_path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Warning: Could not load 'defect_styles.json' ({e}). Using default colors.")
        return {
            'Nick': '#9B59B6', 'Short': '#E74C3C', 'Missing Feature': '#2ECC71',
            'Cut': '#1ABC9C', 'Fine Short': '#BE90D4', 'Pad Violation': '#BDC3C7',
            'Island': '#F39C12', 'Cut/Short': '#3498DB', 'Nick/Protrusion': '#F1C40F'
        }

defect_style_map: Dict[str, str] = load_defect_styles()
