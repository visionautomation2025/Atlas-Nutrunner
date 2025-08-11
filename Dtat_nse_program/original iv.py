import sqlite3
import numpy as np

import pandas as pd
import matplotlib.pyplot as plt
from tkinter import Tk, ttk, Scrollbar, Frame, Label
from scipy.stats import norm

# Connect to the SQLite database
db_path = 'E:/nifty_data.db'

# Query to fetch data for strike price 23000 on 27-01-2025 for CE
query_ce = """
SELECT date_time, oi, changein_oi, ltp, volume, iv
FROM OPTION_CE_DATA
WHERE strike_price = 23500 AND date_time BETWEEN '2025-01-31 09:00:00' AND '2025-01-31 15:30:00'
"""

# Query to fetch data for strike price 23000 on 27-01-2025 for PE
query_pe = """
SELECT date_time, oi, changein_oi, ltp, volume, iv
FROM OPTION_PE_DATA
WHERE strike_price = 23300 AND date_time BETWEEN '2025-01-31 09:00:00' AND '2025-01-31 15:30:00'
"""

# Fetch data using a context manager for the database connection
with sqlite3.connect(db_path) as conn:
    df_ce = pd.read_sql_query(query_ce, conn)
    df_pe = pd.read_sql_query(query_pe, conn)

# Convert date_time to datetime format
df_ce['date_time'] = pd.to_datetime(df_ce['date_time'])
df_pe['date_time'] = pd.to_datetime(df_pe['date_time'])

# Calculate correlation coefficients between IV and LTP
corr_ce_iv_ltp = df_ce['iv'].corr(df_ce['ltp'])
corr_pe_iv_ltp = df_pe['iv'].corr(df_pe['ltp'])

# Function to calculate delta using Black-Scholes model
def calculate_delta(S, K, T, r, sigma, option_type):
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    if option_type == 'ce':
        return norm.cdf(d1)
    elif option_type == 'pe':
        return norm.cdf(d1) - 1

# Assuming some values for S, r, and T
S = 23000  # Current price of the underlying asset
r = 0.05   # Risk-free rate
T = 1      # Time to expiration in years

# Calculate delta for CE and PE
df_ce['delta'] = df_ce.apply(lambda row: calculate_delta(S, 23200, T, r, row['iv'], 'ce'), axis=1)
df_pe['delta'] = df_pe.apply(lambda row: calculate_delta(S, 23100, T, r, row['iv'], 'pe'), axis=1)

# Tkinter GUI setup
root = Tk()
root.title("Option Data for Strike Price 23000 on 27-01-2025")

# Create frames for CE and PE data grids
frame_ce = Frame(root)
frame_ce.pack(side='left', fill='both', expand=True)

frame_pe = Frame(root)
frame_pe.pack(side='right', fill='both', expand=True)

# Add labels to display correlation coefficients
Label(frame_ce, text=f"Correlation (IV vs LTP): {corr_ce_iv_ltp:.2f}", font=('Arial', 12)).pack()
Label(frame_pe, text=f"Correlation (IV vs LTP): {corr_pe_iv_ltp:.2f}", font=('Arial', 12)).pack()

# Create Treeview widgets for CE and PE data
tree_ce = ttk.Treeview(frame_ce, columns=list(df_ce.columns), show='headings')
tree_ce.pack(side='left', fill='both', expand=True)

tree_pe = ttk.Treeview(frame_pe, columns=list(df_pe.columns), show='headings')
tree_pe.pack(side='left', fill='both', expand=True)

# Add scrollbars to the Treeview widgets
scrollbar_ce = Scrollbar(frame_ce, orient='vertical', command=tree_ce.yview)
scrollbar_ce.pack(side='right', fill='y')
tree_ce.configure(yscrollcommand=scrollbar_ce.set)

scrollbar_pe = Scrollbar(frame_pe, orient='vertical', command=tree_pe.yview)
scrollbar_pe.pack(side='right', fill='y')
tree_pe.configure(yscrollcommand=scrollbar_pe.set)

# Define columns for CE data
for col in df_ce.columns:
    tree_ce.heading(col, text=col)
    tree_ce.column(col, width=100)

# Define columns for PE data
for col in df_pe.columns:
    tree_pe.heading(col, text=col)
    tree_pe.column(col, width=100)

# Insert data into the CE Treeview widget
for index, row in df_ce.iterrows():
    tree_ce.insert("", "end", values=list(row))

# Insert data into the PE Treeview widget
for index, row in df_pe.iterrows():
    tree_pe.insert("", "end", values=list(row))

# Plotting the graphs
fig, ((ax_ce, ax_ce_delta), (ax_pe, ax_pe_delta)) = plt.subplots(2, 2, figsize=(15, 10))

# Plot for CE data
# Primary y-axis for Change in OI
ax_ce.plot(df_ce['date_time'], df_ce['changein_oi'], label='Change in OI', color='blue')
ax_ce.set_xlabel('Time')
ax_ce.set_ylabel('Change in OI', color='blue')
ax_ce.tick_params(axis='y', labelcolor='blue')

# Secondary y-axis for LTP
ax_ce_ltp = ax_ce.twinx()
ax_ce_ltp.plot(df_ce['date_time'], df_ce['ltp'], label='LTP', color='red')
ax_ce_ltp.set_ylabel('LTP', color='red')
ax_ce_ltp.tick_params(axis='y', labelcolor='red')

# Add legends for CE data
lines_ce, labels_ce = ax_ce.get_legend_handles_labels()
lines_ltp_ce, labels_ltp_ce = ax_ce_ltp.get_legend_handles_labels()
ax_ce.legend(lines_ce + lines_ltp_ce, labels_ce + labels_ltp_ce, loc='upper left')

# Set title for CE plot
ax_ce.set_title(f'CE Data for Strike Price 23200 on 27-01-2025\nCorrelation (IV vs LTP): {corr_ce_iv_ltp:.2f}')

# Plot for CE Delta
ax_ce_delta.plot(df_ce['date_time'], df_ce['delta'], label='Delta', color='green')
ax_ce_delta.set_xlabel('Time')
ax_ce_delta.set_ylabel('Delta', color='green')
ax_ce_delta.tick_params(axis='y', labelcolor='green')
ax_ce_delta.set_title('CE Delta')

# Plot for PE data
# Primary y-axis for Change in OI
ax_pe.plot(df_pe['date_time'], df_pe['changein_oi'], label='Change in OI', color='blue')
ax_pe.set_xlabel('Time')
ax_pe.set_ylabel('Change in OI', color='blue')
ax_pe.tick_params(axis='y', labelcolor='blue')

# Secondary y-axis for LTP
ax_pe_ltp = ax_pe.twinx()
ax_pe_ltp.plot(df_pe['date_time'], df_pe['ltp'], label='LTP', color='red')
ax_pe_ltp.set_ylabel('LTP', color='red')
ax_pe_ltp.tick_params(axis='y', labelcolor='red')

# Add legends for PE data
lines_pe, labels_pe = ax_pe.get_legend_handles_labels()
lines_ltp_pe, labels_ltp_pe = ax_pe_ltp.get_legend_handles_labels()
ax_pe.legend(lines_pe + lines_ltp_pe, labels_pe + labels_ltp_pe, loc='upper left')

# Set title for PE plot
ax_pe.set_title(f'PE Data for Strike Price 23100 on 27-01-2025\nCorrelation (IV vs LTP): {corr_pe_iv_ltp:.2f}')

# Plot for PE Delta
ax_pe_delta.plot(df_pe['date_time'], df_pe['delta'], label='Delta', color='green')
ax_pe_delta.set_xlabel('Time')
ax_pe_delta.set_ylabel('Delta', color='green')
ax_pe_delta.tick_params(axis='y', labelcolor='green')
ax_pe_delta.set_title('PE Delta')

# Adjust layout
plt.tight_layout()

# Show the plot
plt.show()

# Run the Tkinter main loop
root.mainloop()