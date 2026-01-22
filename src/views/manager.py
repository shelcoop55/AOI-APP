import streamlit as st
from typing import List, Optional, Any
import pandas as pd
from src.state import SessionStore
from src.utils import get_bu_name_from_filename
from src.enums import ViewMode, Quadrant
from src.views.still_alive import render_still_alive_main
from src.views.multi_layer import render_multi_layer_view
from src.views.layer_view import render_layer_view
from src.documentation import render_documentation
from src.analysis import get_analysis_tool
from src.reporting import generate_zip_package
from src.data_handler import load_data
from src.analysis.calculations import get_true_defect_coordinates
from src.config import DEFAULT_OFFSET_X, DEFAULT_OFFSET_Y, DEFAULT_GAP_X, DEFAULT_GAP_Y, FRAME_WIDTH, FRAME_HEIGHT, DYNAMIC_GAP_X, DYNAMIC_GAP_Y
import streamlit.components.v1 as components

class ViewManager:
    """
    Manages view routing, navigation components, and core analysis actions.
    Decouples UI layout from application logic.
    """
    def __init__(self, store: SessionStore):
        self.store = store

    def run_analysis(self, files: List[Any]):
        """
        Orchestrates the analysis process: loads data, calculates layout, and initializes state.
        """
        # Prioritize values from the widgets in session_state, falling back to stored params or defaults
        rows = st.session_state.get("panel_rows", self.store.analysis_params.get("panel_rows", 7))
        cols = st.session_state.get("panel_cols", self.store.analysis_params.get("panel_cols", 7))

        # Retrieve Advanced Params
        off_x_struct = DEFAULT_OFFSET_X
        off_y_struct = DEFAULT_OFFSET_Y
        gap_x_fixed = DEFAULT_GAP_X
        gap_y_fixed = DEFAULT_GAP_Y

        # Dynamic Gaps
        dyn_gap_x = self.store.analysis_params.get("dyn_gap_x", DYNAMIC_GAP_X)
        dyn_gap_y = self.store.analysis_params.get("dyn_gap_y", DYNAMIC_GAP_Y)

        # DYNAMIC CALCULATION
        p_width = float(FRAME_WIDTH) - 2 * off_x_struct - gap_x_fixed - 4 * dyn_gap_x
        p_height = float(FRAME_HEIGHT) - 2 * off_y_struct - gap_y_fixed - 4 * dyn_gap_y

        effective_gap_x = gap_x_fixed + 2 * dyn_gap_x
        effective_gap_y = gap_y_fixed + 2 * dyn_gap_y

        # Load Data
        data = load_data(files, rows, cols, p_width, p_height, effective_gap_x, effective_gap_y)

        if data:
            if not files:
                self.store.dataset_id = "sample_data"
            else:
                self.store.dataset_id = str(hash(tuple(f.name for f in files)))

            # Store lightweight metadata
            meta = {}
            for l_num, sides in data.items():
                meta[l_num] = list(sides.keys())
            self.store.layer_data_keys = meta

            self.store.selected_layer = max(data.keys())
            self.store.active_view = 'layer'

            # Auto-select side
            layer_info = data.get(self.store.selected_layer, {})
            if 'F' in layer_info:
                self.store.selected_side = 'F'
            elif 'B' in layer_info:
                self.store.selected_side = 'B'
            elif layer_info:
                self.store.selected_side = next(iter(layer_info.keys()))

            self.store.multi_layer_selection = sorted(data.keys())
            all_sides = set()
            for l_data in data.values():
                all_sides.update(l_data.keys())
            self.store.multi_side_selection = sorted(list(all_sides))

            # Reset verification filter to select all available options on new run
            # This ensures the UI explicitly shows all tags selected, matching user expectation
            full_df = data.get_combined_dataframe()
            if not full_df.empty and 'Verification' in full_df.columns:
                all_verifs = sorted(full_df['Verification'].dropna().astype(str).unique().tolist())
                self.store.multi_verification_selection = all_verifs
        else:
            self.store.selected_layer = None

        total_off_x_struct = off_x_struct + dyn_gap_x
        total_off_y_struct = off_y_struct + dyn_gap_y

        # Update Params with Calculated Values
        current_params = self.store.analysis_params.copy()
        current_params.update({
            "panel_rows": rows,
            "panel_cols": cols,
            "panel_width": p_width,
            "panel_height": p_height,
            "gap_x": effective_gap_x,
            "gap_y": effective_gap_y,
            "gap_size": effective_gap_x,
            "offset_x": total_off_x_struct,
            "offset_y": total_off_y_struct,
            "fixed_offset_x": off_x_struct,
            "fixed_offset_y": off_y_struct
        })
        self.store.analysis_params = current_params
        self.store.report_bytes = None

    def render_navigation(self, filter_container=None):
        # Inject Keyboard Shortcuts
        with open("src/components/keyboard_shortcuts.html", "r") as f:
            components.html(f.read(), height=0, width=0)

        if not self.store.layer_data:
            return

        self._render_top_nav_buttons()

        if self.store.active_view == 'layer':
            self._render_layer_inspection_controls(filter_container)
        elif self.store.active_view in ['documentation', 'reporting']:
            pass
        else:
            self._render_analysis_page_controls(filter_container)

    def _render_top_nav_buttons(self):
        nav_cols = st.columns(4, gap="small")

        def set_mode(m):
            if m == 'layer': self.store.active_view = 'layer'
            elif m == 'documentation': self.store.active_view = 'documentation'
            elif m == 'reporting': self.store.active_view = 'reporting'
            else:
                if self.store.active_view not in ['still_alive', 'multi_layer_defects', 'analysis_dashboard']:
                     self.store.active_view = 'still_alive'
                elif self.store.active_view == 'documentation':
                     self.store.active_view = 'still_alive'

        is_layer = self.store.active_view == 'layer'
        nav_cols[0].button("Layer Inspection", type="primary" if is_layer else "secondary", use_container_width=True, on_click=lambda: set_mode('layer'))

        is_analysis = self.store.active_view in ['analysis_dashboard', 'still_alive', 'multi_layer_defects']
        nav_cols[1].button("Analysis Page", type="primary" if is_analysis else "secondary", use_container_width=True, on_click=lambda: set_mode('analysis'))

        is_doc = self.store.active_view == 'documentation'
        nav_cols[2].button("Documentation", type="primary" if is_doc else "secondary", use_container_width=True, on_click=lambda: set_mode('documentation'))

        is_rep = self.store.active_view == 'reporting'
        nav_cols[3].button("Reporting", type="primary" if is_rep else "secondary", use_container_width=True, on_click=lambda: set_mode('reporting'))

    def _render_layer_inspection_controls(self, filter_container=None):
        layer_keys = sorted(self.store.layer_data.keys())
        if not layer_keys: return

        # Dropdowns Data
        layer_options = []
        layer_option_map = {}
        process_comment = self.store.analysis_params.get("process_comment", "")

        for num in layer_keys:
            bu_name = ""
            try:
                first_side_key = next(iter(self.store.layer_data[num]))
                source_file = self.store.layer_data[num][first_side_key]['SOURCE_FILE'].iloc[0]
                bu_name = get_bu_name_from_filename(str(source_file))
            except (IndexError, AttributeError, StopIteration): pass

            base_label = bu_name if bu_name else f"Layer {num}"
            label = f"{base_label} ({process_comment})" if process_comment else base_label
            layer_options.append(label)
            layer_option_map[label] = num

        side_options = ["Front", "Back"]

        active_df = pd.DataFrame()
        if self.store.selected_layer:
            layer_info = self.store.layer_data.get(self.store.selected_layer, {})
            active_df = layer_info.get(self.store.selected_side, pd.DataFrame())

        ver_options = []
        if not active_df.empty and 'Verification' in active_df.columns:
            ver_options = sorted(active_df['Verification'].dropna().astype(str).unique().tolist())

        # Sidebar Filters
        target = filter_container if filter_container else st.sidebar
        with target:
             st.divider()
             st.markdown("### Analysis Filters")
             if 'multi_verification_selection' in st.session_state:
                 current_selection = st.session_state['multi_verification_selection']
                 valid_selection = [x for x in current_selection if x in ver_options]
                 st.session_state['multi_verification_selection'] = valid_selection
                 st.multiselect("Filter Verification Status", options=ver_options, key="multi_verification_selection")
             else:
                 st.multiselect("Filter Verification Status", options=ver_options, default=ver_options, key="multi_verification_selection")

        self.store.verification_selection = st.session_state.get('multi_verification_selection', ver_options)

        with st.expander("Analysis Scope", expanded=True):
            if layer_options:
                l_cols = st.columns(len(layer_options), gap="small")
                for i, (label, col) in enumerate(zip(layer_options, l_cols)):
                     layer_num = layer_option_map[label]
                     is_active = (layer_num == self.store.selected_layer)
                     def on_layer_click(n):
                         def cb():
                             self.store.set_layer_view(n)
                             info = self.store.layer_data.get(n, {})
                             if 'F' in info: self.store.selected_side = 'F'
                             elif 'B' in info: self.store.selected_side = 'B'
                             elif info: self.store.selected_side = next(iter(info.keys()))
                         return cb
                     col.button(label, key=f"layer_btn_{i}", type="primary" if is_active else "secondary", use_container_width=True, on_click=on_layer_click(layer_num))

            c1, c2 = st.columns([1, 2], gap="medium")
            with c1:
                s_cols = st.columns(len(side_options), gap="small")
                for i, (label, col) in enumerate(zip(side_options, s_cols)):
                    code = 'F' if label == "Front" else 'B'
                    is_active = (code == self.store.selected_side)
                    def on_side_click(c):
                        def cb(): self.store.selected_side = c
                        return cb
                    col.button(label, key=f"side_btn_{i}", type="primary" if is_active else "secondary", use_container_width=True, on_click=on_side_click(code))

            with c2:
                quad_options = Quadrant.values()
                q_cols = st.columns(len(quad_options), gap="small")
                for i, (label, col) in enumerate(zip(quad_options, q_cols)):
                    is_active = (label == self.store.quadrant_selection)
                    def on_quad_click(l):
                        def cb(): self.store.quadrant_selection = l
                        return cb
                    col.button(label, key=f"quad_btn_{i}", type="primary" if is_active else "secondary", use_container_width=True, on_click=on_quad_click(label))

        st.markdown("")
        tab_labels = ["Defect View", "Summary View", "Pareto View"]
        tab_map = {"Defect View": ViewMode.DEFECT.value, "Summary View": ViewMode.SUMMARY.value, "Pareto View": ViewMode.PARETO.value}
        current_view = self.store.view_mode
        cols = st.columns(len(tab_labels), gap="small")

        for i, label in enumerate(tab_labels):
            mapped_val = tab_map[label]
            is_active = (mapped_val == current_view)
            def make_callback(v):
                def cb(): self.store.view_mode = v
                return cb
            cols[i].button(label, key=f"view_mode_btn_{i}", type="primary" if is_active else "secondary", use_container_width=True, on_click=make_callback(mapped_val))

    def _render_analysis_page_controls(self, filter_container=None):
        all_layers = sorted(self.store.layer_data.keys())
        full_df = self.store.layer_data.get_combined_dataframe()
        all_verifications = []
        if not full_df.empty and 'Verification' in full_df.columns:
            all_verifications = sorted(full_df['Verification'].dropna().astype(str).unique().tolist())

        target = filter_container if filter_container else st.sidebar
        with target:
             st.divider()
             st.markdown("### Analysis Filters")
             if 'multi_verification_selection' in st.session_state:
                 current_selection = st.session_state['multi_verification_selection']
                 valid_selection = [x for x in current_selection if x in all_verifications]
                 st.session_state['multi_verification_selection'] = valid_selection
                 st.multiselect("Filter Verification Status", options=all_verifications, key="multi_verification_selection")
             else:
                 st.multiselect("Filter Verification Status", options=all_verifications, default=all_verifications, key="multi_verification_selection")

             show_alignment = False
             if self.store.active_view == 'multi_layer_defects': show_alignment = True
             elif self.store.active_view == 'analysis_dashboard' and self.store.analysis_subview == ViewMode.HEATMAP.value: show_alignment = True

             if show_alignment:
                 st.markdown("### Alignment")
                 st.checkbox("Align Back Side (Flip Units)", value=False, key="flip_back_side", help="If enabled, Back Side units are mirrored horizontally.")

        current_tab_text = "Heatmap"
        if self.store.active_view == 'still_alive': current_tab_text = "Still Alive"
        elif self.store.active_view == 'multi_layer_defects': current_tab_text = "Multi-Layer"
        elif self.store.active_view == 'analysis_dashboard':
             sub_map_rev = {ViewMode.HEATMAP.value: "Heatmap", ViewMode.STRESS.value: "Stress Map", ViewMode.ROOT_CAUSE.value: "Root Cause", ViewMode.INSIGHTS.value: "Insights"}
             current_tab_text = sub_map_rev.get(self.store.analysis_subview, "Heatmap")

        with st.expander("Analysis Scope", expanded=True):
            layer_buttons_data = []
            process_comment = self.store.analysis_params.get("process_comment", "")
            for num in all_layers:
                bu_name = ""
                try:
                    first_side_key = next(iter(self.store.layer_data[num]))
                    source_file = self.store.layer_data[num][first_side_key]['SOURCE_FILE'].iloc[0]
                    bu_name = get_bu_name_from_filename(str(source_file))
                except: pass
                base_label = bu_name if bu_name else f"Layer {num}"
                label = f"{base_label} ({process_comment})" if process_comment else base_label
                layer_buttons_data.append({'num': num, 'label': label})

            if layer_buttons_data:
                btns = [d['label'] for d in layer_buttons_data]
                l_cols = st.columns(len(btns), gap="small")
                current_selection = self.store.multi_layer_selection if self.store.multi_layer_selection else all_layers
                for i, d in enumerate(layer_buttons_data):
                    num = d['num']
                    is_sel = num in current_selection
                    def on_click_layer(n):
                        def cb():
                            new_sel = list(self.store.multi_layer_selection) if self.store.multi_layer_selection else list(all_layers)
                            if n in new_sel:
                                if len(new_sel) > 1: new_sel.remove(n)
                            else: new_sel.append(n)
                            self.store.multi_layer_selection = sorted(new_sel)
                        return cb
                    l_cols[i].button(d['label'], key=f"an_btn_l_{num}", type="primary" if is_sel else "secondary", use_container_width=True, on_click=on_click_layer(num))

            show_quadrant = current_tab_text not in ["Root Cause", "Multi-Layer"]
            if show_quadrant: c_sides, c_quads = st.columns(2, gap="medium")
            else: c_sides = st.container()

            with c_sides:
                current_sides = st.session_state.get("analysis_side_pills", ["Front", "Back"])
                s_cols = st.columns(4, gap="small") if not show_quadrant else st.columns(2, gap="small")
                def toggle_side(side):
                    def cb():
                        new_sides = list(st.session_state.get("analysis_side_pills", ["Front", "Back"]))
                        if side in new_sides:
                            if len(new_sides) > 1: new_sides.remove(side)
                        else: new_sides.append(side)
                        st.session_state["analysis_side_pills"] = new_sides
                    return cb
                is_f = "Front" in current_sides
                s_cols[0].button("Front", key="an_side_f", type="primary" if is_f else "secondary", use_container_width=True, on_click=toggle_side("Front"))
                is_b = "Back" in current_sides
                s_cols[1].button("Back", key="an_side_b", type="primary" if is_b else "secondary", use_container_width=True, on_click=toggle_side("Back"))

            if show_quadrant:
                with c_quads:
                    quad_opts = ["All", "Q1", "Q2", "Q3", "Q4"]
                    current_quad = st.session_state.get("analysis_quadrant_selection", "All")
                    q_cols = st.columns(len(quad_opts), gap="small")
                    def set_quad(q): st.session_state["analysis_quadrant_selection"] = q
                    for i, q_label in enumerate(quad_opts):
                        is_active = (current_quad == q_label)
                        q_cols[i].button(q_label, key=f"an_quad_{q_label}", type="primary" if is_active else "secondary", use_container_width=True, on_click=lambda q=q_label: set_quad(q))

        tabs = ["Still Alive", "Insights", "Heatmap", "Stress Map", "Root Cause", "Multi-Layer"]
        t_cols = st.columns(len(tabs), gap="small")
        for i, label in enumerate(tabs):
            is_active = (label == current_tab_text)
            def on_tab(sel):
                def cb():
                    if sel == "Still Alive": self.store.active_view = 'still_alive'
                    elif sel == "Multi-Layer": self.store.active_view = 'multi_layer_defects'
                    else:
                         self.store.active_view = 'analysis_dashboard'
                         sub_map = {"Heatmap": ViewMode.HEATMAP.value, "Stress Map": ViewMode.STRESS.value, "Root Cause": ViewMode.ROOT_CAUSE.value, "Insights": ViewMode.INSIGHTS.value}
                         self.store.analysis_subview = sub_map[sel]
                return cb
            t_cols[i].button(label, key=f"an_tab_{i}", type="primary" if is_active else "secondary", use_container_width=True, on_click=on_tab(label))

        st.divider()

        if current_tab_text == "Heatmap":
             st.slider("Smoothing (Sigma)", min_value=1, max_value=20, value=5, key="heatmap_sigma")
        elif current_tab_text == "Stress Map":
             st.radio("Mode", ["Cumulative", "Delta Difference"], horizontal=True, key="stress_map_mode")
        elif current_tab_text == "Root Cause":
             c1, c2 = st.columns(2)
             with c1: st.radio("Slice Axis", ["X (Column)", "Y (Row)"], horizontal=False, key="rca_axis")
             with c2:
                 max_idx = (self.store.analysis_params.get('panel_cols', 7) * 2) - 1
                 st.slider("Slice Index", 0, max_idx, 0, key="rca_index")

    def _sync_params_from_session_state(self):
        """
        Updates analysis_params with latest values from session state widgets
        that are not part of the main form (e.g. Advanced Config).
        """
        # Mapping of widget key to param key
        mapping = {
            "plot_origin_x": "visual_origin_x",
            "plot_origin_y": "visual_origin_y",
            "dyn_gap_x": "dyn_gap_x",
            "dyn_gap_y": "dyn_gap_y"
        }

        updated = False
        current_params = self.store.analysis_params.copy()

        for widget_key, param_key in mapping.items():
            if widget_key in st.session_state:
                val = st.session_state[widget_key]
                if current_params.get(param_key) != val:
                    current_params[param_key] = val
                    updated = True

        if updated:
            self.store.analysis_params = current_params

    def render_reporting_view(self):
        st.header("📥 Generate Analysis Reports")
        st.markdown("Use this page to generate and download comprehensive reports.")

        col1, col2 = st.columns(2, gap="medium")
        with col1:
            st.subheader("Report Content")
            include_excel = st.checkbox("Excel Report", value=True)
            include_coords = st.checkbox("Coordinate List", value=True)
            st.subheader("Visualizations")
            include_map = st.checkbox("Defect Map (HTML)", value=True)
            include_insights = st.checkbox("Insights Charts", value=True)
        with col2:
            st.subheader("Image Exports")
            include_png_all = st.checkbox("Defect Maps (PNG) - All Layers", value=False)
            include_pareto_png = st.checkbox("Pareto Charts (PNG) - All Layers", value=False)
            st.markdown("##### Additional Analysis Charts")
            include_heatmap_png = st.checkbox("Heatmap (PNG)", value=False)
            include_stress_png = st.checkbox("Stress Map (PNG)", value=False)
            include_root_cause_png = st.checkbox("Root Cause (PNG)", value=False)
            include_still_alive_png = st.checkbox("Still Alive Map (PNG)", value=False)

        st.markdown("---")

        if st.button("📦 Generate Download Package", type="primary", use_container_width=True):
            with st.spinner("Generating Package..."):
                full_df = self.store.layer_data.get_combined_dataframe()
                true_defect_coords = get_true_defect_coordinates(self.store.layer_data)
                current_theme = st.session_state.get('plot_theme', None)

                self.store.report_bytes = generate_zip_package(
                    full_df=full_df,
                    panel_rows=self.store.analysis_params.get('panel_rows', 7),
                    panel_cols=self.store.analysis_params.get('panel_cols', 7),
                    quadrant_selection=self.store.quadrant_selection,
                    verification_selection=self.store.verification_selection,
                    source_filename="Multiple Files",
                    true_defect_coords=true_defect_coords,
                    include_excel=include_excel, include_coords=include_coords,
                    include_map=include_map, include_insights=include_insights,
                    include_png_all_layers=include_png_all, include_pareto_png=include_pareto_png,
                    include_heatmap_png=include_heatmap_png, include_stress_png=include_stress_png,
                    include_root_cause_png=include_root_cause_png, include_still_alive_png=include_still_alive_png,
                    layer_data=self.store.layer_data,
                    process_comment=self.store.analysis_params.get("process_comment", ""),
                    lot_number=self.store.analysis_params.get("lot_number", ""),
                    theme_config=current_theme
                )
                st.success("Package generated successfully!")

        if self.store.report_bytes:
            from src.utils import generate_standard_filename
            zip_filename = generate_standard_filename(
                prefix="Defect_Analysis_Package",
                selected_layer=self.store.selected_layer,
                layer_data=self.store.layer_data,
                analysis_params=self.store.analysis_params,
                extension="zip"
            )
            st.download_button("Download Package (ZIP)", data=self.store.report_bytes, file_name=zip_filename, mime="application/zip", type="primary", use_container_width=True)

    def render_main_view(self):
        self._sync_params_from_session_state()

        if not self.store.layer_data:
             st.info("Please upload data and run analysis to proceed.")
             return

        current_theme = st.session_state.get('plot_theme', None)

        if self.store.active_view == 'still_alive':
            render_still_alive_main(self.store, theme_config=current_theme)
        elif self.store.active_view == 'multi_layer_defects':
            render_multi_layer_view(self.store, self.store.multi_layer_selection, self.store.multi_side_selection, theme_config=current_theme)
        elif self.store.active_view == 'analysis_dashboard':
            tool = get_analysis_tool(self.store.analysis_subview, self.store)
            if hasattr(tool, 'render_main_with_theme'): tool.render_main_with_theme(theme_config=current_theme)
            else: tool.render_main()
        elif self.store.active_view == 'layer':
            render_layer_view(self.store, self.store.view_mode, self.store.quadrant_selection, self.store.verification_selection, theme_config=current_theme)
        elif self.store.active_view == 'documentation':
             render_documentation()
        elif self.store.active_view == 'reporting':
             self.render_reporting_view()
        else:
            st.warning(f"Unknown view: {self.store.active_view}")
