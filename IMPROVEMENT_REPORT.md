# Codebase Improvement Report

This report outlines specific improvements for each Python file in the `src` directory and `app.py`, focusing on efficiency, performance, optimization, and best practices.

## Root Application

### `app.py`
1.  **Refactor Main Logic**: Move the complex `on_run_analysis` callback logic into a dedicated controller or service function (e.g., in `src/views/manager.py` or a new `src/controllers` module). This keeps the main UI entry point clean and declarative.
2.  **Optimize File Upload Reset**: The current logic uses a dynamic `uploader_key` in session state to reset the file uploader. A more standard approach in recent Streamlit versions is using `st.form` with `clear_on_submit=False` and a separate "Clear" button that invokes `st.rerun()`, simplifying the state management.
3.  **Performance - CSS Loading**: `load_css` is called on every rerun. Cache the CSS content using `st.cache_data` or `st.cache_resource` to avoid reading from disk on every interaction, especially if the file is large.

## `src` Directory

### `src/config.py`
1.  **Caching JSON Load**: The `load_defect_styles` function reads from disk every time the module is imported or accessed. Wrap this in `st.cache_data` or a simple module-level lru_cache to prevent repeated disk I/O.
2.  **Type Hinting**: Improve type strictness. For example, `ExcelReportStyle.get_formats` takes `workbook` without a specific type hint (e.g., `xlsxwriter.Workbook`). Adding strict types helps IDEs and static analysis.
3.  **Constant Organization**: Group related constants into `dataclasses` or `Enums` (e.g., a `PanelConfig` dataclass for dimensions) to prevent namespace pollution and make passing configuration cleaner.

### `src/data_handler.py`
1.  **Strict Type Checking**: The `load_data` function uses `List[Any]` for uploaded files. Change this to `List[UploadedFile]` (from `streamlit.runtime.uploaded_file_manager`) to enable better type checking and IDE autocompletion.
2.  **Refactor Circular Dependency**: `aggregate_stress_data` imports from `src.analysis.calculations` inside the function to avoid circular imports. This indicates a structural issue. Move the aggregation logic entirely to `calculations.py` or a shared `services` module.
3.  **Vectorization**: The sample data generation loop (`for _ in range(num_points):`) is slow. Use NumPy vectorization to generate all random coordinates and defect types at once, significantly speeding up "sample mode" initialization.

### `src/models.py`
1.  **Lazy Evaluation**: `_add_plotting_coordinates` is called immediately in `__post_init__`. If these coordinates are not always needed (e.g., for summary views), move this logic to a property or a `prepare_for_plotting()` method to save memory and processing time on initial load.
2.  **Memory Optimization**: `BuildUpLayer` stores both `raw_df` and modifies it. If the raw dataframe is large, avoid keeping multiple references or copies. Ensure inplace operations are used effectively.
3.  **Type Safety**: `PanelData.__getitem__` returns a dictionary proxy. This is non-standard behavior for an object. Deprecate `__getitem__` in favor of explicit `get_layer(num)` or `get_layers()` methods to improve code clarity and prevent misuse.

### `src/plotting.py`
1.  **Reduce Trace Count**: In `create_defect_traces`, a new trace is created for every defect group. For large datasets with many defect types, this creates a heavy DOM in the browser. Group traces or use a single `Scattergl` trace with a discrete colorscale for better frontend performance.
2.  **Optimize Shape Generation**: `create_grid_shapes` generates many individual SVG paths/rects. If the grid is static, generate it once and cache the `layout.shapes` object, reusing it across updates instead of recomputing it every time.
3.  **Remove Magic Numbers**: Replace hardcoded values like `510`, `515`, `20.0` (radius) with named constants from `src.config` to ensure maintainability and consistency.

### `src/reporting.py`
1.  **Refactor Large Function**: `_create_summary_sheet` is too long and handles layout, data calculation, and chart generation. Split this into `_calculate_kpis`, `_write_summary_table`, and `_add_summary_chart` for better readability and testability.
2.  **Format Reusability**: The `formats` dictionary is passed around everywhere. Create a `ReportWriter` class that holds the workbook and formats as instance state, reducing function argument clutter.
3.  **Memory Management**: `generate_zip_package` creates all figures in memory before writing. For very large reports, consider writing to the zip stream immediately after generation to keep peak memory usage low.

### `src/state.py`
1.  **Robust Default Handling**: In `__post_init__`, use `setdefault` or direct assignment with existence checks more idiomatically. The current loop works but explicit initialization for typed fields is clearer.
2.  **Type Hinting for Session State**: Use a `TypedDict` or a custom `SessionStateProxy` class (which `SessionStore` partially implements) to fully type-hint `st.session_state` keys, preventing typo-related bugs.
3.  **Remove Setter Logic**: Some setters (e.g., `dataset_id`) are trivial. Python's `@property` is overhead if there's no logic. Use public attributes or verify if validation logic should be added to setters.

### `src/utils.py`
1.  **Regex Compilation**: Compile regex patterns (e.g., inside `get_bu_name_from_filename`) at the module level (global constant) instead of compiling them every time the function is called.
2.  **Error Handling**: The `try-except` block in `generate_standard_filename` catches general `Exception`. Be more specific (e.g., `AttributeError`, `KeyError`) to avoid masking unexpected bugs.
3.  **Type Hinting**: `layer_data: Any` is too broad. Import `PanelData` (inside a `TYPE_CHECKING` block to avoid circular imports) and type it correctly.

### `src/documentation.py`
1.  **Externalize Content**: Move the massive `TECHNICAL_DOCUMENTATION` string to a separate Markdown file (`assets/docs.md`). Read it at runtime. This keeps Python files small and allows non-developers to edit documentation easily.
2.  **Caching**: If moved to a file, use `st.cache_data` to load the text content so disk I/O only happens once.
3.  **Structure**: Convert `VERIFICATION_DESCRIPTIONS` into a proper Enum or a JSON file if it needs to be shared with other parts of the system (like the frontend or reporting).

### `src/enums.py`
1.  **Functional Extensions**: Add helper methods to the Enums, such as `ViewMode.is_analysis()` or `Quadrant.as_index()`, to encapsulate logic related to these values instead of scattering `if mode == ...` checks in the code.
2.  **Docstrings**: Add docstrings to individual Enum members to explain what each view or quadrant represents, helpful for new developers.

## `src/analysis` Directory

### `src/analysis/base.py`
1.  **Type Safety**: Use `typing.Protocol` or keep `ABC` but ensure `SessionStore` is imported only for type checking to avoid circular dependencies if `SessionStore` starts importing analysis tools.
2.  **Interface Expansion**: Add a `teardown()` or `on_exit()` method to the interface. This allows tools to clean up resources (like heavy figures from memory) when the user switches views.

### `src/analysis/calculations.py`
1.  **Vectorize String Operations**: In `aggregate_stress_data_from_df`, the tooltip generation loop iterates over groups. Use pandas string vectorization (`df['col'] + ' ' + ...`) to build hover text columns faster.
2.  **Optimize GroupBy**: The "Top 3 per cell" logic uses multiple groupbys. Use `nlargest` directly on the groups or sort the entire dataframe once and take slices to speed up processing.
3.  **Parameter Objects**: `get_true_defect_coordinates` takes many optional arguments. Introduce a `FilterContext` dataclass to pass these parameters as a single object, making signatures cleaner.

### `src/analysis/heatmap.py`
1.  **Optimize Concatenation**: The loop accumulates DataFrames in `dfs_to_concat`. If the number of layers is large, consider filtering the master DataFrame (if available) directly using boolean masks instead of iterating and concatenating small chunks.
2.  **Remove Dead Code**: Delete commented-out sections (header, legacy sidebar) to improve readability and maintainability.
3.  **Caching Granularity**: The `get_filtered_heatmap_data` function caches based on input. Ensure `panel_data_id` is robust. If `_panel_data` changes but ID doesn't (bug), cache will be stale. Verify ID generation logic in `data_handler`.

### `src/analysis/insights.py`
1.  **Performance - Stats Loop**: The `stats_data` generation loop iterates over defect types. For high cardinality defect types, this will be slow. Calculate metrics (False Rate, counts) using vectorized pandas operations (`groupby` + `agg`) instead of a Python loop.
2.  **Avoid Copy**: `df_layer = layer.data.copy()` is called inside a loop. If data is large, this spikes memory. Use `layer.data` directly and add the `LAYER_NUM` / `SIDE` columns to a list of small metadata dictionaries, then merge, or modify a temporary list of references.
3.  **Chart Optimization**: Limit the number of slices in the Sunburst chart. If there are hundreds of defect types, group the tail into "Others" to prevent browser lag.

### `src/analysis/root_cause.py`
1.  **Fix Logic Gap**: `calculate_yield_killers` is called without respect to current filters (Layer/Verification). Update the call to pass the filtered DataFrame or current selection context so KPIs match the user's view.
2.  **Refactor Matrix Calculation**: `get_cross_section_matrix` iterates through layers. Move this logic to NumPy for faster matrix construction, especially if the panel resolution increases.
3.  **UI Feedback**: Add a visual indicator (like a line on a small heatmap) showing exactly where the current "Slice Index" is located on the panel.

### `src/analysis/stress.py`
1.  **Vectorized Aggregation**: `aggregate_stress_data` iterates over keys. Use `panel_data.get_combined_dataframe()` with a filter mask, then perform a single `groupby` or 2D histogram. This exploits Pandas/NumPy C-level speed better than Python loops.
2.  **Diff Map Logic**: The "Delta Difference" mode calculates two full maps. Ensure `aggregate_stress_data` is cached effectively (it is), otherwise this doubles the compute time.
3.  **Code Cleanliness**: Remove the manual list construction of `keys`. Use `panel_data.get_layer_keys(filter=...)` if such a helper existed (add it to `PanelData`).

## `src/views` Directory

### `src/views/layer_view.py`
1.  **Extract Business Logic**: `render_summary_view` contains heavy calculation logic (Yield, KPIs, breakdowns). Move these calculations to `src.analysis.calculations` and return a structured result object (DTO) to the view.
2.  **Deprecation Fix**: `use_container_width` in `st.dataframe` is deprecated in favor of `width`. The code attempts a fix but check compatibility. Also, `st.experimental_...` calls should be verified.
3.  **Filter Efficiency**: The filtering logic (`df[df['Verification'].isin...]`) runs on every render. Cache the filtered result in a local variable or `st.session_state` if the user is interacting with the chart but not changing filters.

### `src/views/manager.py`
1.  **Componentize**: `render_navigation` is very long and mixes layout with logic. Break it down into `_render_nav_buttons`, `_render_global_filters`, and `_render_context_filters`.
2.  **State Sync**: The logic for syncing `multi_side_selection` (List) and `analysis_side_pills` (Radio/Buttons) is scattered. Centralize the filter state management in `SessionStore` or a dedicated `FilterManager` class.
3.  **Safe Callbacks**: The lambda callbacks in loops (e.g., `on_layer_click`) are correctly defined, but using `functools.partial` is often cleaner and less error-prone than nested closures.

### `src/views/multi_layer.py`
1.  **Filter Logic Duplication**: The filtering logic (Layer, Side, Verification) is repeated here. Use a shared `apply_standard_filters(df, store)` function (in `utils` or `calculations`) to ensure consistency across all views.
2.  **Performance**: `prepare_multi_layer_data` creates a large concatenated DataFrame. Ensure this is cached (it is), but consider caching the *filtered* view if the user toggles visual settings (like flip back side) frequently.
3.  **UI Feedback**: The `st.info` and header are commented out. Use `st.caption` or a help tooltip on the chart to explain what "Multi-Layer" means to the user without cluttering the UI.

### `src/views/still_alive.py`
1.  **Vectorize Zonal Yield**: The nested loops (`for r in range... for c in range...`) to calculate Zonal Yield are O(N*M). Use NumPy array masking (e.g., `dist_x = np.minimum(...)`) to calculate rings and yield stats instantly for the whole grid.
2.  **Remove Empty Functions**: `render_still_alive_sidebar` is empty and unused. Remove it to clean up the code.
3.  **Download Logic**: The "Pick List" download generates a CSV on every render. Move this generation inside the `if st.download_button` callback (requires Streamlit pattern adjustment or generating lazily) or cache the CSV string.
