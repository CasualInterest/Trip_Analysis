# Code for displaying Trip Length
import matplotlib.pyplot as plt
import pandas as pd

# Sample data for demonstration
trip_lengths = ['Short', 'Medium', 'Long']
trip_counts = [150, 200, 50]  # Example counts of trips based on lengths

# Calculate percentages
total_trips = sum(trip_counts)
percentages = [(count / total_trips) * 100 for count in trip_counts]

# Create a DataFrame
trip_data = pd.DataFrame({
    'Trip Length': trip_lengths,
    'Count': trip_counts,
    'Percentage': percentages
})

# Plotting
x = range(len(trip_data))  # the label locations
width = 0.35  # the width of the bars

fig, ax = plt.subplots()

# Create bars for counts and percentages
bars1 = ax.bar(x, trip_data['Count'], width, label='Count')
bars2 = ax.bar([p + width for p in x], trip_data['Percentage'], width, label='Percentage')

# Add some text for labels, title and custom x-axis tick labels, etc.
ax.set_xlabel('Trip Length')
ax.set_ylabel('Values')
ax.set_title('Trip Count and Percentage by Trip Length')
ax.set_xticks([p + width / 2 for p in x])
ax.set_xticklabels(trip_data['Trip Length'])
ax.legend()

# Show the plot
plt.show()