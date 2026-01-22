import re
import streamlit as st
from typing import Dict, Optional, Any, TYPE_CHECKING
from src.config import BACKGROUND_COLOR, TEXT_COLOR, PANEL_COLOR

if TYPE_CHECKING:
    from src.models import PanelData

# Compile Regex Patterns Globally
RE_BU_MATCH = re.compile(r"(BU-\d{2})", re.IGNORECASE)
RE_SAMPLE_MATCH = re.compile(r"Sample Data Layer (\d+)")
RE_CONSECUTIVE_UNDERSCORES = re.compile(r"_+")

def get_bu_name_from_filename(filename: str) -> str:
    """
    Extracts the 'BU-XX' part from a filename.
    Returns the original filename if no match is found.
    """
    match = RE_BU_MATCH.search(filename)
    if match:
        return match.group(1).upper()

    # Fallback for sample data
    match = RE_SAMPLE_MATCH.search(filename)
    if match:
        return f"BU-{int(match.group(1)):02d}"

    return filename

def generate_standard_filename(
    prefix: str,
    selected_layer: Optional[int],
    layer_data: "PanelData", # String forward reference
    analysis_params: Dict,
    extension: str = "zip"
) -> str:
    """
    Generates a standardized filename: [Type]_[BU]_[ProcessStep]_[LotNumber].ext
    Example: Defective_Cell_Coordinates_BU_02_Processstep_Lotnumber.xlsx
    """
    parts = [prefix]

    # 1. BU Part
    bu_label = "BU_ALL"
    if selected_layer is not None:
        try:
            # Accessing via standard dict access if possible.
            # In manager.py: self.store.layer_data[layer_id] works.
            if hasattr(layer_data, '__getitem__'):
                 layer_info = layer_data[selected_layer] # type: ignore
                 first_side = next(iter(layer_info))

                 # Access dataframe: layer_info[first_side] is usually a DataFrame or object with 'SOURCE_FILE'
                 layer_obj = layer_info[first_side]

                 # Handle if it is a DataFrame directly or an object
                 src_file = "Unknown"
                 if hasattr(layer_obj, 'columns') and 'SOURCE_FILE' in layer_obj.columns:
                      src_file = str(layer_obj['SOURCE_FILE'].iloc[0])
                 elif hasattr(layer_obj, 'source_file'):
                      src_file = layer_obj.source_file
                 elif isinstance(layer_obj, dict) and 'SOURCE_FILE' in layer_obj:
                      src_file = layer_obj['SOURCE_FILE'] # If it's a dict record

                 bu_part = get_bu_name_from_filename(src_file)
                 if bu_part and bu_part.upper().startswith("BU"):
                     # Replace hyphen with underscore for consistency: BU-02 -> BU_02
                     bu_label = bu_part.replace("-", "_")
                 else:
                     # Fallback to standard format using layer index if filename doesn't contain BU
                     bu_label = f"BU_{selected_layer:02d}"
        except (KeyError, AttributeError, StopIteration, IndexError):
            # Fallback if extraction fails
            bu_label = f"BU_{selected_layer:02d}"

    parts.append(bu_label)

    # 2. Process Step
    proc_step = analysis_params.get('process_comment', '').strip()
    if proc_step:
        parts.append(proc_step)

    # 3. Lot Number
    lot_num = analysis_params.get('lot_number', '').strip()
    if lot_num:
        parts.append(lot_num)

    # Join and Sanitize
    base_name = "_".join(parts)
    # Allow alphanumeric, underscores, hyphens. Remove others.

    safe_name = "".join([c if c.isalnum() or c in "._-" else "_" for c in base_name])

    # Remove consecutive underscores if sanitization caused them
    safe_name = RE_CONSECUTIVE_UNDERSCORES.sub("_", safe_name)

    return f"{safe_name}.{extension}"

@st.cache_data
def _read_css_file(file_path: str) -> Optional[str]:
    """Reads CSS file content with caching."""
    try:
        with open(file_path) as f:
            return f.read()
    except FileNotFoundError:
        return None

def load_css(file_path: str) -> None:
    """Loads a CSS file and injects it into the Streamlit app."""
    css_content = _read_css_file(file_path)
    if css_content:
        css_variables = f'''
        <style>
            :root {{
                --background-color: {BACKGROUND_COLOR};
                --text-color: {TEXT_COLOR};
                --panel-color: {PANEL_COLOR};
                --panel-hover-color: #d48c46;
            }}
            {css_content}
        </style>
        '''
        st.markdown(css_variables, unsafe_allow_html=True)
