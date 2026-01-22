# Panel Defect Analysis Dashboard

**Version 2.0 | Advanced Semiconductor Manufacturing Analytics**

![Status](https://img.shields.io/badge/Status-Active-success)
![Python](https://img.shields.io/badge/Python-3.12-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.40%2B-FF4B4B)

A professional, high-performance interactive web application built with Streamlit for visualizing and analyzing semiconductor panel defect data. Designed for engineers and technicians, this dashboard enables multi-layer build-up analysis, spatial defect mapping, and automated yield reporting.

![App Screenshot](assets/screenshot.png)

---

## 🚀 Key Features

### 1. Multi-Layer & Multi-Side Analysis
- **Build-Up (BU) Support**: Upload and analyze data from multiple layers simultaneously (e.g., `BU-01`, `BU-02`).
- **Front & Back Side Alignment**: Automatically handles Front/Back side flipping and alignment for true-to-physical spatial stacking.
- **Robust Data Ingestion**: Intelligently normalizes column names (e.g., `Verification`, `DEFECT_TYPE`) to handle inconsistencies in input files.

### 2. Advanced Visualization
- **Interactive Defect Map**: Zoomable, pan-able Plotly maps representing the true physical scale of the panel.
- **"Still Alive" Yield Map**: A powerful yield aggregation view that identifies "killer" defects across all layers to pinpoint units that remain defect-free.
- **Heatmaps & Stress Maps**: Visualize defect density hotspots and mechanical stress points across the panel surface.

### 3. Intelligent Filtering & Controls
- **Global Verification Filters**: Filter defects by verification status (e.g., `True`, `False`, `Acceptable`) with a global scope that persists across layer views.
- **Smart Defaults**: Automatically detects available data and pre-selects all options, ensuring you never start with an empty view.
- **Quadrant Focusing**: Isolate specific panel quadrants (Q1-Q4) for detailed inspection.

### 4. Reporting & Metrics
- **Automated Reporting**: Generate presentation-ready Excel packages containing summary statistics, raw data, and embedded charts.
- **Pareto Analysis**: Dynamic Pareto charts to identify top defect contributors.
- **KPI Dashboard**: Real-time calculation of Defect Density, Yield Loss, and Kill Ratios.

---

## 🛠️ Installation & Setup

### Prerequisites
- **Python 3.12+** (Managed via `pyenv` recommended)
- **Git**

### Step-by-Step Guide

1.  **Clone the Repository**
    ```bash
    git clone <your-repo-url>
    cd panel-defect-analysis
    ```

2.  **Set Up Python Environment**
    ```bash
    # Install specific python version
    pyenv install 3.12.12
    pyenv local 3.12.12
    ```

3.  **Install Dependencies**
    It is recommended to use a virtual environment.
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate

    # Install Core Dependencies
    pip install -r requirements.txt

    # Install Dev/Test Dependencies (Optional)
    pip install -r requirements-dev.txt
    ```

4.  **Launch the Application**
    ```bash
    streamlit run app.py
    ```
    The app will open automatically in your browser at `http://localhost:8501`.

---

## 📖 Usage Guide

### 1. Data Preparation
Your Excel files should follow this naming convention:
- **Format**: `BU-XX[F|B]*.xlsx` (e.g., `BU-01F_Lot123.xlsx`, `BU-02B.xlsx`)
- **Sheet**: Must contain a sheet named `Defects`.
- **Columns**:
  - `DEFECT_TYPE` (String)
  - `UNIT_INDEX_X` (Integer)
  - `UNIT_INDEX_Y` (Integer)
  - `Verification` (String, Optional) - *Note: The app robustly handles variations like "VERIFICATION", "Verification ", etc.*

### 2. Running Analysis
1.  **Upload**: Use the sidebar **"Data Source & Configuration"** to upload one or multiple BU layer files.
2.  **Configure**: Set the `Panel Rows` and `Panel Columns` to match your product's grid.
3.  **Run**: Click **🚀 Run Analysis**. The dashboard will load with the highest layer selected by default.

### 3. Navigation
- **Layer Inspection**: View defects for a specific single layer. Toggle between "Front" and "Back" sides.
- **Analysis Page**: Access advanced tools like Heatmaps, Stress Maps, and Root Cause Analysis.
- **Still Alive**: View the cumulative yield map.

### 4. Exporting Results
- Navigate to the **Reporting** tab via the top navigation bar.
- Choose your export options (Excel Report, PNG Maps, Coordinate Lists).
- Click **📦 Generate Download Package** to get a ZIP file with all assets.

---

## ⚙️ Configuration

### Customizing Defect Colors
Map specific defect types to custom colors by editing `assets/defect_styles.json`.
```json
{
    "Nick": "#9B59B6",
    "Short": "#E74C3C",
    "Open": "#3498DB"
}
```
*Any defect type not listed will receive a color from the auto-generated palette.*

### Advanced Plot Settings
In the **Advanced Configuration** sidebar expander:
- **Plot Origin**: Shift the (0,0) visual origin.
- **Dynamic Gaps**: Adjust the visual spacing between quadrants for better clarity.

---

## 🏗️ Project Structure

The project follows a modular architecture for scalability and maintenance.

```
├── app.py                 # Main Streamlit Entry Point
├── src/
│   ├── config.py          # Global constants and theme settings
│   ├── state.py           # Centralized SessionState management
│   ├── data_handler.py    # Data ingestion, cleaning, and normalization
│   ├── plotting.py        # Plotly visualization logic
│   ├── reporting.py       # Excel/ZIP report generation
│   ├── analysis/          # Advanced analysis logic (Heatmaps, Stress)
│   ├── views/             # UI View Components (Layer View, Dashboard)
│   └── models.py          # Data classes (PanelData, BuildUpLayer)
├── assets/
│   └── defect_styles.json # Color configuration
├── tests/                 # Pytest suite
└── requirements.txt       # Dependencies
```

---

## 🧪 Testing

We use `pytest` for robust unit and integration testing.

```bash
# Run all tests
pytest

# Run a specific test file
pytest tests/test_data_handler.py
```

---

## 🤝 Contributing

1.  Create a feature branch (`git checkout -b feature/amazing-feature`).
2.  Commit your changes.
3.  Run tests to ensure no regressions.
4.  Push to the branch and open a Pull Request.

---

**Developed for Semiconductor Excellence.**
