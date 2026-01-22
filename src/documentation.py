"""
Documentation and Defect Definitions Module.

This module contains:
1. The full technical documentation for ICS & Core Defects.
2. A dictionary mapping verification codes to short descriptions for UI tooltips.
"""
import streamlit as st
import json
from pathlib import Path
from typing import Dict

@st.cache_data
def load_verification_descriptions() -> Dict[str, str]:
    """Loads verification descriptions from JSON."""
    try:
        path = Path("assets/verification_descriptions.json")
        if path.exists():
            with open(path, "r") as f:
                return json.load(f)
        return {}
    except Exception:
        return {}

VERIFICATION_DESCRIPTIONS = load_verification_descriptions()

@st.cache_data
def load_technical_documentation() -> str:
    """Loads technical documentation from Markdown file."""
    try:
        path = Path("assets/docs.md")
        if path.exists():
            with open(path, "r") as f:
                return f.read()
        return "Documentation not found."
    except Exception:
        return "Error loading documentation."

def render_documentation():
    """Renders the technical documentation in the Streamlit app."""
    doc_text = load_technical_documentation()
    st.markdown(doc_text)
