# Updated app.py with Grouped Bar Chart for Trip Length

import plotly.graph_objects as go
import pandas as pd

# Sample Data (Replace it with your actual data source)
trip_data = {
    'trip_length': ['0-1 miles', '1-2 miles', '2-3 miles', '3+ miles'],
    'count': [150, 120, 90, 60]
}

# Create a DataFrame
trip_df = pd.DataFrame(trip_data)

# Calculate percentages
trip_df['percentage'] = (trip_df['count'] / trip_df['count'].sum()) * 100

# Create a grouped bar chart
fig = go.Figure()

fig.add_trace(go.Bar(
    x=trip_df['trip_length'],
    y=trip_df['count'],
    name='Number of Trips'
))

fig.add_trace(go.Bar(
    x=trip_df['trip_length'],
    y=trip_df['percentage'],
    name='Percentage of Total Trips'
))

# Update layout
fig.update_layout(
    title='Trip Length Distribution',
    barmode='group',
    xaxis_title='Trip Length',
    yaxis_title='Count / Percentage',
)

# Show the figureig.show() 
