import pandas as pd
import yfinance as yf
import numpy as np
from tkinter import Tk, Text, Scrollbar, VERTICAL, RIGHT, Y, END, Label
from datetime import datetime, timedelta

def calculate_volatility(stock_data):
    # Calculate daily returns
    stock_data['Returns'] = stock_data['Close'].pct_change()
    
    # Calculate the rolling standard deviation of returns (21 trading days ≈ 1 month)
    stock_data['Volatility'] = stock_data['Returns'].rolling(window=21).std() * np.sqrt(252)
    
    return stock_data

def fetch_nifty_data():
    # Fetch historical data for Nifty index for the last 3 months
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)  # approximately 3 months
    
    nifty = yf.Ticker("^NSEI")
    stock_data = nifty.history(start=start_date, end=end_date)
    return stock_data

def display_volatility():
    stock_data = fetch_nifty_data()
    volatility_data = calculate_volatility(stock_data)
    
    # Calculate average volatility
    avg_volatility = volatility_data['Volatility'].mean()
    
    # Format the data for display
    volatility_str = "Date\t\tClose\t\tVolatility\n"
    volatility_str += "=" * 50 + "\n"
    
    for index, row in volatility_data.iterrows():
        date_str = index.strftime('%Y-%m-%d')
        close = f"{row['Close']:.2f}"
        vol = f"{row['Volatility']*100:.2f}%" if not np.isnan(row['Volatility']) else "N/A"
        volatility_str += f"{date_str}\t{close}\t\t{vol}\n"
    
    # Add average volatility at the bottom
    volatility_str += "\n" + "=" * 50 + "\n"
    volatility_str += f"Average Volatility: {avg_volatility*100:.2f}%"
    
    # Clear existing text and insert new data
    text_box.delete(1.0, END)
    text_box.insert(END, volatility_str)

# Initialize Tkinter window
root = Tk()
root.title("Nifty 3-Month Historical Volatility")
root.geometry("600x400")  # Set window size

# Create a Textbox with a Scrollbar
scrollbar = Scrollbar(root, orient=VERTICAL)
text_box = Text(root, wrap='none', yscrollcommand=scrollbar.set, font=('Courier', 10))
scrollbar.config(command=text_box.yview)
scrollbar.pack(side=RIGHT, fill=Y)
text_box.pack(expand=True, fill='both')

# Fetch and display volatility data
display_volatility()

# Start the Tkinter main loop
root.mainloop()