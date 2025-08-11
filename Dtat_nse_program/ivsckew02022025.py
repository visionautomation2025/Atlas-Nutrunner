import sqlite3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import skew
from datetime import datetime 

# Function to calculate IV skewness
def calculate_iv_skewness(options_data):
    # Group by strike price and calculate the mean implied volatility
    iv_mean = options_data.groupby('strike_price')['iv'].mean()
    
    # Calculate skewness
    iv_skewness = skew(iv_mean)
    
    return iv_mean, iv_skewness

# Function to visualize IV skewness
def plot_iv_skewness(iv_mean):
    plt.figure(figsize=(10, 6))
    plt.plot(iv_mean.index, iv_mean.values, marker='o')
    plt.title('Implied Volatility Skew')
    plt.xlabel('Strike Price')
    plt.ylabel('Mean Implied Volatility')
    plt.grid()
    plt.axhline(y=iv_mean.mean(), color='r', linestyle='--', label='Average IV')
    plt.legend()
    plt.show()

# Main function
def main():
    current_date = datetime.today().strftime('%Y-%m-%d')
    # Connect to the SQLite database
    conn = sqlite3.connect('E:/nifty_data.db')

    # Fetch data from OPTION_CE_DATA and OPTIONS_PE_DATA tables
#     ce_query = "SELECT strike_price, iv FROM option_ce_data WHERE date_time = '2025-02-01 15:00:00';"
#     pe_query = "SELECT strike_price, iv FROM option_pe_data WHERE date_time = '2025-02-01';"
    ce_query = f"""
    SELECT strike_price, iv
    FROM option_ce_data
    WHERE date_time BETWEEN '{current_date} 09:00:00' AND '{current_date} 15:30:00';
    """
    pe_query = f"""
    SELECT strike_price, iv
    FROM option_pe_data
    WHERE date_time BETWEEN '{current_date} 09:00:00' AND '{current_date} 15:30:00';
    """
    
    ce_data = pd.read_sql_query(ce_query, conn)
    pe_data = pd.read_sql_query(pe_query, conn)
    
    print(f"Call Options Data Count: {len(ce_data)}")
    print(f"Put Options Data Count: {len(pe_data)}")

    # Combine the data from both tables
    options_data = pd.concat([ce_data, pe_data], ignore_index=True)

    # Close the database connection
    conn.close()

    # Calculate IV skewness
    iv_mean, iv_skewness = calculate_iv_skewness(options_data)

    print(f'Implied Volatility Skewness: {iv_skewness}')
    
    # Plot the results
    plot_iv_skewness(iv_mean)

if __name__ == '__main__':
    main()
