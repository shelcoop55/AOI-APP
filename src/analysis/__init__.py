from typing import Dict, Type
from src.enums import ViewMode
from src.analysis.base import AnalysisTool
from src.analysis.heatmap import HeatmapTool
from src.analysis.stress import StressMapTool
from src.analysis.root_cause import RootCauseTool
from src.analysis.insights import InsightsTool
from src.state import SessionStore

# Registry mapping ViewMode enum values to Strategy Classes
TOOL_REGISTRY: Dict[str, Type[AnalysisTool]] = {
    ViewMode.HEATMAP.value: HeatmapTool,
    ViewMode.STRESS.value: StressMapTool,
    ViewMode.ROOT_CAUSE.value: RootCauseTool,
    ViewMode.INSIGHTS.value: InsightsTool
}

def get_analysis_tool(mode_value: str, store: SessionStore) -> AnalysisTool:
    """Factory to instantiate the correct tool strategy."""
    tool_class = TOOL_REGISTRY.get(mode_value, HeatmapTool)
    return tool_class(store)
