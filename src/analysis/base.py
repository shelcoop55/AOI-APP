from abc import ABC, abstractmethod
import streamlit as st
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.state import SessionStore

class AnalysisTool(ABC):
    """
    Abstract Base Class for an Analysis Tool Strategy.
    Encapsulates the Sidebar controls and Main Area rendering for a specific analysis mode.
    """

    def __init__(self, store: "SessionStore"):
        self.store = store

    @property
    @abstractmethod
    def name(self) -> str:
        """The display name of the tool."""
        pass

    @abstractmethod
    def render_sidebar(self):
        """Renders controls specific to this tool in the sidebar."""
        pass

    @abstractmethod
    def render_main(self):
        """Renders the main visualization/content."""
        pass

    def teardown(self):
        """Optional hook to clean up resources when the tool is unloaded."""
        pass
