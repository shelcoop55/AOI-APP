import pytest
from unittest.mock import patch, mock_open
from src.utils import get_bu_name_from_filename, load_css

def test_get_bu_name_from_filename():
    """Tests the extraction of BU names from filenames."""

    # Standard format: BU-XX... (Assumes filename only, no path)
    assert get_bu_name_from_filename("BU-01F.xlsx") == "BU-01"
    assert get_bu_name_from_filename("BU-02B.xls") == "BU-02"

    # Sample data format: Sample Data Layer X...
    assert get_bu_name_from_filename("Sample Data Layer 1") == "BU-01"
    assert get_bu_name_from_filename("Sample Data Layer 2F") == "BU-02"
    assert get_bu_name_from_filename("Sample Data Layer 10B") == "BU-10"

    # Fallback behavior: Returns original filename if no match
    assert get_bu_name_from_filename("random_file.txt") == "random_file.txt"
    assert get_bu_name_from_filename("Layer 1 data") == "Layer 1 data"

@patch("src.utils.st")
def test_load_css(mock_st):
    """Tests that load_css reads the file and calls st.markdown."""

    # Mock file content
    mock_css_content = "body { color: red; }"

    with patch("builtins.open", mock_open(read_data=mock_css_content)) as mock_file:
        load_css("fake_path.css")

        # Verify file was opened
        mock_file.assert_called_once_with("fake_path.css")

        # Verify st.markdown was called
        mock_st.markdown.assert_called_once()

        # Check that the CSS content was injected (partially)
        args, _ = mock_st.markdown.call_args
        injected_style = args[0]
        assert mock_css_content in injected_style
        assert ":root {" in injected_style

@patch("src.utils.st")
def test_load_css_file_not_found(mock_st):
    """Tests that load_css handles FileNotFoundError silently."""

    with patch("builtins.open", side_effect=FileNotFoundError):
        load_css("non_existent_file.css")

        # Verify st.markdown was NOT called
        mock_st.markdown.assert_not_called()
