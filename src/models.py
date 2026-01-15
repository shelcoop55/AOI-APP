"""
Domain Models for Panel Defect Analysis.
Encapsulates logic for Build-Up Layers, Coordinate Transformations, and Defect Data.
"""
from dataclasses import dataclass
import pandas as pd
import numpy as np
import uuid
from typing import Dict, List, Optional
from src.config import PANEL_WIDTH, PANEL_HEIGHT, GAP_SIZE, QUADRANT_WIDTH, QUADRANT_HEIGHT

@dataclass
class BuildUpLayer:
    """
    Represents a single side (Front/Back) of a specific Build-Up Layer.
    Encapsulates raw data and handles coordinate transformations.
    """
    layer_num: int
    side: str  # 'F' or 'B'
    raw_df: pd.DataFrame
    panel_rows: int
    panel_cols: int

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
        Internal method to calculate and append 'plot_x', 'plot_y', and 'physical_plot_x'
        to the internal DataFrame.
        """
        if self.raw_df.empty:
            return

        df = self.raw_df
        cell_width = QUADRANT_WIDTH / self.panel_cols
        cell_height = QUADRANT_HEIGHT / self.panel_rows

        # --- 1. RAW COORDINATES (Individual View - No Flip) ---
        # Calculate Raw Quadrant
        conditions_raw = [
            (df['UNIT_INDEX_X'] < self.panel_cols) & (df['UNIT_INDEX_Y'] < self.panel_rows),
            (df['UNIT_INDEX_X'] >= self.panel_cols) & (df['UNIT_INDEX_Y'] < self.panel_rows),
            (df['UNIT_INDEX_X'] < self.panel_cols) & (df['UNIT_INDEX_Y'] >= self.panel_rows),
            (df['UNIT_INDEX_X'] >= self.panel_cols) & (df['UNIT_INDEX_Y'] >= self.panel_rows)
        ]
        choices = ['Q1', 'Q2', 'Q3', 'Q4']
        df['QUADRANT'] = np.select(conditions_raw, choices, default='Other')

        local_index_x_raw = df['UNIT_INDEX_X'] % self.panel_cols
        local_index_y = df['UNIT_INDEX_Y'] % self.panel_rows

        plot_x_base_raw = local_index_x_raw * cell_width
        plot_y_base = local_index_y * cell_height

        x_offset_raw = np.where(df['UNIT_INDEX_X'] >= self.panel_cols, QUADRANT_WIDTH + GAP_SIZE, 0)
        y_offset = np.where(df['UNIT_INDEX_Y'] >= self.panel_rows, QUADRANT_HEIGHT + GAP_SIZE, 0)

        # Jitter
        jitter_x = np.random.rand(len(df)) * cell_width * 0.8 + (cell_width * 0.1)
        jitter_y = np.random.rand(len(df)) * cell_height * 0.8 + (cell_height * 0.1)

        df['plot_x'] = plot_x_base_raw + x_offset_raw + jitter_x
        df['plot_y'] = plot_y_base + y_offset + jitter_y

        # --- 2. PHYSICAL COORDINATES (Stacked View - Flip Back Side) ---
        # Logic: If Side is Back, Flip X Index.
        # Physical X = (Total_Cols - 1) - Raw_X

        total_width_units = 2 * self.panel_cols

        if self.is_back:
            df['PHYSICAL_X'] = (total_width_units - 1) - df['UNIT_INDEX_X']
        else:
            df['PHYSICAL_X'] = df['UNIT_INDEX_X']

        # Calculate Physical Plotting Coordinates
        local_index_x_phys = df['PHYSICAL_X'] % self.panel_cols
        plot_x_base_phys = local_index_x_phys * cell_width
        x_offset_phys = np.where(df['PHYSICAL_X'] >= self.panel_cols, QUADRANT_WIDTH + GAP_SIZE, 0)

        # Reuse jitter for visual consistency across views
        df['physical_plot_x'] = plot_x_base_phys + x_offset_phys + jitter_x


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
