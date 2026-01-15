"""
State Management Module.
Implements the 'Store' pattern to unify access to Streamlit's session state.
"""
import streamlit as st
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any
from src.enums import ViewMode, Quadrant

@dataclass
class SessionStore:
    """
    Centralized store for application state.
    Wraps st.session_state to provide typed access and centralized modification logic.
    """

    def __post_init__(self):
        """Initialize default state values if they don't exist."""
        defaults = {
            'report_bytes': None,
            'layer_data': {},
            'selected_layer': None,
            'selected_side': 'F',
            'analysis_params': {},
            'active_view': 'layer', # Default start view
            'analysis_subview': ViewMode.HEATMAP.value,
            # UI Filter States
            'view_mode': ViewMode.DEFECT.value,
            'quadrant_selection': Quadrant.ALL.value,
            'verification_selection': 'All',
            'multi_layer_selection': [],
            'multi_side_selection': []
        }

        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value

    # --- Properties for Typed Access ---

    @property
    def layer_data(self) -> Dict:
        return st.session_state.layer_data

    @layer_data.setter
    def layer_data(self, data: Dict):
        st.session_state.layer_data = data

    @property
    def selected_layer(self) -> Optional[int]:
        return st.session_state.selected_layer

    @selected_layer.setter
    def selected_layer(self, layer_num: Optional[int]):
        st.session_state.selected_layer = layer_num

    @property
    def selected_side(self) -> str:
        return st.session_state.selected_side

    @selected_side.setter
    def selected_side(self, side: str):
        st.session_state.selected_side = side

    @property
    def active_view(self) -> str:
        return st.session_state.active_view

    @active_view.setter
    def active_view(self, view: str):
        st.session_state.active_view = view

    @property
    def analysis_subview(self) -> str:
        return st.session_state.analysis_subview

    @analysis_subview.setter
    def analysis_subview(self, subview: str):
        st.session_state.analysis_subview = subview

    @property
    def analysis_params(self) -> Dict:
        return st.session_state.analysis_params

    @analysis_params.setter
    def analysis_params(self, params: Dict):
        st.session_state.analysis_params = params

    @property
    def report_bytes(self) -> Optional[bytes]:
        return st.session_state.report_bytes

    @report_bytes.setter
    def report_bytes(self, data: Optional[bytes]):
        st.session_state.report_bytes = data

    # --- UI Filter Properties ---
    @property
    def view_mode(self) -> str:
        return st.session_state.view_mode

    @view_mode.setter
    def view_mode(self, val: str):
        st.session_state.view_mode = val

    @property
    def quadrant_selection(self) -> str:
        return st.session_state.quadrant_selection

    @quadrant_selection.setter
    def quadrant_selection(self, val: str):
        st.session_state.quadrant_selection = val

    @property
    def verification_selection(self) -> str:
        return st.session_state.verification_selection

    @verification_selection.setter
    def verification_selection(self, val: str):
        st.session_state.verification_selection = val

    @property
    def multi_layer_selection(self) -> List[int]:
        return st.session_state.multi_layer_selection

    @multi_layer_selection.setter
    def multi_layer_selection(self, val: List[int]):
        st.session_state.multi_layer_selection = val

    @property
    def multi_side_selection(self) -> List[str]:
        return st.session_state.multi_side_selection

    @multi_side_selection.setter
    def multi_side_selection(self, val: List[str]):
        st.session_state.multi_side_selection = val

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
