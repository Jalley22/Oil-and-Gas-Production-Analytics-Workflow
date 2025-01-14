# Import necessary Libraries
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from scipy.optimize import curve_fit
import janitor

# Modified Hyperbolic Arps equation
# This function models production decline using the hyperbolic decline formula
def mod_hyperbolic_arps(t, qi, Di, b):
    return qi / (1 + b * Di * t) ** (1/b)
# Define the Arps forecast function
# This function forecasts production using Arps parameters
def arps_forecast(t, qi, Di, b):
    
    time_adjusted = t - np.min(t)
    return qi * (1 + b * Di * time_adjusted) ** (-1 / b)

# Load processed dataset create during the eda
df = pd.read_csv("data/processed/final_df.csv")
df_clean = df.clean_names() # clean column names for consistency

# Select relevant columns for analysis
daily_cols = ['ndic_file_no', 'api_no', 'well_type', 'well_status',
       'latitude','longitude', 'current_operator', 'current_well_name', 'total_depth',
       'field', 'perfs', 'filenumber','well_id','ds', 'producing_days', 'y', 'daily_gas_rate',
       'daily_water_rate', 'cumulative_oil_bbls', 'cumulative_gas_mcf',
       'cumulative_wtr_bbls', 'rolling_oil_mean', 'rolling_oil_std',
       'is_outlier', 'trend', 'yhat', 'yhat_lower', 'yhat_upper']

daily_df = df_clean[daily_cols]

# Filter for wells with status 'A' (active wells)
daily_df = daily_df.query(
    "well_status == 'A'"
)

# Placeholder for Arps parameters
qi_est = float()  # Initial production rate (qi)
Di_est = float() # Decline rate (Di)
b_est = float()  # Hyperbolic exponent (b)

# Rename column 'y' to 'daily_oil_rate' for clarity
daily_df = daily_df.rename(columns={'y':'daily_oil_rate'})

# Streamlit dashboard title
st.title('Production Dashboard with Dynamic Arps Parameters')

# Sidebar: Select field and well
st.sidebar.header("Select Field and Well")
# Sidebar filters
selected_field = st.sidebar.radio('Fields', daily_df['field'].unique())
st.sidebar.markdown("---")
selected_well = st.sidebar.selectbox(
    'Wells', sorted(daily_df[daily_df['field']==selected_field]['current_well_name'].unique())
)

# Filter the DataFrame based on selected field and well
filtered_df = daily_df[
    (daily_df['current_well_name'] == selected_well) & 
    (daily_df['field'] == selected_field) &
    daily_df['daily_oil_rate'].notna()
]

# Fill missing rolling oil mean values with daily oil rate
filtered_df['rolling_oil_mean'] = filtered_df['rolling_oil_mean'].fillna(filtered_df['daily_oil_rate'])
# Let's perform traditional DCA on selected well

# Parameter bounds, including b factor constraints (e.g., 0 < b <= 1)
param_bounds = ([0, 0, 0], [np.inf, 15, 1.5])  # qi, Di, and b upper/lower bounds
rows_list = []
# Filter the DataFrame for the current well
well_data = filtered_df.copy()

# Extract Time and rate for curve fitting
time = well_data['producing_days'].values
rate = well_data['rolling_oil_mean'].values

# Fit the Arps model to estimate parameters (qi, Di, b)
if len(time) >= 3:  # Proceed only if there are at least three data points
    try:
        params, covariance = curve_fit(mod_hyperbolic_arps, time, rate, bounds=param_bounds)
        qi_est, Di_est, b_est = params
        
        # Calculate the predicted rates using the fitted model and parameters
        predicted_rates = mod_hyperbolic_arps(time, *params)
        
        # Calculate RMSE
        rmse = np.sqrt(np.mean((rate - predicted_rates) ** 2))
            
        # Append the results, including RMSE, to the list                
        rows_list.append({'current_well_name': selected_well, 'qi': qi_est, 'Di': Di_est, 'b': b_est, 'RMSE': rmse})
    except RuntimeError:
        qi_est, Di_est, b_est = 500, 0.01, 0.5 

# Sidebar: Sliders for adjusting Arps parameters
st.sidebar.header("Arps Parameters")
qi = st.sidebar.slider("Initial Production Rate (qi)", min_value=0.0, max_value=1000.0, value=float(qi_est), step=10.0)
Di = st.sidebar.slider("Decline Rate (Di)", min_value=0.0, max_value=1.0, value=float(Di_est)*30, step=0.01)
b = st.sidebar.slider("b-Factor", min_value=0.0, max_value=1.5, value=float(b_est), step=0.01)

# Reset parameters to best-fit values
if st.sidebar.button("Reset to Best-Fit Parameters"):
    qi, Di, b = qi_est, Di_est * 30, b_est

# Convert rows_list directly to DataFrame
param_df = pd.DataFrame(rows_list)

Df_constant = 0.005687923  
# Forecast 6 Months past last production date. 
forecast_df = pd.DataFrame()
forecast_rows_list = []
# Generate forecast based on user inputs
forecast_period = 6 * 30  # Forecast 6 months (in days)
max_ip_day = filtered_df['producing_days'].max()
additional_time_points = np.arange(max_ip_day + 30, max_ip_day + forecast_period + 1, 30)
full_time_points = np.concatenate([filtered_df['producing_days'], additional_time_points])
forecasted_production = arps_forecast(full_time_points, qi, Di/30, b)

# Create a forecast DataFrame
forecast_df = pd.DataFrame({
    'current_well_name': selected_well,
    'producing_days': full_time_points,
    'ForecastedProduction': forecasted_production
})

# Dashboard Layout
col1, col2 = st.columns(2)

# Left Column: Production Plots
with col1:
    # Daily Oil Chart with Confidence Interval and Arps Forecast
    fig = go.Figure()

    # Add main line for 'daily_oil_rate'
    fig.add_trace(
        go.Scatter(
            x=filtered_df['producing_days'],
            y=filtered_df['daily_oil_rate'],
            mode='lines+markers',
            name='Daily Oil Rate',
            line=dict(color='green', dash='solid')
        )
    )
    # Add Prophet Forecasted Daily Oil Rate Line
    fig.add_trace(
        go.Scatter(
            x=filtered_df['producing_days'],
            y=filtered_df['yhat'],
            mode='lines',
            name='Prophet Forecasted Daily Oil Rate',
            line=dict(color='purple', dash='dash', width=2)
        )
    )
    # Add arps Forecasted Daily Oil Rate Line
    fig.add_trace(
        go.Scatter(
            x=forecast_df['producing_days'],
            y=forecast_df['ForecastedProduction'],
            mode='lines',
            name='Forecasted Daily Oil Rate',
            line=dict(color='white', dash='dash', width=3)
        )
    )
    # Add Confidence Interval as Shaded Area
    fig.add_trace(
        go.Scatter(
            x=list(filtered_df['producing_days']) + list(filtered_df['producing_days'][::-1]),  # Combine x for both bounds
            y=list(filtered_df['yhat_upper']) + list(filtered_df['yhat_lower'][::-1]), 
            fill='toself',
            fillcolor='rgba(0, 0, 0, 0.0)', 
            line=dict(color='rgba(255, 255, 0, 1.0)'),  
            mode='lines',
            name='Forecast Confidence Interval'
        )
    )

    # Update layout
    fig.update_layout(
        title='Daily Oil Production with Confidence Intervals and Arps Forecast',
        xaxis_title='Producing Days',
        yaxis_title='Daily Oil Rate (bbls)',
        template='plotly_white',
        yaxis=dict(range=[0,None]),
        height=800,
        legend=dict(
            font = dict(size=12, color="white"),
            yanchor="top", y=0.99, xanchor="right", x=0.99,
            bgcolor="rgba(0, 0, 0, 0.5)"
            )
    )

    # Streamlit Plot
    st.plotly_chart(fig, use_container_width=True)
    # Add some metrics and charts
    st.subheader('Daily Production')
    daily_oil_chart_date = px.line(filtered_df, x='ds', y='daily_oil_rate', color='current_well_name')
    st.plotly_chart(daily_oil_chart_date, use_container_width=True)

# Add RMSE display
rmse = np.sqrt(np.mean((rate - arps_forecast(time, qi, Di/30, b)) ** 2))      
st.sidebar.metric("RMSE", f"{rmse:.2f}")

# Option to download the forecast data
csv = forecast_df.to_csv(index=False)
st.download_button(label="Download Forecast Data", data=csv, file_name="forecast.csv", mime="text/csv")

# Right Column: Map Chart
with col2:
    # Prepare data for map
    map_df = daily_df[daily_df['field'] == selected_field]
    cum_oil_df = map_df.groupby('current_well_name')['cumulative_oil_bbls'].max().reset_index()
    min_cum = cum_oil_df.cumulative_oil_bbls.min()
    cum_oil_df['cumulative_oil_bbls'] = cum_oil_df['cumulative_oil_bbls'].fillna(min_cum)    
    map_df = map_df[['current_well_name','latitude', 'longitude']].drop_duplicates()
    
    # Merge the cumulative oil data with the map DataFrame
    map_df = map_df.merge(cum_oil_df, on='current_well_name', how='left')

    # Plot map using Plotly Express
    map_fig = px.scatter_mapbox(
        map_df,
        lat='latitude',
        lon='longitude',
        hover_name='current_well_name',
        zoom=10,
        color_discrete_sequence=["fuchsia"],
        size='cumulative_oil_bbls',
        title='Well Location'
    )

    # Configure map style
    map_fig.update_layout(
        mapbox_style='open-street-map',
        height=800,
        margin={"r": 0, "t": 0, "l": 0, "b": 0}
    )

    st.plotly_chart(map_fig, use_container_width=True)


