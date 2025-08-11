import matplotlib.pyplot as plt
import numpy as np

# Sample data
strike_prices = ['23000', '22000', '21000']
oi = [1000, 1500, 1200]
change_in_oi = [100, -50, 200]
current_volume = [2, 5, 10]  # Current volume
target_volume = [10, 5, 15]   # Target volume

# Calculate the difference for volume representation
volume_bars = []
for i in range(len(current_volume)):
    if current_volume[i] < target_volume[i]:
        volume_bars.append([current_volume[i], target_volume[i] - current_volume[i]])
    else:
        volume_bars.append([target_volume[i], 0])  # No difference to show

# Prepare the data for plotting
bar_width = 0.25
x = np.arange(len(strike_prices))

# Create a single histogram frame for all parameters
fig, ax = plt.subplots(figsize=(10, 6))

# Plotting the bars for each parameter
for i in range(len(strike_prices)):
    # Volume Bars: Current (green) and Difference (red)
    ax.bar(x[i] - bar_width, volume_bars[i][0], width=bar_width, color='green', label='Current Volume' if i == 0 else "")
    ax.bar(x[i] - bar_width, volume_bars[i][1], bottom=volume_bars[i][0], width=bar_width, color='red', label='Difference' if i == 0 else "")
    
    # Open Interest Bars (blue)
    ax.bar(x[i], oi[i], width=bar_width, color='blue', label='Open Interest' if i == 0 else "")
    
    # Change in OI Bars (orange)
    ax.bar(x[i] + bar_width, change_in_oi[i], width=bar_width, color='orange', label='Change in OI' if i == 0 else "")

# Adding labels and title
ax.set_xlabel('Strike Prices')
ax.set_ylabel('Values')
ax.set_title('Combined Histogram of Parameters for Each Strike Price')
ax.set_xticks(x)
ax.set_xticklabels(strike_prices)
ax.legend()

plt.tight_layout()
plt.show()
