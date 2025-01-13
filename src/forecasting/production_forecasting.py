# %%
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import janitor
from scipy.optimize import curve_fit, minimize
## %%
#df = pd.read_csv("../../data/processed/final_df.csv") # for local dev
df = pd.read_csv("data/processed/final_df.csv")
df_clean = df.clean_names()

## %% 
daily_cols = ['ndic_file_no', 'api_no', 'well_type', 'well_status',
       'latitude','longitude', 'current_operator', 'current_well_name', 'total_depth',
       'field', 'perfs', 'filenumber','well_id','ds', 'producing_days', 'y', 'daily_gas_rate',
       'daily_water_rate', 'cumulative_oil_bbls', 'cumulative_gas_mcf',
       'cumulative_wtr_bbls', 'rolling_oil_mean', 'rolling_oil_std',
       'is_outlier', 'trend', 'yhat', 'yhat_lower', 'yhat_upper']

daily_df = df_clean[daily_cols]
daily_df = daily_df.query(
    "well_status == 'A'"
)


#change column name y back to oil rate (need to do this before the csv export from eda)
daily_df = daily_df.rename(columns={'y':'daily_oil_rate'})

## %%
st.title('Production Dashboard')

# Sidebar filters
selected_field = st.sidebar.radio('Well Status', daily_df['field'].unique())
selected_well = st.sidebar.radio('Wells', daily_df[daily_df['field']==selected_field]['current_well_name'].unique())

# Apply filters
filtered_df = daily_df[
    (daily_df['current_well_name'] == selected_well) & 
    (daily_df['field'] == selected_field) &
    daily_df['daily_oil_rate'].notna()
]

# Let's perform traditional DCA on selected well
# Modified Hyperbolic Arps equation
def mod_hyperbolic_arps(t, qi, Di, b):
    return qi / (1 + b * Di * t) ** (1/b)
# Parameter bounds, including b factor constraints (e.g., 0 < b <= 1)
param_bounds = ([0, 0, 0], [np.inf, 15, 1.5])  # qi, Di, and b upper/lower bounds
rows_list = []
# Filter the DataFrame for the current well
well_data = filtered_df.copy()    
# Extract Time and rate for curve fitting

time = well_data['producing_days'].values
rate = well_data['daily_oil_rate'].values

# Skip wells with insufficient data
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
    except RuntimeError as e:
        print(f"Curve fitting failed for well {selected_well}: {e}")

# Convert rows_list directly to DataFrame
param_df = pd.DataFrame(rows_list)

def arps_forecast(t, qi, Di, b):
    
    time_adjusted = t - np.min(t)
    return qi * (1 + b * Di * time_adjusted) ** (-1 / b)
Df_constant = 0.005687923  
# Forecast 6 Months past last production date. 
forecast_df = pd.DataFrame()
forecast_rows_list = []

for index, row in param_df.iterrows():
    well = row['current_well_name']    
    qi_est = row['qi']
    Di_est = row['Di']
    b_est = row['b']
    
    max_ip_day = well_data['producing_days'].max()  # The last recorded production day for the well
    Q_ip_day = well_data['producing_days'].min()

    # Generate forecast time points from initial production day up to six months past the last recorded day
    # Convert 6 months to days (approx. 6 * 30)
    forecast_period = 6 * 30  # 6 months in days
    initial_time = Q_ip_day  # Starting from the first month of production

    # Create an array starting from initial_time to max_ip_day in steps of 30 days (one month)
    # Then extend this array to six months beyond the max_ip_day
    existing_time_points = np.arange(initial_time, max_ip_day + 1, 30)  # Existing production times
    additional_time_points = np.arange(max_ip_day + 30, max_ip_day + forecast_period + 1, 30)  # Additional forecast times

    # Combine both arrays to have a full range from start to six months past last record
    full_time_points = np.concatenate([existing_time_points, additional_time_points])
    
       
    # Forecast production using the fitted parameters
    forecasted_production = arps_forecast(full_time_points,qi=qi_est, Di=Di_est, b=b_est)
    
    # Create a DataFrame for the forecasted values
    well_forecast_df = pd.DataFrame({
        'current_well_name': well,
        'producing_days': full_time_points,
        'ForecastedProduction': forecasted_production
    })
    
    # Append the forecasted values for the current well to the list
    forecast_rows_list.append(well_forecast_df)

# Concatenate all forecasts into a single DataFrame
forecast_df = pd.concat(forecast_rows_list, ignore_index=True)

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
# Add arps Forecasted Daily Oil Rate Line
fig.add_trace(
    go.Scatter(
        x=forecast_df['producing_days'],
        y=forecast_df['ForecastedProduction'],
        mode='lines',
        name='Forecasted Daily Oil Rate',
        line=dict(color='blue', dash='dash', width=3)
    )
)
# Add Confidence Interval as Shaded Area
fig.add_trace(
    go.Scatter(
        x=list(filtered_df['producing_days']) + list(filtered_df['producing_days'][::-1]),  # Combine x for both bounds
        y=list(filtered_df['yhat_upper']) + list(filtered_df['yhat_lower'][::-1]), 
        fill='toself',
        fillcolor='rgba(0, 0, 0, 0.0)',  # Adjusted color for debugging
        line=dict(color='rgba(255, 0, 0, 0.5)'),  # Make line visible for debugging
        mode='lines',
        name='Forecast Confidence Interval'
    )
)

# Update layout
fig.update_layout(
    title='Daily Oil Production with Confidence Intervals and Arps Forecast',
    xaxis_title='Producing Days',
    yaxis_title='Daily Oil Rate (bbls)',
    legend=dict(yanchor="top", y=0.99, xanchor="right", x=0.99)
)

# Streamlit Plot
st.plotly_chart(fig)
# Add some metrics and charts
st.subheader('Daily Production')
daily_oil_chart_date = px.line(filtered_df, x='ds', y='daily_oil_rate', color='current_well_name')
st.plotly_chart(daily_oil_chart_date)
