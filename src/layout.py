"""
Layout Logic Module.
Handles the calculation of unit coordinates based on the "Copper Grid" specification.
"""
from dataclasses import dataclass
from typing import Tuple

@dataclass
class LayoutParams:
    panel_cols: int
    panel_rows: int
    quad_width: float
    quad_height: float
    margin_x: float
    margin_y: float
    gap_mid: float
    gap_unit: float

    @property
    def unit_width(self) -> float:
        # Width = (Quad - (N-1)*Gap) / N
        if self.panel_cols <= 0: return 0.0
        return (self.quad_width - ((self.panel_cols - 1) * self.gap_unit)) / self.panel_cols

    @property
    def unit_height(self) -> float:
        if self.panel_rows <= 0: return 0.0
        return (self.quad_height - ((self.panel_rows - 1) * self.gap_unit)) / self.panel_rows

    def get_unit_origin(self, col_index: int, row_index: int) -> Tuple[float, float]:
        """
        Calculates the bottom-left coordinate (x, y) for a unit given its global index.
        """
        # 1. Determine Quadrant Offset
        # Columns 0 to (cols-1) are Left. Cols (cols) to (2*cols-1) are Right.
        if col_index < self.panel_cols:
            start_x = self.margin_x
            local_col = col_index
        else:
            start_x = self.margin_x + self.quad_width + self.gap_mid
            local_col = col_index - self.panel_cols

        if row_index < self.panel_rows:
            # Bottom Quadrants
            start_y = self.margin_y
            local_row = row_index
        else:
            # Top Quadrants
            start_y = self.margin_y + self.quad_height + self.gap_mid
            local_row = row_index - self.panel_rows

        # 2. Calculate Final Position
        # Start + (Units * Width) + (Gaps * GapWidth)
        final_x = start_x + (local_col * self.unit_width) + (local_col * self.gap_unit)
        final_y = start_y + (local_row * self.unit_height) + (local_row * self.gap_unit)

        return final_x, final_y

    def get_physical_extent(self) -> Tuple[float, float]:
        """Returns the total width and height of the visual area including margins."""
        # Width = Margin + Quad + Mid + Quad + Margin
        # Actually, standard visual extent implies the canvas size.
        # User specified Global Margins.
        # Right edge of Q2 = Margin + Quad + Mid + Quad.
        # Plus Right Margin? Usually yes for canvas size.
        total_w = self.margin_x + self.quad_width + self.gap_mid + self.quad_width + self.margin_x
        total_h = self.margin_y + self.quad_height + self.gap_mid + self.quad_height + self.margin_y
        return total_w, total_h
