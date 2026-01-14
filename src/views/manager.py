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
        """
        Renders the top navigation controls.
        Specific logic for 'Layer Inspection' view where we show Layer/Side/Quadrant/Verification controls.
        """
        if not self.store.layer_data:
            return

        # Only render the top control bar if we are in the main 'Layer Inspection' mode
        if self.store.active_view == 'layer':
            self._render_layer_inspection_controls()
            st.divider()

    def _render_layer_inspection_controls(self):
        """Renders the top control row for Layer Inspection."""

        # Prepare Data for Dropdowns
        layer_keys = sorted(self.store.layer_data.keys())
        if not layer_keys:
            return

        # Layer Options
        layer_options = []
        layer_option_map = {}
        for num in layer_keys:
            # Try to get BU name
            bu_name = ""
            try:
                first_side_key = next(iter(self.store.layer_data[num]))
                source_file = self.store.layer_data[num][first_side_key]['SOURCE_FILE'].iloc[0]
                bu_name = get_bu_name_from_filename(str(source_file))
            except (IndexError, AttributeError, StopIteration):
                pass
            label = f"Layer {num}: {bu_name}" if bu_name else f"Layer {num}"
            layer_options.append(label)
            layer_option_map[label] = num

        # Determine Current Layer Index
        current_layer_idx = 0
        if self.store.selected_layer:
             for i, opt in enumerate(layer_options):
                 if layer_option_map[opt] == self.store.selected_layer:
                     current_layer_idx = i
                     break

        # Prepare Data for Side Toggle
        # Default options
        side_options = ["Front", "Back"]
        # If current layer has limited sides, we might want to disable one?
        # But keeping it simple for now as per design.
        current_side_label = "Front" if self.store.selected_side == 'F' else "Back"

        # Prepare Data for Verification
        active_df = pd.DataFrame()
        if self.store.selected_layer:
            layer_info = self.store.layer_data.get(self.store.selected_layer, {})
            active_df = layer_info.get(self.store.selected_side, pd.DataFrame())

        ver_options = ['All'] + sorted(active_df['Verification'].unique().tolist()) if not active_df.empty and 'Verification' in active_df.columns else ['All']
        current_ver = self.store.verification_selection
        current_ver_idx = ver_options.index(current_ver) if current_ver in ver_options else 0

        # --- Layout: 4 Columns ---
        col1, col2, col3, col4 = st.columns(4)

        # 1. Layer Selection
        with col1:
            def on_layer_change():
                label = st.session_state.layer_selector_top
                layer_num = layer_option_map[label]
                self.store.set_layer_view(layer_num)
                # Auto-select side logic
                layer_info = self.store.layer_data.get(layer_num, {})
                if 'F' in layer_info:
                    self.store.selected_side = 'F'
                elif 'B' in layer_info:
                    self.store.selected_side = 'B'
                elif layer_info:
                     self.store.selected_side = next(iter(layer_info.keys()))

            st.selectbox(
                "Select Layer",
                options=layer_options,
                index=current_layer_idx,
                key="layer_selector_top",
                on_change=on_layer_change,
                label_visibility="collapsed"
            )

        # 2. Side Selection (Front/Back)
        with col2:
            def on_side_change():
                label = st.session_state.side_selector_top
                self.store.selected_side = 'F' if label == "Front" else 'B'

            # Use pills if available for button-like toggle
            if hasattr(st, "pills"):
                 st.pills(
                     "Side",
                     side_options,
                     selection_mode="single",
                     default=current_side_label,
                     key="side_selector_top",
                     on_change=on_side_change,
                     label_visibility="collapsed"
                 )
            else:
                 st.radio(
                     "Side",
                     side_options,
                     horizontal=True,
                     key="side_selector_top",
                     on_change=on_side_change,
                     index=side_options.index(current_side_label),
                     label_visibility="collapsed"
                 )

        # 3. Quadrant Selection
        with col3:
            quad_options = Quadrant.values()
            curr_quad = self.store.quadrant_selection
            curr_quad_idx = quad_options.index(curr_quad) if curr_quad in quad_options else 0

            st.selectbox(
                "Quadrant",
                options=quad_options,
                index=curr_quad_idx,
                key="quadrant_selection", # Updates store automatically via SessionStore proxy? No, store reads session state
                label_visibility="collapsed",
                # Note: SessionStore properties might not auto-sync if we don't use on_change or property setter
                # But app.py initializes widgets with keys.
                # Ideally we explicitly set it.
                on_change=lambda: setattr(self.store, 'quadrant_selection', st.session_state.quadrant_selection)
            )

        # 4. Verification Filter
        with col4:
            st.selectbox(
                "Verification",
                options=ver_options,
                index=current_ver_idx,
                key="verification_selection",
                label_visibility="collapsed",
                on_change=lambda: setattr(self.store, 'verification_selection', st.session_state.verification_selection)
            )

        # --- Tabs for View Mode ---
        st.markdown("") # Spacer
        tab_labels = ["Defect View", "Summary View", "Pareto View"]
        # Map tab labels to ViewMode values
        tab_map = {
            "Defect View": ViewMode.DEFECT.value,
            "Summary View": ViewMode.SUMMARY.value,
            "Pareto View": ViewMode.PARETO.value
        }

        # Determine current tab index
        current_view = self.store.view_mode
        # If current view is not one of these (e.g. legacy), default to Defect
        current_tab = "Defect View"
        for label, val in tab_map.items():
            if val == current_view:
                current_tab = label
                break

        # We can't easily programmatically set the active tab in st.tabs
        # Use st.radio or st.segmented_control (pills) for the look of tabs if we want state control?
        # Standard st.tabs contains content.
        # Design requirement: "Below Layer Selection Give Three tab option"
        # Since st.tabs are containers, we wrap the content rendering in them.

        # Implementation: We render the tabs here, and inside each tab, we call render_main_view logic?
        # BUT render_main_view is called separately in app.py logic.
        # Better approach: Use st.tabs to SET the view mode, or use custom styled radio/pills looking like tabs.
        # Using actual st.tabs implies the content is inside.

        # Let's use st.tabs and conditionally render content inside?
        # Problem: st.tabs renders all tabs at once (or lazy loads).
        # If we just want them to act as buttons:

        # Use st.pills for "Tabs" look-alike if available, or just render the content using st.tabs wrapper in render_main_view
        # But render_navigation is separated.

        # Solution: We will NOT render st.tabs here. We will render st.tabs in render_main_view if mode is layer.
        # Wait, the user said "Below Layer Selection Give Three tab option".
        # If I put st.tabs in `render_navigation`, I can't easily put the chart area inside them unless I merge the functions.
        # But `app.py` calls `render_navigation` (outside fragment) then `render_main_view` (inside fragment).

        # To support "Tabs" that switch the view (and thus the fragment content):
        # We can use a segmented control or pills here in `render_navigation` that updates `store.view_mode`.

        st.write("") # Spacer

        def on_tab_change():
             label = st.session_state.view_mode_selector
             self.store.view_mode = tab_map[label]

        if hasattr(st, "pills"):
            st.pills(
                "",
                tab_labels,
                selection_mode="single",
                default=current_tab,
                key="view_mode_selector",
                on_change=on_tab_change,
                label_visibility="collapsed"
            )
        else:
             st.radio(
                "",
                tab_labels,
                horizontal=True,
                key="view_mode_selector",
                index=tab_labels.index(current_tab),
                on_change=on_tab_change,
                label_visibility="collapsed"
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
            # Note: We are not using st.tabs container because the tabs are navigation controls
            # (handled in render_navigation) that switch the `view_mode`.
            # We just render the content for the selected mode.
            render_layer_view(
                self.store,
                self.store.view_mode,
                self.store.quadrant_selection,
                self.store.verification_selection
            )
        else:
            # Fallback
            st.warning(f"Unknown view: {self.store.active_view}")
