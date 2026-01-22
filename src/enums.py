"""
Enum Definitions Module.

This module contains Enumeration classes for defining constant sets of values,
such as UI view modes or quadrant identifiers. Using enums instead of raw strings
improves code readability and reduces the risk of typos.
"""
from enum import Enum

class ViewMode(Enum):
    """Enumeration for the different analysis views in the UI."""
    DEFECT = "Defect View"
    HEATMAP = "Heatmap Analysis"
    STRESS = "Stress Map Analysis"
    PARETO = "Pareto View"
    SUMMARY = "Summary View"
    INSIGHTS = "Insights View"
    ROOT_CAUSE = "Root Cause Analysis"
    STILL_ALIVE = "Still Alive"
    MULTI_LAYER = "Multi-Layer"
    DOCUMENTATION = "Documentation"
    REPORTING = "Reporting"

    @classmethod
    def values(cls) -> list[str]:
        """Returns the string values of all enum members."""
        return [item.value for item in cls]

    def is_analysis(self) -> bool:
        """Returns True if the view is considered an 'Analysis' subview."""
        return self in [ViewMode.HEATMAP, ViewMode.STRESS, ViewMode.ROOT_CAUSE, ViewMode.INSIGHTS, ViewMode.STILL_ALIVE, ViewMode.MULTI_LAYER]

class Quadrant(Enum):
    """Enumeration for the panel quadrants."""
    ALL = "All"
    Q1 = "Q1"
    Q2 = "Q2"
    Q3 = "Q3"
    Q4 = "Q4"

    @classmethod
    def values(cls) -> list[str]:
        """Returns the string values of all enum members."""
        return [item.value for item in cls]

    @property
    def index(self) -> int:
        """Returns a 0-based index for the quadrant (Q1=0, Q2=1, Q3=2, Q4=3). Returns -1 for ALL."""
        if self == Quadrant.Q1: return 0
        if self == Quadrant.Q2: return 1
        if self == Quadrant.Q3: return 2
        if self == Quadrant.Q4: return 3
        return -1
