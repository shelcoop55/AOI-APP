# Final Improvements Report

This report outlines 5 *additional* improvements for each Python file in the codebase, building upon the recent refactoring.

## Root

### `app.py`
1.  **Strict Type Checking**: Add strict type annotations to `on_run_analysis` and `on_reset` callbacks if extracted, or ensure `mypy` is run in CI/CD.
2.  **Error Boundary**: Wrap the `main()` execution in a try-except block to catch unhandled exceptions and display a user-friendly error message using `st.error` instead of a raw traceback.
3.  **Config Loading**: Move the hardcoded `DEFAULT_THEME` instantiation to a configuration loader function that can optionally read from a `config.toml` or `secrets.toml` file.
4.  **Logging**: Initialize a structured logger (e.g., using `loguru` or standard `logging`) at the start of `main` to capture user actions and errors to a file.
5.  **Session State Validation**: Add a validation step at the start of `main` to ensure `st.session_state` has all required keys (using `SessionStore`), recovering gracefully if state is corrupted (e.g., on browser refresh).

## `src` Directory

### `src/config.py`
1.  **Environment Variables**: Allow overriding physical constants (like `FRAME_WIDTH`) via environment variables for easier deployment configuration without code changes.
2.  **Immutable Data Structures**: Convert `PanelConfig` to use `frozen=True` to prevent accidental modification of configuration during runtime.
3.  **Theme Validation**: Add a `validate()` method to `PlotTheme` to ensure color strings are valid hex codes or named colors.
4.  **Serialization**: Add `to_dict()` and `from_dict()` methods to `PlotTheme` to allow saving/loading user-customized themes to/from disk.
5.  **Asset Path Handling**: Use `pathlib` more robustly for `load_defect_styles` to handle different working directories (e.g., running tests vs running app).

### `src/data_handler.py`
1.  **Parquet Support**: Add support for saving/loading intermediate data as Parquet files. This is much faster than Excel and preserves data types better.
2.  **Input Validation Schema**: Use a library like `pandera` to validate the schema of uploaded Excel files (column names, types) and provide detailed error reports to the user.
3.  **Async Loading**: Experiment with `asyncio` for file reading if moving to a server-based architecture (though Streamlit is synchronous, it can benefit from thread pools for I/O).
4.  **Progress Bar Granularity**: In `load_data`, break down the progress bar updates more finely (e.g., per file) instead of a single spinner.
5.  **Memory Mapping**: For extremely large datasets, investigate using `mmap` or `dask` (via `pandas` chunking) to handle data larger than RAM.

### `src/models.py`
1.  **Slots**: Add `__slots__` to `BuildUpLayer` and `PanelData` to reduce memory overhead for these frequently instantiated objects.
2.  **Abstract Base Class**: Define an abstract `Layer` class if future support for different layer types (e.g., Core vs BuildUp) is needed.
3.  **Serialization**: Implement `__getstate__` and `__setstate__` to optimize pickling of `PanelData` if caching to disk (Streamlit cache uses pickle).
4.  **Dirty Flags**: Implement a "dirty" flag system to track if data has been modified, avoiding re-calculation of derived metrics if nothing changed.
5.  **Unit Tests**: Add dedicated unit tests for the coordinate transformation logic inside `BuildUpLayer` to ensure edge cases (e.g., points exactly on the boundary) are handled correctly.

### `src/state.py`
1.  **Observer Pattern**: Implement a mechanism to notify listeners when a specific state key changes (e.g., to trigger a specific chart update).
2.  **State Versioning**: Add a version key to `AppState`. If the schema changes in the future, migrate old state automatically.
3.  **Deep Copy**: Ensure setters for mutable objects (lists, dicts) perform a copy to prevent accidental mutation of the internal state from outside.
4.  **Persistence**: Add a method to save/load specific parts of the session state (e.g., user preferences) to `st.session_state` or local storage (using a custom component).
5.  **Generic Type Support**: Use `Generic` types for `SessionStore` if we plan to support different "Modes" of the application with different state requirements.

### `src/utils.py`
1.  **Path Sanitization**: In `generate_standard_filename`, add stricter sanitization to prevent directory traversal attacks if filenames are used in file system operations.
2.  **Unit Testing Regex**: Add comprehensive test cases for the regex patterns, covering edge cases like filenames with multiple hyphens or unusual spacing.
3.  **Custom CSS Loader**: Extend `load_css` to support templating (e.g., Jinja2) to dynamically inject colors from the active `PlotTheme` into the CSS.
4.  **Retry Logic**: Add a retry decorator for file operations (like reading CSS or assets) to handle transient file system locks.
5.  **Logging**: Add debug logging to `get_bu_name_from_filename` to trace which regex matched for a given input.

### `src/enums.py`
1.  **Display Names**: Add a `display_name` property to Enums (e.g., "Heatmap Analysis" vs "HEATMAP") to separate internal logic from UI presentation.
2.  **Iteration Helper**: Add a `list_ui_options()` class method that returns a list of tuples `(name, value)` for easier use in `st.selectbox`.
3.  **StrEnum**: Inherit from `StrEnum` (Python 3.11+) or `str` and `Enum` to make Enums JSON serializable by default.
4.  **Lookup**: Add a `from_display_name` method to easily lookup Enum members from user-facing strings.
5.  **Grouping**: Group views by category (e.g., `ViewCategory.ANALYSIS`, `ViewCategory.REPORTING`) to support hierarchical menus.

### `src/plotting.py`
1.  **WebGL Context Loss**: Handle WebGL context loss gracefully (frontend issue, but we can limit the number of `Scattergl` traces further or provide a fallback to SVG for small datasets).
2.  **Custom Color Scales**: Allow users to define custom continuous color scales for heatmaps in the UI, passing them to the plotting functions.
3.  **Annotation Overlap**: Implement a logic to detect and resolve overlapping text annotations in `create_density_contour_map`.
4.  **Figure Serialization**: Add a helper to serialize figures to JSON for potential "Save Chart" functionality in the UI (outside of the report zip).
5.  **Theme Injection**: Make `apply_panel_theme` stricter; raise a warning if a required theme attribute is missing instead of silently falling back.

### `src/reporting.py`
1.  **Template Engine**: Use a templating engine (like `jinja2` for HTML or `openpyxl` templates for Excel) to separate report design from data population logic.
2.  **Asynchronous Generation**: For very large reports, run the generation in a background thread and use a placeholder in Streamlit to show progress, avoiding UI freeze.
3.  **PDF Support**: Add an option to export the summary report as a PDF using a library like `weasyprint` or converting HTML.
4.  **Metadata Sheet**: Add a dedicated sheet logging the exact version of the code, timestamp, and user who generated the report for audit trails.
5.  **Memory Profiling**: Add logging of memory usage during report generation to identify potential leaks in the image generation loop.

### `src/documentation.py`
1.  **Markdown Rendering**: Use a library like `mistune` or `markdown` to validate the syntax of `docs.md` during loading to prevent broken rendering.
2.  **Search Functionality**: Implement a simple search bar in the Documentation view to filter the markdown content.
3.  **Section Linking**: Parse the markdown headers to create a dynamic Table of Contents sidebar for easy navigation.
4.  **Asset Verification**: Ensure images referenced in the markdown (if any) actually exist in the assets folder.
5.  **Version Display**: Display the documentation version or last updated date (read from file metadata).

## `src/views` Directory

### `src/views/manager.py`
1.  **Route Guarding**: Implement a check to ensure `self.store.layer_data` exists before rendering *any* view (except the upload screen), redirecting if necessary.
2.  **Dynamic Modules**: Load view modules lazily using `importlib` only when requested, to reduce initial startup time.
3.  **Error Feedback**: Display a visual indicator (toast) when analysis settings are updated (e.g., "Filters Applied").
4.  **Keyboard Shortcuts**: Expand `keyboard_shortcuts.html` to support more actions (e.g., switching tabs) and document them in the UI.
5.  **URL Query Params**: Sync the active view and key filters with `st.query_params` so users can share links to specific analysis states.

### `src/views/layer_view.py`
1.  **Virtualization**: If the defect list table grows very large, ensure `st.dataframe` virtualization is enabled and working (it is by default, but verify config).
2.  **Diff View**: Add a "Compare to Previous Layer" toggle to visually overlay the previous layer's defects in ghost mode.
3.  **Selection Sync**: Allow selecting a defect in the table to highlight it in the plot (requires bidirectional Streamlit component or `st.plotly_chart(on_select=...)` handling).
4.  **Export CSV**: Add a direct "Download CSV" button for the currently filtered view data.
5.  **Metric Delta**: Calculate and show the delta of KPIs compared to the *average* of all layers.

### `src/views/multi_layer.py`
1.  **3D Visualization**: Experiment with `go.Scatter3d` to show the stack of layers in 3D space for true "Multi-Layer" visualization.
2.  **Opacity Slider**: Add a slider to control the opacity of layers to see "through" the board better.
3.  **Layer Reordering**: Allow users to reorder the Z-index of layers (which draws on top) via the UI.
4.  **Intersection Analysis**: Highlight X,Y coordinates where defects exist on *multiple* layers (vertical stack).
5.  **Custom Tooltip**: Allow users to customize which fields are shown in the hover tooltip.

### `src/views/still_alive.py`
1.  **Interactive Ring Config**: Allow users to define the "Ring" sizes (Edge vs Center) via a slider instead of hardcoded logic.
2.  **Yield Trend**: If `Lot Number` implies a sequence, show a trend line of yield across lots (if multiple files/lots were loaded).
3.  **Heatmap Overlay**: Allow toggling a density heatmap underneath the binary Good/Bad map.
4.  **Click-to-Filter**: Clicking a "Dead" cell should filter the "Layer View" to show the killer defect for that specific unit.
5.  **Advanced Metrics**: Calculate "Cluster Factor" – are dead cells clumped together or random? (Nearest Neighbor analysis).

## `src/analysis` Directory

### `src/analysis/base.py`
1.  **Protocol Definition**: Define a strict `Protocol` for what `AnalysisTool` expects from `SessionStore` to decouple them further.
2.  **Async Methods**: Add async support to `render_main` if we move to async data fetching.
3.  **Configuration Schema**: Add a `get_config_schema()` method to tools so they can define their own settings requirements.
4.  **Help Text**: Add a `get_help_text()` method that returns markdown documentation specific to that tool.
5.  **State Scope**: Enforce that tools can only modify their own slice of the session state (namespaced).

### `src/analysis/calculations.py`
1.  **Numba JIT**: Decorate heavy numerical loops (like histogramming or distance calcs) with `@numba.jit` for C-like performance.
2.  **Parallelism**: Use `joblib` or `ProcessPoolExecutor` for calculations that CPU-bound and independent (e.g., processing layers in parallel).
3.  **Unit Tests**: Add property-based testing (using `hypothesis`) to ensure calculations hold for edge cases (empty data, all defects, etc.).
4.  **Result Caching**: Implement an LRU cache with size limit for `get_filtered_heatmap_data` to prevent memory bloat over time.
5.  **Input Hashing**: Improve the stability of the cache key by creating a deterministic hash of the *content* of the input dataframes, not just the object ID.

### `src/analysis/heatmap.py`
1.  **Dynamic Binning**: Automatically adjust the bin size based on the zoom level (requires frontend callback info).
2.  **Colorscale Editor**: Add a widget to let users adjust the min/max range of the colorscale manually.
3.  **Export Data**: Button to download the underlying grid matrix as a CSV/Excel file.
4.  **Statistical Significance**: Highlight "Hotspots" that are statistically significant (e.g., > 3 sigma above mean).
5.  **Compare Mode**: Side-by-side comparison of two heatmaps (e.g., Filter A vs Filter B).

### `src/analysis/stress.py`
1.  **Threshold Filtering**: Allow users to hide cells with defect counts below a certain threshold.
2.  **Normalization**: Add an option to view "Defects per Area" (normalized) vs raw counts.
3.  **Annotation Toggle**: Allow toggling text labels on/off entirely for cleaner view.
4.  **Correlation**: Calculate correlation coefficient between Front and Back stress maps.
5.  **Save View**: Button to save the current stress map configuration as a "Preset".

### `src/analysis/root_cause.py`
1.  **Interactive Slicing**: Instead of a slider, allow clicking on the main heatmap to select the slice X/Y.
2.  **Layer Aggregation**: Option to group layers (e.g., "Core" vs "BuildUp") in the Y-axis of the cross-section.
3.  **Defect Type Color**: Color the cross-section cells by the *dominant* defect type, not just count.
4.  **Pareto Integration**: Show a mini Pareto chart for the selected slice.
5.  **3D Stack**: (Advanced) Render a 3D voxel view of the defect stack.

### `src/analysis/insights.py`
1.  **Trend Analysis**: If data allows, show defects over "Layer Number" as a trend line.
2.  **False Alarm Impact**: Calculate "Potential Yield Gain" if False Alarms were eliminated.
3.  **Interactive Drilling**: Clicking a sector in Sunburst filters the main Defect Map.
4.  **Sankey Ordering**: Allow users to sort Sankey nodes by Count, Name, or Custom order.
5.  **Data Quality Score**: Display a score based on how much verification data is missing vs present.
