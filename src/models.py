"""
Domain Models for Panel Defect Analysis.
Encapsulates logic for Build-Up Layers, Coordinate Transformations, and Defect Data.
"""
from dataclasses import dataclass
import pandas as pd
import numpy as np
import uuid
from typing import Dict, List, Optional
from src.layout import LayoutParams

@dataclass
class BuildUpLayer:
    """
    Represents a single side (Front/Back) of a specific Build-Up Layer.
    Encapsulates raw data and handles coordinate transformations.
    """
    layer_num: int
    side: str  # 'F' or 'B'
    raw_df: pd.DataFrame
    layout: LayoutParams

    def __post_init__(self):
        self._validate()
        self._add_plotting_coordinates()

    def _validate(self):
        if self.side not in ['F', 'B']:
            raise ValueError(f"Invalid side '{self.side}'. Must be 'F' or 'B'.")
        if self.raw_df.empty:
            return

    @property
    def is_front(self) -> bool:
        return self.side == 'F'

    @property
    def is_back(self) -> bool:
        return self.side == 'B'

    @property
    def label(self) -> str:
        side_name = "Front" if self.is_front else "Back"
        return f"Layer {self.layer_num} ({side_name})"

    @property
    def data(self) -> pd.DataFrame:
        """Returns the dataframe with both Raw and Physical plotting coordinates."""
        return self.raw_df

    def _add_plotting_coordinates(self):
        """
        Calculates plot coordinates using LayoutParams.
        """
        if self.raw_df.empty:
            return

        df = self.raw_df
        layout = self.layout

        # --- 1. COORDINATE CALCULATION USING LAYOUT LOGIC ---

        # Determine Quadrant
        # Note: Layout logic assumes cols 0..N-1 are Q1/Q3, N..2N-1 are Q2/Q4.
        conditions = [
            (df['UNIT_INDEX_X'] < layout.panel_cols) & (df['UNIT_INDEX_Y'] < layout.panel_rows), # Q1
            (df['UNIT_INDEX_X'] >= layout.panel_cols) & (df['UNIT_INDEX_Y'] < layout.panel_rows), # Q2
            (df['UNIT_INDEX_X'] < layout.panel_cols) & (df['UNIT_INDEX_Y'] >= layout.panel_rows), # Q3
            (df['UNIT_INDEX_X'] >= layout.panel_cols) & (df['UNIT_INDEX_Y'] >= layout.panel_rows) # Q4
        ]
        choices = ['Q1', 'Q2', 'Q3', 'Q4']
        df['QUADRANT'] = np.select(conditions, choices, default='Other')

        # Calculate Origin (Bottom-Left) for every unit
        # Vectorized implementation of layout.get_unit_origin

        # X Origin
        # If col < panel_cols: start = margin_x
        # Else: start = margin_x + quad_w + gap_mid
        # final = start + (local_col * unit_w) + (local_col * gap_unit)

        local_col = df['UNIT_INDEX_X'] % layout.panel_cols
        x_start = np.where(df['UNIT_INDEX_X'] < layout.panel_cols,
                           layout.margin_x,
                           layout.margin_x + layout.quad_width + layout.gap_mid)

        base_x = x_start + (local_col * layout.unit_width) + (local_col * layout.gap_unit)

        # Y Origin
        local_row = df['UNIT_INDEX_Y'] % layout.panel_rows
        y_start = np.where(df['UNIT_INDEX_Y'] < layout.panel_rows,
                           layout.margin_y,
                           layout.margin_y + layout.quad_height + layout.gap_mid)

        base_y = y_start + (local_row * layout.unit_height) + (local_row * layout.gap_unit)

        # --- SPATIAL LOGIC (ABSOLUTE MAPPING) ---
        use_spatial_coords = False
        offset_x = 0.0
        offset_y = 0.0

        if 'X_COORDINATES' in df.columns and 'Y_COORDINATES' in df.columns:
            try:
                # Convert um to mm
                abs_x_mm = df['X_COORDINATES'] / 1000.0
                abs_y_mm = df['Y_COORDINATES'] / 1000.0

                if pd.api.types.is_numeric_dtype(abs_x_mm) and pd.api.types.is_numeric_dtype(abs_y_mm):
                    use_spatial_coords = True
                    # Treat raw coords as offset from Unit Origin
                    offset_x = abs_x_mm
                    offset_y = abs_y_mm
            except Exception:
                use_spatial_coords = False

        if not use_spatial_coords:
            # Jitter: Random within Unit Size (0.1 to 0.9)
            # Relative to Unit Origin (base_x/y)
            jitter_x = np.random.rand(len(df)) * layout.unit_width * 0.8 + (layout.unit_width * 0.1)
            jitter_y = np.random.rand(len(df)) * layout.unit_height * 0.8 + (layout.unit_height * 0.1)

            df['plot_x'] = base_x + jitter_x
            df['plot_y'] = base_y + jitter_y
        else:
            # Spatial Mode: Coordinates are GLOBAL (0 to Max Active Width).
            # We must NOT add 'base_x' (Unit Origin).
            # Instead, we apply global Margins and Gaps (Visual Layout).

            # 1. Apply Margins (Offset from Canvas Origin)
            abs_x = offset_x + layout.margin_x
            abs_y = offset_y + layout.margin_y

            # 2. Inject Gap
            # If unit is in Right Quadrants (Q2/Q4), shift by Gap Size.
            # We rely on UNIT_INDEX to determine quadrant consistently.
            gap_shift_x = np.where(df['QUADRANT'].isin(['Q2', 'Q4']), layout.gap_mid, 0)
            gap_shift_y = np.where(df['QUADRANT'].isin(['Q3', 'Q4']), layout.gap_mid, 0)

            df['plot_x'] = abs_x + gap_shift_x
            df['plot_y'] = abs_y + gap_shift_y

        # --- 2. PHYSICAL COORDINATES (Stacked View) ---
        # For simplicity in this iteration, we map Flipped/Raw similarly but flip the index.

        # Raw (No Flip)
        df['PHYSICAL_X_RAW'] = df['UNIT_INDEX_X']
        df['physical_plot_x_raw'] = df['plot_x'] # Same as main view

        # Flipped
        if self.is_back:
            total_cols = layout.panel_cols * 2
            df['PHYSICAL_X_FLIPPED'] = (total_cols - 1) - df['UNIT_INDEX_X']

            # Recalculate Base X for Flipped Index
            local_col_flip = df['PHYSICAL_X_FLIPPED'] % layout.panel_cols
            x_start_flip = np.where(df['PHYSICAL_X_FLIPPED'] < layout.panel_cols,
                                    layout.margin_x,
                                    layout.margin_x + layout.quad_width + layout.gap_mid)
            base_x_flip = x_start_flip + (local_col_flip * layout.unit_width) + (local_col_flip * layout.gap_unit)

            # Add Centering (Width/2) instead of specific spatial coord to avoid flipping errors
            df['physical_plot_x_flipped'] = base_x_flip + (layout.unit_width / 2)
        else:
            df['PHYSICAL_X_FLIPPED'] = df['UNIT_INDEX_X']
            df['physical_plot_x_flipped'] = df['plot_x']


class PanelData:
    """
    Container for the entire panel's data.
    Replaces Dict[int, Dict[str, DataFrame]].
    """
    def __init__(self):
        # Internal storage: layer_num -> side -> BuildUpLayer
        self._layers: Dict[int, Dict[str, BuildUpLayer]] = {}
        # Unique ID for caching/hashing purposes
        self.id = uuid.uuid4().hex

    def add_layer(self, layer: BuildUpLayer):
        if layer.layer_num not in self._layers:
            self._layers[layer.layer_num] = {}
        self._layers[layer.layer_num][layer.side] = layer

    def get_layer(self, layer_num: int, side: str) -> Optional[BuildUpLayer]:
        return self._layers.get(layer_num, {}).get(side)

    def get_all_layer_nums(self) -> List[int]:
        return sorted(self._layers.keys())

    def get_sides_for_layer(self, layer_num: int) -> List[str]:
        return sorted(self._layers.get(layer_num, {}).keys())

    def get_combined_dataframe(self, filter_func=None) -> pd.DataFrame:
        """Returns a concatenated DataFrame of all layers."""
        dfs = []
        for layer_num in self._layers:
            for side in self._layers[layer_num]:
                layer = self._layers[layer_num][side]
                df = layer.data.copy()
                # Add Metadata
                df['LAYER_NUM'] = layer_num
                df['SIDE'] = side
                df['Layer_Label'] = layer.label

                if filter_func:
                    df = filter_func(df)

                if not df.empty:
                    dfs.append(df)

        if not dfs:
            return pd.DataFrame()
        return pd.concat(dfs, ignore_index=True)

    def __bool__(self):
        return bool(self._layers)

    def __len__(self):
        return len(self._layers)

    # --- Compatibility Interface (mimics Dict behaviour for easier migration) ---
    def __iter__(self):
        return iter(self._layers)

    def keys(self):
        return self._layers.keys()

    def items(self):
        return self._layers.items()

    def values(self):
        return self._layers.values()

    def __getitem__(self, key):
        # Returns the inner dict {side: BuildUpLayer}
        # Ideally we refactor consumers to not need this, but for now:
        # Consumers expect Dict[str, DataFrame].
        # We need to return a proxy that behaves like { 'F': df, 'B': df }
        # This is a bit hacky but allows gradual refactor.

        inner = self._layers[key]
        return {side: layer_obj.data for side, layer_obj in inner.items()}

    def __contains__(self, key):
        return key in self._layers

    def get(self, key, default=None):
        if key in self._layers:
            return self[key] # Use the __getitem__ proxy logic
        return default
