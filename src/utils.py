import re

def get_bu_name_from_filename(filename: str) -> str:
    """
    Extracts the 'BU-XX' part from a filename.
    Returns the original filename if no match is found.
    """
    match = re.match(r"(BU-\d{2})", filename, re.IGNORECASE)
    if match:
        return match.group(1).upper()

    # Fallback for sample data
    match = re.match(r"Sample Data Layer (\d+)", filename)
    if match:
        return f"BU-{int(match.group(1)):02d}"

    return filename