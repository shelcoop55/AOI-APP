"""
State Management Module.
Implements the 'Store' pattern to unify access to Streamlit's session state.
"""
import streamlit as st
from dataclasses import dataclass, field
from typing import Optional, Dict, List, TypedDict, Any, TYPE_CHECKING
from src.enums import ViewMode, Quadrant

if TYPE_CHECKING:
    from src.models import PanelData

# --- TypedDict Definitions ---

class AnalysisParams(TypedDict, total=False):
    """
    Type definition for analysis parameters stored in session state.
    """
    panel_rows: int
    panel_cols: int
    panel_width: float
    panel_height: float
    gap_x: float
    gap_y: float
    gap_size: float # Backwards compatibility
    lot_number: str
    process_comment: str
    offset_x: float
    offset_y: float
    visual_origin_x: float
    visual_origin_y: float
    dyn_gap_x: float
    dyn_gap_y: float
    fixed_offset_x: float
    fixed_offset_y: float

class AppState(TypedDict, total=False):
    """
    Type definition for the entire application session state.
    """
    report_bytes: Optional[bytes]
    dataset_id: Optional[str]
    layer_data_metadata: Dict
    selected_layer: Optional[int]
    selected_side: str
    analysis_params: AnalysisParams
    active_view: str
    analysis_subview: str
    view_mode: str
    quadrant_selection: str
    verification_selection: str # Legacy single select
    multi_verification_selection: List[str] # Unified multi select
    multi_layer_selection: List[int]
    multi_side_selection: List[str]
    uploader_key: int

@dataclass
class SessionStore:
    """
    Centralized store for application state.
    Wraps st.session_state to provide typed access and centralized modification logic.
    """

    def __post_init__(self):
        """Initialize default state values if they don't exist."""
        # Define defaults using the TypedDict structure as a guide
        defaults: AppState = {
            'report_bytes': None,
            'dataset_id': None,
            'layer_data_metadata': {},
            'selected_layer': None,
            'selected_side': 'F',
            'analysis_params': {},
            'active_view': 'layer',
            'analysis_subview': ViewMode.HEATMAP.value,
            'view_mode': ViewMode.DEFECT.value,
            'quadrant_selection': Quadrant.ALL.value,
            'verification_selection': 'All',
            # 'multi_verification_selection': [],  <-- Removed to allow detection of uninitialized state
            'multi_layer_selection': [],
            'multi_side_selection': []
        }

        # Robust initialization
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value

    # --- Properties for Typed Access ---

    @property
    def dataset_id(self) -> Optional[str]:
        return st.session_state.get('dataset_id')

    @dataset_id.setter
    def dataset_id(self, val: Optional[str]):
        st.session_state['dataset_id'] = val

    @property
    def layer_data(self) -> Optional["PanelData"]:
        """
        Retrieves the heavy PanelData object from the global cache using the stored dataset_id.
        """
        # Import internally to avoid circular dependency
        from src.data_handler import load_data

        if not self.dataset_id:
            return None

        current_uploader_key = f"uploaded_files_{st.session_state.get('uploader_key', 0)}"
        files = st.session_state.get(current_uploader_key, [])

        # Use defaults if params not set yet
        rows = self.analysis_params.get("panel_rows", 7)
        cols = self.analysis_params.get("panel_cols", 7)

        # Safety Check
        is_sample = self.dataset_id and str(self.dataset_id).startswith("sample")

        if not files and not is_sample:
             return None

        # Call load_data. If inputs haven't changed, it hits cache.
        return load_data(files, rows, cols)

    @property
    def layer_data_keys(self) -> Dict:
        return st.session_state.get('layer_data_metadata', {})

    @layer_data_keys.setter
    def layer_data_keys(self, val: Dict):
        st.session_state['layer_data_metadata'] = val

    @property
    def selected_layer(self) -> Optional[int]:
        return st.session_state.get('selected_layer')

    @selected_layer.setter
    def selected_layer(self, layer_num: Optional[int]):
        st.session_state['selected_layer'] = layer_num

    @property
    def selected_side(self) -> str:
        return st.session_state.get('selected_side', 'F')

    @selected_side.setter
    def selected_side(self, side: str):
        st.session_state['selected_side'] = side

    @property
    def active_view(self) -> str:
        return st.session_state.get('active_view', 'layer')

    @active_view.setter
    def active_view(self, view: str):
        st.session_state['active_view'] = view

    @property
    def analysis_subview(self) -> str:
        return st.session_state.get('analysis_subview', ViewMode.HEATMAP.value)

    @analysis_subview.setter
    def analysis_subview(self, subview: str):
        st.session_state['analysis_subview'] = subview

    @property
    def analysis_params(self) -> AnalysisParams:
        return st.session_state.get('analysis_params', {})

    @analysis_params.setter
    def analysis_params(self, params: AnalysisParams):
        st.session_state['analysis_params'] = params

    @property
    def report_bytes(self) -> Optional[bytes]:
        return st.session_state.get('report_bytes')

    @report_bytes.setter
    def report_bytes(self, data: Optional[bytes]):
        st.session_state['report_bytes'] = data

    # --- UI Filter Properties ---
    @property
    def view_mode(self) -> str:
        return st.session_state.get('view_mode', ViewMode.DEFECT.value)

    @view_mode.setter
    def view_mode(self, val: str):
        st.session_state['view_mode'] = val

    @property
    def quadrant_selection(self) -> str:
        return st.session_state.get('quadrant_selection', Quadrant.ALL.value)

    @quadrant_selection.setter
    def quadrant_selection(self, val: str):
        st.session_state['quadrant_selection'] = val

    @property
    def verification_selection(self) -> str:
        return st.session_state.get('verification_selection', 'All')

    @verification_selection.setter
    def verification_selection(self, val: str):
        st.session_state['verification_selection'] = val

    @property
    def multi_layer_selection(self) -> List[int]:
        return st.session_state.get('multi_layer_selection', [])

    @multi_layer_selection.setter
    def multi_layer_selection(self, val: List[int]):
        st.session_state['multi_layer_selection'] = val

    @property
    def multi_side_selection(self) -> List[str]:
        return st.session_state.get('multi_side_selection', [])

    @multi_side_selection.setter
    def multi_side_selection(self, val: List[str]):
        st.session_state['multi_side_selection'] = val

    # --- Actions ---

    def clear_all(self):
        """Resets the entire session state."""
        st.session_state.clear()

    def set_layer_view(self, layer_num: int, side: Optional[str] = None):
        """Helper to switch to a specific layer view."""
        self.active_view = 'layer'
        self.selected_layer = layer_num
        if side:
            self.selected_side = side
