import streamlit as st
from typing import List, Optional
import pandas as pd
from src.state import SessionStore
from src.utils import get_bu_name_from_filename
from src.enums import ViewMode, Quadrant
from src.views.still_alive import render_still_alive_main
from src.views.multi_layer import render_multi_layer_view
from src.views.layer_view import render_layer_view
from src.analysis import get_analysis_tool

class ViewManager:
    """
    Manages view routing and navigation components.
    Decouples UI layout from application logic.
    """
    def __init__(self, store: SessionStore):
        self.store = store

    def render_navigation(self):
        """Renders the top navigation bar (Layer Selection, View Switching)."""
        if not self.store.layer_data:
            return

        with st.container():
            # Create a layout: Layer Selector (Left) | View Mode Toggles (Right)
            col1, col2 = st.columns([2, 1])

            with col1:
                self._render_layer_selector()

            with col2:
                self._render_global_view_toggles()

        st.divider()

    def _render_layer_selector(self):
        """Renders the scalable layer selection widget."""
        layer_keys = sorted(self.store.layer_data.keys())
        if not layer_keys:
            return

        # Prepare options for the selectbox
        options = []
        option_map = {}
        for num in layer_keys:
            first_side_key = next(iter(self.store.layer_data[num]))
            # Handle empty dataframe case safely
            try:
                source_file = self.store.layer_data[num][first_side_key]['SOURCE_FILE'].iloc[0]
                bu_name = get_bu_name_from_filename(str(source_file))
            except (IndexError, AttributeError):
                bu_name = ""

            label = f"Layer {num}: {bu_name}" if bu_name else f"Layer {num}"
            options.append(label)
            option_map[label] = num

        # Current selection index
        current_layer = self.store.selected_layer
        current_index = 0
        if current_layer:
             for i, opt in enumerate(options):
                 if option_map[opt] == current_layer:
                     current_index = i
                     break

        def on_layer_change():
            label = st.session_state.layer_selector
            layer_num = option_map[label]
            self.store.set_layer_view(layer_num)
            # Auto-select side logic
            layer_info = self.store.layer_data.get(layer_num, {})
            if 'F' in layer_info:
                self.store.selected_side = 'F'
            elif 'B' in layer_info:
                self.store.selected_side = 'B'
            elif layer_info:
                 self.store.selected_side = next(iter(layer_info.keys()))

        # Layout: Layer Select | Side Select
        sub_col1, sub_col2 = st.columns([2, 1])

        with sub_col1:
            st.selectbox(
                "Select Layer",
                options=options,
                index=current_index,
                key="layer_selector",
                on_change=on_layer_change,
                label_visibility="collapsed"
            )

        with sub_col2:
            # Render Side Toggles if in Layer View
            # We show it even if not strictly in 'layer' view if a layer is selected,
            # to allow easy context switching.
            if self.store.selected_layer:
                layer_info = self.store.layer_data.get(self.store.selected_layer, {})
                if len(layer_info) >= 1:
                    sides = sorted(layer_info.keys())
                    side_options = ["Front" if s == 'F' else "Back" for s in sides]
                    side_map_rev = {"Front": 'F', "Back": 'B'}

                    current_side_label = "Front" if self.store.selected_side == 'F' else "Back"
                    # Validate current selection
                    if current_side_label not in side_options and side_options:
                         current_side_label = side_options[0]

                    def on_side_change():
                         label = st.session_state.side_selector
                         self.store.selected_side = side_map_rev[label]

                    # Use pills if available (st 1.40+) or radio
                    if hasattr(st, "pills"):
                         st.pills(
                             "Side",
                             side_options,
                             selection_mode="single",
                             default=current_side_label,
                             key="side_selector",
                             on_change=on_side_change,
                             label_visibility="collapsed"
                         )
                    else:
                         st.radio(
                             "Side",
                             side_options,
                             horizontal=True,
                             key="side_selector",
                             on_change=on_side_change,
                             index=side_options.index(current_side_label) if current_side_label in side_options else 0,
                             label_visibility="collapsed"
                         )

    def _render_global_view_toggles(self):
        # Buttons for Global Views
        col_sa, col_ml = st.columns(2)

        with col_sa:
             is_active = self.store.active_view == 'still_alive'
             st.button(
                 "Still Alive",
                 type="primary" if is_active else "secondary",
                 use_container_width=True,
                 on_click=lambda: setattr(self.store, 'active_view', 'still_alive')
             )

        with col_ml:
             is_active = self.store.active_view == 'multi_layer_defects'
             st.button(
                 "Multi-Layer",
                 type="primary" if is_active else "secondary",
                 use_container_width=True,
                 on_click=lambda: setattr(self.store, 'active_view', 'multi_layer_defects')
             )

    def render_main_view(self):
        """Dispatches the rendering to the appropriate view function."""

        # Ensure we have data before trying to render views that require it
        if not self.store.layer_data:
             st.info("Please upload data and run analysis to proceed.")
             return

        if self.store.active_view == 'still_alive':
            render_still_alive_main(self.store)

        elif self.store.active_view == 'multi_layer_defects':
            render_multi_layer_view(
                self.store,
                self.store.multi_layer_selection,
                self.store.multi_side_selection
            )

        elif self.store.active_view == 'analysis_dashboard':
            tool = get_analysis_tool(self.store.analysis_subview, self.store)
            tool.render_main()

        elif self.store.active_view == 'layer':
            render_layer_view(
                self.store,
                self.store.view_mode,
                self.store.quadrant_selection,
                self.store.verification_selection
            )
        else:
            # Fallback
            st.warning(f"Unknown view: {self.store.active_view}")
