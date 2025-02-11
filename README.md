# Data Visualization App

A Streamlit-based application for data visualization.

## Getting Started

### Prerequisites

- Python 3.11
- pip (Python package installer)

### Installation

1. Clone this repository:

```bash
git clone https://github.com/chrishonselaar/inzicht-ui-prototype
cd inzicht-ui-prototype
```

2.  Create and activate a virtual environment (optional but recommended):

```bash
python -m venv venv
source venv/bin/activate # On Windows use: venv\Scripts\activate
```

3. Install required dependencies:
```bash
pip install -r requirements.txt
```

4. Copy and rename .env.example to .env, fill in your API keys

## Running the Applications

This repository contains two Streamlit applications:

### 1. Statler Realtime Dashboard
For real-time data monitoring and visualization:
```bash
streamlit run src/statler_realtime/app.py
```

### 2. Waldorf Research Dashboard
For historical data analysis and research:
```bash
streamlit run src/waldorf_research/app.py
```

### Running in VS Code

If you're using Visual Studio Code, you can use the included launch configurations:

1. Open the project in VS Code
2. Go to the "Run and Debug" view (Ctrl+Shift+D)
3. Select either "Statler Realtime" or "Waldorf Research" from the dropdown menu
4. Click the play button or press F5

## Example Visualizations

Check out the `examples/`, `notebooks/` and `deep-research/` directory for sample visualization scripts and demonstrations of different chart types and data analysis techniques.

## System Architecture

![System Architecture Diagram](pitch/main-impact-diagram2.png)

The system processes data from multiple input sources:
- Municipal archives (30,000+ documents)
- Live meetings (Real-time data)
- Scientific publications
- News and social media
- Internal documents (Reports, permit applications)

Through intelligent knowledge tools including Waldorf/Statler, this data is transformed into three key outcomes:
- Better informed decision-making
- Stronger animal welfare advocacy
- More effective coalition building
