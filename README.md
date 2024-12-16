# Oil and Gas Production Analytics Workflow

## Overview
The **Oil and Gas Production Analytics Workflow** is an end-to-end Python-based solution for collecting, analyzing, and forecasting oil and gas production data. This project showcases skills in creative way to get data, data engineering, exploratory analysis, and machine learning modeling, designed for those curious about oil and gas.

---

## Features
- **Scraping**: Automates data extraction for well header and production data from North Dakota State website.
- **Data Cleaning**: Cleans and preprocesses the data for analysis.
- **Exploratory Analysis**: Provides insights into production trends and operational efficiency.
- **Forecasting**: Implements machine learning models and DCA to predict future production values.
- **Reproducible Workflow**: Organized structure for easy navigation and extension.

---

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Jalley22/Oil-and-Gas-Production-Analytics-Workflow.git
   cd Oil-and-Gas-Production-Analytics-Workflow
   
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt

   python src/get_data/scrape_production_data.py

## Usage

1. **Get the Data**
   - The scraper collects well header and production data for a specified operator.
   - Upon running the script:
     - Input the operator name when prompted.
     - Alternatively, select from the available options.
   - **Output**: raw CSV files are stored in the `data/raw` directory.

2. **Analyze the Data**
   - **Notebooks for Analysis**: Use Jupyter notebooks provided in the `notebooks/` directory for exploratory data analysis.

3. **Forecast Production**
   - Build machine learning models using the data in the `forecasting/` directory to predict future production values.
  ```
  Oil-and-Gas-Production-Analytics-Workflow/
  |
  ├── data/                   # Scraped data files
  ├── notebooks/              # Jupyter notebooks for data exploration
  ├── src/
  │   ├── get_data/           # Web scraping scripts
  │   ├── analysis/           # Data cleaning and EDA scripts
  │   ├── forecasting/        # Forecasting models and scripts
  │
  ├── venv/                   # Virtual environment files
  ├── requirements.txt        # Python dependencies
  └── README.md               # Project documentation
  ```


## Key Libraries
- **Scraping**: BeautifulSoup, requests
- **Data Manipulation**: pandas, numpy
- **Visualization**: matplotlib, seaborn
- **Machine Learning**: scikit-learn

---

## Contributions and Future Work
I welcome contributions! Some areas for enhancement include:
- Expanding the scraper for additional data sources (Texas, etc.).
- Adding advanced machine learning models for forecasting.
- Visualizing results with interactive dashboards (e.g., Plotly, Dash).
