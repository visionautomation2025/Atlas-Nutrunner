import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
from tkinter import Tk, ttk, Scrollbar, Frame
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Connect to the SQLite database
db_path = 'E:/nifty_data.db'

# Define strike prices
strike_price_ce = 24000
strike_price_pe = 23500

# Query to fetch data for CE
query_ce = f"""
SELECT date_time, oi, changein_oi, ltp, volume
FROM OPTION_CE_DATA
WHERE strike_price = {strike_price_ce} AND date_time BETWEEN '2025-02-01 09:00:00' AND '2025-02-01 15:30:00'
"""

# Query to fetch data for PE
query_pe = f"""
SELECT date_time, oi, changein_oi, ltp, volume
FROM OPTION_PE_DATA
WHERE strike_price = {strike_price_pe} AND date_time BETWEEN '2025-02-01 09:00:00' AND '2025-02-01 15:30:00'
"""

# Fetch data
with sqlite3.connect(db_path) as conn:
    df_ce = pd.read_sql_query(query_ce, conn)
    df_pe = pd.read_sql_query(query_pe, conn)

# Convert date_time to datetime format
df_ce['date_time'] = pd.to_datetime(df_ce['date_time'])
df_pe['date_time'] = pd.to_datetime(df_pe['date_time'])

# Tkinter GUI setup
root = Tk()
root.title("Option Data for Strike Prices")

# Frame for the tables
frame_tables = Frame(root)
frame_tables.pack(side='top', fill='both', expand=True)

# Frame for CE Data
frame_ce = Frame(frame_tables)
frame_ce.pack(side='left', fill='both', expand=True)

frame_pe = Frame(frame_tables)
frame_pe.pack(side='right', fill='both', expand=True)

# Create Treeview widgets for CE and PE data
tree_ce = ttk.Treeview(frame_ce, columns=list(df_ce.columns), show='headings')
tree_ce.pack(side='left', fill='both', expand=True)

tree_pe = ttk.Treeview(frame_pe, columns=list(df_pe.columns), show='headings')
tree_pe.pack(side='left', fill='both', expand=True)

# Add scrollbars
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

# Insert data into the Treeviews
for _, row in df_ce.iterrows():
    tree_ce.insert("", "end", values=list(row))

for _, row in df_pe.iterrows():
    tree_pe.insert("", "end", values=list(row))

# Create a frame for the CE and PE graphs
frame_graphs = Frame(root)
frame_graphs.pack(side='bottom', fill='both', padx=10, pady=10)

# -------- CE Graph --------
frame_ce_graph = Frame(frame_graphs)
frame_ce_graph.pack(side='left', padx=10)

fig_ce, ax_ce = plt.subplots(figsize=(5, 3))  # Small figure size

# Primary y-axis (Change in OI)
ax_ce.plot(df_ce['date_time'], df_ce['changein_oi'], label="CE Change in OI", color='green')
ax_ce.set_xlabel("Time")
ax_ce.set_ylabel("Change in OI", color='green')
ax_ce.tick_params(axis='y', labelcolor='green')

# Secondary y-axis (LTP)
ax_ce_ltp = ax_ce.twinx()
ax_ce_ltp.plot(df_ce['date_time'], df_ce['ltp'], label="CE LTP", color='red')
ax_ce_ltp.set_ylabel("LTP", color='red')
ax_ce_ltp.tick_params(axis='y', labelcolor='red')

# Legends
lines_ce, labels_ce = ax_ce.get_legend_handles_labels()
lines_ltp_ce, labels_ltp_ce = ax_ce_ltp.get_legend_handles_labels()
ax_ce.legend(lines_ce + lines_ltp_ce, labels_ce + labels_ltp_ce, loc="upper left")

# **Title with Strike Price**
ax_ce.set_title(f"CE Data (Strike Price: {strike_price_ce})")

canvas_ce = FigureCanvasTkAgg(fig_ce, master=frame_ce_graph)
canvas_ce_widget = canvas_ce.get_tk_widget()
canvas_ce_widget.pack()

# -------- PE Graph --------
frame_pe_graph = Frame(frame_graphs)
frame_pe_graph.pack(side='right', padx=10)

fig_pe, ax_pe = plt.subplots(figsize=(5, 3))  # Small figure size

# Primary y-axis (Change in OI)
ax_pe.plot(df_pe['date_time'], df_pe['changein_oi'], label="PE Change in OI", color='blue')
ax_pe.set_xlabel("Time")
ax_pe.set_ylabel("Change in OI", color='blue')
ax_pe.tick_params(axis='y', labelcolor='blue')

# Secondary y-axis (LTP)
ax_pe_ltp = ax_pe.twinx()
ax_pe_ltp.plot(df_pe['date_time'], df_pe['ltp'], label="PE LTP", color='orange')
ax_pe_ltp.set_ylabel("LTP", color='orange')
ax_pe_ltp.tick_params(axis='y', labelcolor='orange')

# Legends
lines_pe, labels_pe = ax_pe.get_legend_handles_labels()
lines_ltp_pe, labels_ltp_pe = ax_pe_ltp.get_legend_handles_labels()
ax_pe.legend(lines_pe + lines_ltp_pe, labels_pe + labels_ltp_pe, loc="upper left")

# **Title with Strike Price**
ax_pe.set_title(f"PE Data (Strike Price: {strike_price_pe})")

canvas_pe = FigureCanvasTkAgg(fig_pe, master=frame_pe_graph)
canvas_pe_widget = canvas_pe.get_tk_widget()
canvas_pe_widget.pack()

# Run Tkinter main loop
root.mainloop()
