import sqlite3
import asyncio
import aiohttp
from datetime import datetime, time, timedelta
import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
import nest_asyncio

nest_asyncio.apply()

DB_PATH = 'E:/nifty_data.db'
EXPIRY_DATE = '19-Jun-2025'

# Style configuration
GREEN_BG = '#90EE90'  # Light green background
DARK_GREEN = '#006400'  # Dark green for text
WHITE = '#FFFFFF'  # White text

def is_market_hours():
    current_time = datetime.now().time()
    market_start = time(9, 0)  # 9:00 AM
    market_end = time(15, 40)  # 3:40 PM
    return market_start <= current_time <= market_end

def get_next_update_time():
    current_time = datetime.now()
    current_hour = current_time.hour
    current_minute = current_time.minute
    
    # If before 9 AM, return 9:00
    if current_hour < 9:
        return current_time.replace(hour=9, minute=0, second=0, microsecond=0)
    
    # If after 3:40 PM, return next day 9:00
    if current_hour >= 15 and current_minute >= 40:
        next_day = current_time + timedelta(days=1)
        return next_day.replace(hour=9, minute=0, second=0, microsecond=0)
    
    # Calculate next 5-minute interval
    next_minute = ((current_minute // 5) + 1) * 5
    if next_minute >= 60:
        next_hour = current_hour + 1
        next_minute = 0
    else:
        next_hour = current_hour
    
    next_update = current_time.replace(hour=next_hour, minute=next_minute, second=0, microsecond=0)
    
    # If the calculated time is in the past, add 5 minutes
    if next_update <= current_time:
        next_update = next_update + timedelta(minutes=5)
    
    return next_update

# Create signal comparison table
def create_signal_comparison_table():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create table for storing signal comparison data
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS signal_comparison (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date_time TEXT,
        strike_price REAL,
        option_type TEXT,
        ltp REAL,
        oi REAL,
        volume REAL,
        ma_5min REAL,
        ma_15min REAL,
        ma_30min REAL,
        vol_ma_5min REAL,
        vol_ma_15min REAL,
        signal_type TEXT,
        signal_strength INTEGER,
        created_at TEXT
    )
    ''')
    
    conn.commit()
    conn.close()

# Function to insert signal comparison data
def insert_signal_comparison_data(row_data):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    insert_query = '''
    INSERT INTO signal_comparison (
        date_time, strike_price, option_type, ltp, oi, volume,
        ma_5min, ma_15min, ma_30min, vol_ma_5min, vol_ma_15min,
        signal_type, signal_strength, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    '''
    
    cursor.execute(insert_query, row_data)
    conn.commit()
    conn.close()

# Function to check signal sustainability
def check_signal_sustainability(strike_price, option_type, current_time):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get last 5 records for the same strike and option type
    query = '''
    SELECT * FROM signal_comparison 
    WHERE strike_price = ? 
    AND option_type = ? 
    AND date_time <= ?
    ORDER BY date_time DESC 
    LIMIT 5
    '''
    
    cursor.execute(query, (strike_price, option_type, current_time))
    records = cursor.fetchall()
    conn.close()
    
    if len(records) < 5:
        return False
    
    # Check if all records show consistent signal
    signal_type = records[0][11]  # signal_type column
    return all(record[11] == signal_type for record in records)

# SQL query to get top volume strikes with time-wise data
SQL_QUERY = """
WITH timeframes AS (
    SELECT 
        strftime('%H:%M', date_time) as time_window,
        strike_price,
        option_type,
        SUM(volume) AS total_volume,
        SUM(open_interest) AS total_oi,
        AVG(ltp) AS ltp,
        AVG(iv) AS iv,
        COUNT(*) as data_points,
        -- Calculate 5-minute, 15-minute, and 30-minute moving averages
        AVG(AVG(ltp)) OVER (
            PARTITION BY strike_price, option_type 
            ORDER BY strftime('%H:%M', date_time) 
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ) as ma_5min,
        AVG(AVG(ltp)) OVER (
            PARTITION BY strike_price, option_type 
            ORDER BY strftime('%H:%M', date_time) 
            ROWS BETWEEN 5 PRECEDING AND CURRENT ROW
        ) as ma_15min,
        AVG(AVG(ltp)) OVER (
            PARTITION BY strike_price, option_type 
            ORDER BY strftime('%H:%M', date_time) 
            ROWS BETWEEN 9 PRECEDING AND CURRENT ROW
        ) as ma_30min,
        -- Calculate volume moving averages
        AVG(SUM(volume)) OVER (
            PARTITION BY strike_price, option_type 
            ORDER BY strftime('%H:%M', date_time) 
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ) as vol_ma_5min,
        AVG(SUM(volume)) OVER (
            PARTITION BY strike_price, option_type 
            ORDER BY strftime('%H:%M', date_time) 
            ROWS BETWEEN 5 PRECEDING AND CURRENT ROW
        ) as vol_ma_15min
    FROM nifty_option_chain_data
    WHERE date_time LIKE '2025-06-12%'
    AND expiry_date = (
        SELECT expiry_date 
        FROM nifty_option_chain_data 
        WHERE date_time LIKE '2025-06-12%'
        ORDER BY expiry_date 
        LIMIT 1
    )
    GROUP BY time_window, strike_price, option_type
),
ranked_options AS (
    SELECT *,
        ROW_NUMBER() OVER (PARTITION BY time_window, option_type ORDER BY total_volume DESC) AS vol_rank
    FROM timeframes
),
top_options AS (
    SELECT * FROM ranked_options WHERE vol_rank <= 3
),
option_with_lag AS (
    SELECT 
        t.*,
        LAG(t.total_volume) OVER (PARTITION BY t.strike_price, t.option_type ORDER BY t.time_window) AS prev_volume,
        LAG(t.total_oi) OVER (PARTITION BY t.strike_price, t.option_type ORDER BY t.time_window) AS prev_oi,
        LAG(t.ltp) OVER (PARTITION BY t.strike_price, t.option_type ORDER BY t.time_window) AS prev_ltp,
        LAG(t.iv) OVER (PARTITION BY t.strike_price, t.option_type ORDER BY t.time_window) AS prev_iv,
        LAG(t.ma_5min) OVER (PARTITION BY t.strike_price, t.option_type ORDER BY t.time_window) AS prev_ma_5min,
        LAG(t.ma_15min) OVER (PARTITION BY t.strike_price, t.option_type ORDER BY t.time_window) AS prev_ma_15min,
        LAG(t.ma_30min) OVER (PARTITION BY t.strike_price, t.option_type ORDER BY t.time_window) AS prev_ma_30min,
        LAG(t.vol_ma_5min) OVER (PARTITION BY t.strike_price, t.option_type ORDER BY t.time_window) AS prev_vol_ma_5min,
        LAG(t.vol_ma_15min) OVER (PARTITION BY t.strike_price, t.option_type ORDER BY t.time_window) AS prev_vol_ma_15min,
        -- Get opposite option data
        p.total_volume as opposite_volume,
        p.total_oi as opposite_oi,
        p.ltp as opposite_ltp,
        p.iv as opposite_iv,
        p.ma_5min as opposite_ma_5min,
        p.ma_15min as opposite_ma_15min,
        p.ma_30min as opposite_ma_30min,
        p.vol_ma_5min as opposite_vol_ma_5min,
        p.vol_ma_15min as opposite_vol_ma_15min
    FROM top_options t
    LEFT JOIN top_options p ON 
        t.time_window = p.time_window 
        AND t.strike_price = p.strike_price 
        AND t.option_type != p.option_type
),
option_analysis AS (
    SELECT 
        *,
        CASE
            WHEN option_type = 'CE' AND opposite_oi > 0 AND opposite_ltp > 0 AND opposite_iv > 0 THEN
                CASE
                    WHEN total_oi > opposite_oi * 1.5 AND total_volume > opposite_volume * 1.5 
                         AND ltp > opposite_ltp * 1.2 AND iv > opposite_iv * 1.1
                    THEN 'Strong CE Dominance'
                    WHEN total_oi < opposite_oi * 0.7 AND total_volume < opposite_volume * 0.7 
                         AND ltp < opposite_ltp * 0.8 AND iv < opposite_iv * 0.9
                    THEN 'Strong PE Dominance'
                    WHEN ABS(total_oi - opposite_oi) / opposite_oi < 0.2 
                         AND ABS(total_volume - opposite_volume) / opposite_volume < 0.2
                    THEN 'Neutral - Both Options Balanced'
                    ELSE 'Mixed Signals'
                END
            WHEN option_type = 'PE' AND opposite_oi > 0 AND opposite_ltp > 0 AND opposite_iv > 0 THEN
                CASE
                    WHEN total_oi > opposite_oi * 1.5 AND total_volume > opposite_volume * 1.5 
                         AND ltp > opposite_ltp * 1.2 AND iv > opposite_iv * 1.1
                    THEN 'Strong PE Dominance'
                    WHEN total_oi < opposite_oi * 0.7 AND total_volume < opposite_volume * 0.7 
                         AND ltp < opposite_ltp * 0.8 AND iv < opposite_iv * 0.9
                    THEN 'Strong CE Dominance'
                    WHEN ABS(total_oi - opposite_oi) / opposite_oi < 0.2 
                         AND ABS(total_volume - opposite_volume) / opposite_volume < 0.2
                    THEN 'Neutral - Both Options Balanced'
                    ELSE 'Mixed Signals'
                END
            ELSE 'Insufficient Opposite Data'
        END as option_dominance
    FROM option_with_lag
)
SELECT 
    time_window,
    option_type,
    strike_price,
    total_volume,
    prev_volume,
    ROUND(
        CASE 
            WHEN prev_volume > 0 THEN 100.0 * (total_volume - prev_volume) / prev_volume 
            ELSE NULL 
        END, 2
    ) AS volume_pct_change,
    total_oi,
    prev_oi,
    ROUND(
        CASE 
            WHEN prev_oi > 0 THEN 100.0 * (total_oi - prev_oi) / prev_oi 
            ELSE NULL 
        END, 2
    ) AS oi_pct_change,
    ltp,
    prev_ltp,
    ROUND(
        CASE 
            WHEN prev_ltp > 0 THEN 100.0 * (ltp - prev_ltp) / prev_ltp 
            ELSE NULL 
        END, 2
    ) AS ltp_pct_change,
    iv,
    prev_iv,
    ROUND(
        CASE 
            WHEN prev_iv > 0 THEN 100.0 * (iv - prev_iv) / prev_iv 
            ELSE NULL 
        END, 2
    ) AS iv_pct_change,
    -- Opposite option data
    opposite_volume,
    opposite_oi,
    opposite_ltp,
    opposite_iv,
    option_dominance,
    CASE
        WHEN prev_volume IS NOT NULL THEN
            CASE
                -- CALL Unwinding Signal
                WHEN option_type = 'CE' 
                     AND prev_ltp > 0 AND prev_oi > 0
                     AND 100.0 * (ltp - prev_ltp) / prev_ltp < -1
                     AND 100.0 * (total_oi - prev_oi) / prev_oi < -1
                THEN 'CALL Unwinding'
                
                -- PUT Unwinding Signal
                WHEN option_type = 'PE' 
                     AND prev_ltp > 0 AND prev_oi > 0
                     AND 100.0 * (ltp - prev_ltp) / prev_ltp < -1
                     AND 100.0 * (total_oi - prev_oi) / prev_oi < -1
                THEN 'PUT Unwinding'
                
                -- Strong Buy CE Signal with Sustainability Check
                WHEN option_type = 'CE' 
                     AND prev_ltp > 0 AND prev_oi > 0
                     -- Current period increase
                     AND 100.0 * (ltp - prev_ltp) / prev_ltp > 15
                     AND 100.0 * (total_oi - prev_oi) / prev_oi > 15
                     -- Sustainability check over 5 minutes
                     AND ma_5min > prev_ma_5min * 1.1
                     -- Volume confirmation
                     AND vol_ma_5min > prev_vol_ma_5min * 1.2
                     -- Trend confirmation (15 min)
                     AND ma_15min > prev_ma_15min * 1.05
                THEN 'STRONG BUY CE'
                
                -- Strong Buy PE Signal with Sustainability Check
                WHEN option_type = 'PE' 
                     AND prev_ltp > 0 AND prev_oi > 0
                     -- Current period increase
                     AND 100.0 * (ltp - prev_ltp) / prev_ltp > 15
                     AND 100.0 * (total_oi - prev_oi) / prev_oi > 15
                     -- Sustainability check over 5 minutes
                     AND ma_5min > prev_ma_5min * 1.1
                     -- Volume confirmation
                     AND vol_ma_5min > prev_vol_ma_5min * 1.2
                     -- Trend confirmation (15 min)
                     AND ma_15min > prev_ma_15min * 1.05
                THEN 'STRONG BUY PE'
                
                ELSE 'No Clear Signal'
            END
        ELSE 'Insufficient data'
    END AS signal,
    CASE
        -- CALL Unwinding Action
        WHEN option_type = 'CE' 
             AND prev_ltp > 0 AND prev_oi > 0
             AND 100.0 * (ltp - prev_ltp) / prev_ltp < -1
             AND 100.0 * (total_oi - prev_oi) / prev_oi < -1
        THEN 'BUY PE - Unwinding Signal'
        
        -- PUT Unwinding Action (Buy CE)
        WHEN option_type = 'PE' 
             AND prev_ltp > 0 AND prev_oi > 0
             AND 100.0 * (ltp - prev_ltp) / prev_ltp < -1
             AND 100.0 * (total_oi - prev_oi) / prev_oi < -1
        THEN 'BUY CE - PUT Unwinding'
        
        -- Strong Buy CE Action
        WHEN option_type = 'CE' 
             AND prev_ltp > 0 AND prev_oi > 0
             AND 100.0 * (ltp - prev_ltp) / prev_ltp > 15
             AND 100.0 * (total_oi - prev_oi) / prev_oi > 15
        THEN 'STRONG BUY CE'
        
        -- Strong Buy PE Action
        WHEN option_type = 'PE' 
             AND prev_ltp > 0 AND prev_oi > 0
             AND 100.0 * (ltp - prev_ltp) / prev_ltp > 15
             AND 100.0 * (total_oi - prev_oi) / prev_oi > 15
        THEN 'STRONG BUY PE'
        
        ELSE 'No Clear Action'
    END AS action
FROM option_analysis
ORDER BY time_window, option_type, volume_pct_change DESC;
"""

# Add new SQL query for IV analysis
IV_ANALYSIS_QUERY = """
WITH top_strikes AS (
    SELECT 
        strike_price,
        option_type,
        SUM(volume) as total_volume
    FROM nifty_option_chain_data
    WHERE date_time LIKE '2025-06-12%'
    GROUP BY strike_price, option_type
    ORDER BY total_volume DESC
    LIMIT 16  -- 8 for CE and 8 for PE
),
iv_data AS (
    SELECT 
        strftime('%H:%M', date_time) as time_window,
        i.strike_price,
        i.option_type,
        AVG(i.iv) as avg_iv,
        AVG(i.ltp) as avg_ltp,
        SUM(i.volume) as total_volume,
        SUM(i.open_interest) as total_oi,
        COUNT(*) as data_points,
        -- Calculate IV moving averages
        AVG(AVG(i.iv)) OVER (
            PARTITION BY i.strike_price, i.option_type 
            ORDER BY strftime('%H:%M', i.date_time) 
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ) as iv_ma_5min,
        AVG(AVG(i.iv)) OVER (
            PARTITION BY i.strike_price, i.option_type 
            ORDER BY strftime('%H:%M', i.date_time) 
            ROWS BETWEEN 5 PRECEDING AND CURRENT ROW
        ) as iv_ma_15min,
        -- Calculate volume moving averages
        AVG(SUM(i.volume)) OVER (
            PARTITION BY i.strike_price, i.option_type 
            ORDER BY strftime('%H:%M', i.date_time) 
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ) as vol_ma_5min,
        AVG(SUM(i.volume)) OVER (
            PARTITION BY i.strike_price, i.option_type 
            ORDER BY strftime('%H:%M', i.date_time) 
            ROWS BETWEEN 5 PRECEDING AND CURRENT ROW
        ) as vol_ma_15min,
        -- Calculate OI moving averages
        AVG(SUM(i.open_interest)) OVER (
            PARTITION BY i.strike_price, i.option_type 
            ORDER BY strftime('%H:%M', i.date_time) 
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ) as oi_ma_5min,
        AVG(SUM(i.open_interest)) OVER (
            PARTITION BY i.strike_price, i.option_type 
            ORDER BY strftime('%H:%M', i.date_time) 
            ROWS BETWEEN 5 PRECEDING AND CURRENT ROW
        ) as oi_ma_15min,
        -- Calculate IV percentiles
        PERCENT_RANK() OVER (
            PARTITION BY strftime('%H:%M', i.date_time)
            ORDER BY i.iv
        ) as iv_percentile,
        -- Calculate volume percentiles
        PERCENT_RANK() OVER (
            PARTITION BY strftime('%H:%M', i.date_time)
            ORDER BY SUM(i.volume)
        ) as volume_percentile,
        -- Calculate OI percentiles
        PERCENT_RANK() OVER (
            PARTITION BY strftime('%H:%M', i.date_time)
            ORDER BY SUM(i.open_interest)
        ) as oi_percentile,
        -- Calculate previous values
        LAG(AVG(i.iv)) OVER (
            PARTITION BY i.strike_price, i.option_type 
            ORDER BY strftime('%H:%M', i.date_time)
        ) as prev_iv,
        LAG(AVG(i.ltp)) OVER (
            PARTITION BY i.strike_price, i.option_type 
            ORDER BY strftime('%H:%M', i.date_time)
        ) as prev_ltp,
        LAG(SUM(i.volume)) OVER (
            PARTITION BY i.strike_price, i.option_type 
            ORDER BY strftime('%H:%M', i.date_time)
        ) as prev_volume,
        LAG(SUM(i.open_interest)) OVER (
            PARTITION BY i.strike_price, i.option_type 
            ORDER BY strftime('%H:%M', i.date_time)
        ) as prev_oi
    FROM nifty_option_chain_data i
    INNER JOIN top_strikes ts 
        ON i.strike_price = ts.strike_price 
        AND i.option_type = ts.option_type
    WHERE i.date_time LIKE '2025-06-12%'
    AND i.expiry_date = (
        SELECT expiry_date 
        FROM nifty_option_chain_data 
        WHERE date_time LIKE '2025-06-12%'
        ORDER BY expiry_date 
        LIMIT 1
    )
    GROUP BY time_window, i.strike_price, i.option_type
),
iv_with_changes AS (
    SELECT 
        *,
        CASE
            WHEN prev_iv > 0 THEN
                ROUND(100.0 * (avg_iv - prev_iv) / prev_iv, 2)
            ELSE NULL
        END as iv_pct_change,
        CASE
            WHEN prev_volume > 0 THEN
                ROUND(100.0 * (total_volume - prev_volume) / prev_volume, 2)
            ELSE NULL
        END as volume_pct_change,
        CASE
            WHEN prev_oi > 0 THEN
                ROUND(100.0 * (total_oi - prev_oi) / prev_oi, 2)
            ELSE NULL
        END as oi_pct_change
    FROM iv_data
),
iv_analysis AS (
    SELECT 
        *,
        CASE
            WHEN iv_pct_change > 15 THEN 'High IV Spike'
            WHEN iv_pct_change < -15 THEN 'Low IV Spike'
            WHEN iv_percentile > 0.8 THEN 'High IV Percentile'
            WHEN iv_percentile < 0.2 THEN 'Low IV Percentile'
            ELSE 'Normal IV'
        END as iv_signal,
        CASE
            WHEN avg_ltp > prev_ltp AND iv_pct_change < 0 THEN 'Price Up IV Down'
            WHEN avg_ltp > prev_ltp AND iv_pct_change > 0 THEN 'Price Up IV Up'
            WHEN avg_ltp < prev_ltp AND iv_pct_change < 0 THEN 'Price Down IV Down'
            WHEN avg_ltp < prev_ltp AND iv_pct_change > 0 THEN 'Price Down IV Up'
            ELSE 'Neutral'
        END as price_iv_relationship,
        CASE
            WHEN option_type = 'CE' AND avg_ltp > prev_ltp AND iv_pct_change > 0 AND oi_pct_change < 0 THEN 'Potential Short Covering'
            WHEN option_type = 'CE' AND avg_ltp > prev_ltp AND iv_pct_change > 0 AND oi_pct_change > 0 THEN 'Possible Hedging'
            WHEN option_type = 'CE' AND avg_ltp > prev_ltp AND iv_pct_change > 15 AND volume_pct_change > 100 THEN 'Smart Money Activity'
            WHEN option_type = 'CE' AND avg_ltp > prev_ltp AND iv_pct_change > 0 AND volume_percentile > 0.8 THEN 'Failed Breakout Risk'
            ELSE 'Normal Activity'
        END as market_behavior
    FROM iv_with_changes
)
SELECT 
    time_window,
    option_type,
    strike_price,
    ROUND(avg_iv, 2) as iv,
    ROUND(iv_pct_change, 2) as iv_change_pct,
    ROUND(iv_percentile * 100, 2) as iv_percentile,
    ROUND(avg_ltp, 2) as ltp,
    total_volume,
    total_oi,
    ROUND(volume_pct_change, 2) as volume_change_pct,
    ROUND(oi_pct_change, 2) as oi_change_pct,
    iv_signal,
    price_iv_relationship,
    market_behavior,
    CASE
        WHEN market_behavior = 'Potential Short Covering' THEN 'Watch for Reversal - Bears Closing Positions'
        WHEN market_behavior = 'Possible Hedging' THEN 'Institutional Activity - Not Necessarily Bullish'
        WHEN market_behavior = 'Smart Money Activity' THEN 'High Risk - Possible Fake Rally'
        WHEN market_behavior = 'Failed Breakout Risk' THEN 'Caution - Market May Reject Level'
        WHEN iv_signal = 'High IV Spike' AND price_iv_relationship IN ('Price Down IV Up', 'Price Up IV Up') 
        THEN 'Strong Reversal Signal'
        WHEN iv_signal = 'Low IV Spike' AND price_iv_relationship IN ('Price Down IV Down', 'Price Up IV Down')
        THEN 'Potential Continuation'
        WHEN iv_percentile > 80 AND iv_pct_change > 0
        THEN 'High IV - Consider Selling'
        WHEN iv_percentile < 20 AND iv_pct_change < 0
        THEN 'Low IV - Consider Buying'
        ELSE 'Monitor'
    END as trading_signal
FROM iv_analysis
ORDER BY time_window, option_type, strike_price;
"""

# Add new SQL query for volume analysis
VOLUME_ANALYSIS_QUERY = """
WITH top_strikes AS (
    SELECT 
        strike_price,
        option_type,
        SUM(volume) as total_volume
    FROM nifty_option_chain_data
    WHERE date_time LIKE '2025-06-12%'
    GROUP BY strike_price, option_type
    ORDER BY total_volume DESC
    LIMIT 16  -- 8 for CE and 8 for PE
),
volume_data AS (
    SELECT 
        strftime('%H:%M', date_time) as time_window,
        v.strike_price,
        v.option_type,
        SUM(v.volume) as total_volume,
        SUM(v.open_interest) as total_oi,
        AVG(v.ltp) as avg_ltp,
        COUNT(*) as data_points,
        -- Calculate volume moving averages
        AVG(SUM(v.volume)) OVER (
            PARTITION BY v.strike_price, v.option_type 
            ORDER BY strftime('%H:%M', v.date_time) 
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ) as vol_ma_5min,
        AVG(SUM(v.volume)) OVER (
            PARTITION BY v.strike_price, v.option_type 
            ORDER BY strftime('%H:%M', v.date_time) 
            ROWS BETWEEN 5 PRECEDING AND CURRENT ROW
        ) as vol_ma_15min,
        -- Calculate OI moving averages
        AVG(SUM(v.open_interest)) OVER (
            PARTITION BY v.strike_price, v.option_type 
            ORDER BY strftime('%H:%M', v.date_time) 
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ) as oi_ma_5min,
        AVG(SUM(v.open_interest)) OVER (
            PARTITION BY v.strike_price, v.option_type 
            ORDER BY strftime('%H:%M', v.date_time) 
            ROWS BETWEEN 5 PRECEDING AND CURRENT ROW
        ) as oi_ma_15min,
        -- Calculate volume percentiles
        PERCENT_RANK() OVER (
            PARTITION BY strftime('%H:%M', v.date_time)
            ORDER BY SUM(v.volume)
        ) as volume_percentile,
        -- Calculate OI percentiles
        PERCENT_RANK() OVER (
            PARTITION BY strftime('%H:%M', v.date_time)
            ORDER BY SUM(v.open_interest)
        ) as oi_percentile,
        -- Calculate previous values
        LAG(SUM(v.volume)) OVER (
            PARTITION BY v.strike_price, v.option_type 
            ORDER BY strftime('%H:%M', v.date_time)
        ) as prev_volume,
        LAG(SUM(v.open_interest)) OVER (
            PARTITION BY v.strike_price, v.option_type 
            ORDER BY strftime('%H:%M', v.date_time)
        ) as prev_oi
    FROM nifty_option_chain_data v
    INNER JOIN top_strikes ts 
        ON v.strike_price = ts.strike_price 
        AND v.option_type = ts.option_type
    WHERE v.date_time LIKE '2025-06-12%'
    AND v.expiry_date = (
        SELECT expiry_date 
        FROM nifty_option_chain_data 
        WHERE date_time LIKE '2025-06-12%'
        ORDER BY expiry_date 
        LIMIT 1
    )
    GROUP BY time_window, v.strike_price, v.option_type
),
volume_with_changes AS (
    SELECT 
        *,
        CASE
            WHEN prev_volume > 0 THEN
                ROUND(100.0 * (total_volume - prev_volume) / prev_volume, 2)
            ELSE NULL
        END as volume_pct_change,
        CASE
            WHEN prev_oi > 0 THEN
                ROUND(100.0 * (total_oi - prev_oi) / prev_oi, 2)
            ELSE NULL
        END as oi_pct_change
    FROM volume_data
),
volume_analysis AS (
    SELECT 
        *,
        CASE
            WHEN volume_pct_change > 100 AND oi_pct_change > 10 THEN 'New Position Building'
            WHEN volume_pct_change > 100 AND oi_pct_change < -10 THEN 'Position Squaring Off'
            WHEN volume_pct_change > 100 AND ABS(oi_pct_change) <= 10 THEN 'High Volume - Neutral OI'
            WHEN volume_percentile > 0.8 THEN 'Unusually High Volume'
            WHEN volume_percentile < 0.2 THEN 'Unusually Low Volume'
            ELSE 'Normal Volume'
        END as volume_signal,
        CASE
            WHEN oi_pct_change > 20 THEN 'Strong OI Build-up'
            WHEN oi_pct_change < -20 THEN 'Strong OI Unwinding'
            WHEN oi_pct_change > 10 THEN 'Moderate OI Build-up'
            WHEN oi_pct_change < -10 THEN 'Moderate OI Unwinding'
            ELSE 'Neutral OI'
        END as oi_signal
    FROM volume_with_changes
)
SELECT 
    time_window,
    option_type,
    strike_price,
    total_volume,
    volume_pct_change,
    ROUND(volume_percentile * 100, 2) as volume_percentile,
    total_oi,
    oi_pct_change,
    ROUND(oi_percentile * 100, 2) as oi_percentile,
    ROUND(avg_ltp, 2) as ltp,
    volume_signal,
    oi_signal,
    CASE
        WHEN volume_signal = 'New Position Building' AND oi_signal IN ('Strong OI Build-up', 'Moderate OI Build-up')
        THEN 'Strong Buy Signal'
        WHEN volume_signal = 'Position Squaring Off' AND oi_signal IN ('Strong OI Unwinding', 'Moderate OI Unwinding')
        THEN 'Strong Sell Signal'
        WHEN volume_signal = 'Unusually High Volume' AND oi_pct_change > 0
        THEN 'Potential Breakout'
        WHEN volume_signal = 'Unusually Low Volume' AND oi_pct_change < 0
        THEN 'Potential Reversal'
        ELSE 'Monitor'
    END as trading_signal
FROM volume_analysis
ORDER BY time_window, option_type, strike_price;
"""

# --- Data Fetching ---
async def fetch_nse_option_chain():
    url_oc = "https://www.nseindia.com/option-chain"
    url_nf = 'https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY'
    headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'accept-language': 'en,gu;q=0.9,hi;q=0.8',
        'accept-encoding': 'gzip, deflate, br'
    }

    try:
        async with aiohttp.ClientSession() as session:
            # First request to get cookies
            async with session.get(url_oc, headers=headers, timeout=10) as resp:
                if resp.status != 200:
                    print(f"Error accessing NSE website: {resp.status}")
                    return None
                cookies = {k: v.value for k, v in resp.cookies.items()}
                print("Successfully obtained cookies")
            
            # Second request to get data
            async with session.get(url_nf, headers=headers, cookies=cookies, timeout=30) as resp:
                if resp.status != 200:
                    print(f"Error fetching option chain data: {resp.status}")
                    return None
                data = await resp.json()
                print(f"Successfully fetched data from NSE at {datetime.now()}")
                print("Data keys:", data.keys() if data else "None")
                return data
    except Exception as e:
        print(f"Error in fetch_nse_option_chain: {e}")
        return None

def extract_option_chain_data(raw_data, expiry_date):
    try:
        if not raw_data:
            print("Error: Raw data is None")
            return []
            
        if 'records' not in raw_data:
            print("Error: 'records' key not found in raw data")
            print("Raw data keys:", raw_data.keys())
            return []
            
        if 'data' not in raw_data['records']:
            print("Error: 'data' key not found in records")
            print("Records keys:", raw_data['records'].keys())
            return []
            
        records = raw_data['records']['data']
        if not records:
            print("Error: No data in records")
            return []
            
        print(f"Processing {len(records)} records from NSE")
        rows = []
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        for row in records:
            try:
                if not isinstance(row, dict):
                    print(f"Warning: Invalid row format: {type(row)}")
                    continue
                    
                if 'expiryDate' not in row:
                    print(f"Warning: No expiry date in row: {row}")
                    continue
                    
                if row.get('expiryDate') != expiry_date:
                    continue
                    
                ce = row.get('CE', {})
                pe = row.get('PE', {})
                
                if not ce and not pe:
                    continue
                    
                strike_price = ce.get('strikePrice') if ce else pe.get('strikePrice')
                if not strike_price:
                    continue
                
                underlying_value = raw_data['records'].get('underlyingValue', 0.0)
                
                if ce:
                    rows.append((
                        current_time,
                        strike_price,
                        'CE',
                        expiry_date,
                        ce.get('openInterest', 0),
                        ce.get('changeinOpenInterest', 0),
                        ce.get('totalTradedVolume', 0),
                        ce.get('impliedVolatility', 0.0),
                        ce.get('lastPrice', 0.0),
                        ce.get('change', 0.0),
                        ce.get('totalBuyQuantity', 0),
                        ce.get('totalSellQuantity', 0),
                        ce.get('bidQty', 0),
                        ce.get('bidprice', 0.0),
                        ce.get('askQty', 0),
                        ce.get('askPrice', 0.0),
                        underlying_value
                    ))
                    
                if pe:
                    rows.append((
                        current_time,
                        strike_price,
                        'PE',
                        expiry_date,
                        pe.get('openInterest', 0),
                        pe.get('changeinOpenInterest', 0),
                        pe.get('totalTradedVolume', 0),
                        pe.get('impliedVolatility', 0.0),
                        pe.get('lastPrice', 0.0),
                        pe.get('change', 0.0),
                        pe.get('totalBuyQuantity', 0),
                        pe.get('totalSellQuantity', 0),
                        pe.get('bidQty', 0),
                        pe.get('bidprice', 0.0),
                        pe.get('askQty', 0),
                        pe.get('askPrice', 0.0),
                        underlying_value
                    ))
            except Exception as e:
                print(f"Error processing row: {e}")
                continue
        
        print(f"Successfully extracted {len(rows)} rows of data")
        if len(rows) == 0:
            print("Warning: No valid rows extracted. Raw data sample:", raw_data['records']['data'][:2] if raw_data['records']['data'] else "No data")
        return rows
        
    except Exception as e:
        print(f"Error in extract_option_chain_data: {e}")
        print("Raw data structure:", raw_data.keys() if raw_data else "None")
        return []

def insert_data_to_db(rows):
    if not rows:
        print("No data to insert")
        return
        
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Create table if it doesn't exist
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS nifty_option_chain_data (
            date_time TEXT,
            strike_price REAL,
            option_type TEXT,
            expiry_date TEXT,
            open_interest INTEGER,
            changein_oi INTEGER,
            volume INTEGER,
            iv REAL,
            ltp REAL,
            net_change REAL,
            total_buy_quantity INTEGER,
            total_sell_quantity INTEGER,
            bid_qty INTEGER,
            bid_price REAL,
            ask_qty INTEGER,
            ask_price REAL,
            underlying_value REAL
        )
        ''')
        
        insert_query = '''
        INSERT INTO nifty_option_chain_data (
            date_time, strike_price, option_type, expiry_date, open_interest, changein_oi, volume, iv, ltp, net_change,
            total_buy_quantity, total_sell_quantity, bid_qty, bid_price, ask_qty, ask_price, underlying_value
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''
        
        cursor.executemany(insert_query, rows)
        conn.commit()
        print(f"Successfully inserted {len(rows)} rows into database")
    except Exception as e:
        print(f"Error inserting data: {e}")
    finally:
        conn.close()

def fetch_sql_results():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Verify table exists and has data
        cursor.execute("SELECT COUNT(*) FROM nifty_option_chain_data")
        count = cursor.fetchone()[0]
        print(f"Total rows in database: {count}")
        
        if count == 0:
            print("No data in database")
            return pd.DataFrame()
            
        df = pd.read_sql_query(SQL_QUERY, conn)
        print(f"Successfully fetched {len(df)} rows for analysis")
        return df
    except Exception as e:
        print(f"Error fetching data: {e}")
        return pd.DataFrame()
    finally:
        conn.close()

# --- GUI ---
class NiftyApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Nifty Option Chain Dashboard")
        
        # Make window full screen
        self.root.state('zoomed')
        
        # Configure root window background
        self.root.configure(bg=GREEN_BG)
        
        # Configure style
        style = ttk.Style()
        style.configure('TNotebook', background=GREEN_BG)
        style.configure('TNotebook.Tab', background=GREEN_BG, foreground=DARK_GREEN)
        style.configure('TFrame', background=GREEN_BG)
        style.configure('Treeview', background=WHITE, fieldbackground=WHITE)
        style.configure('Treeview.Heading', background=GREEN_BG, foreground=DARK_GREEN)
        
        # Create main container
        self.main_container = ttk.Frame(root)
        self.main_container.pack(expand=1, fill="both", padx=10, pady=10)
        
        # Create tabs
        self.tabs = ttk.Notebook(self.main_container)
        self.tabs.pack(expand=1, fill="both")

        # Add status label with green background
        self.status_label = ttk.Label(root, text="", font=('Arial', 10, 'bold'), 
                                    background=GREEN_BG, foreground=DARK_GREEN)
        self.status_label.pack(pady=5)

        # Create frames for each tab
        self.frames = []
        self.tables = []
        
        # Create main data view tab
        frame = ttk.Frame(self.tabs)
        self.tabs.add(frame, text="Option Chain Data")
        self.frames.append(frame)

        # Create treeview
        tree = ttk.Treeview(frame, show="headings", style='Treeview')
        tree.pack(expand=1, fill="both")
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        scrollbar.pack(side="right", fill="y")
        tree.configure(yscrollcommand=scrollbar.set)
        
        self.tables.append(tree)

        # Create IV Analysis tab
        iv_frame = ttk.Frame(self.tabs)
        self.tabs.add(iv_frame, text="IV Analysis")
        self.frames.append(iv_frame)

        # Create treeview for IV analysis
        iv_tree = ttk.Treeview(iv_frame, show="headings", style='Treeview')
        iv_tree.pack(expand=1, fill="both")
        
        # Add scrollbar for IV analysis
        iv_scrollbar = ttk.Scrollbar(iv_frame, orient="vertical", command=iv_tree.yview)
        iv_scrollbar.pack(side="right", fill="y")
        iv_tree.configure(yscrollcommand=iv_scrollbar.set)
        
        self.tables.append(iv_tree)

        # Create Volume Analysis tab
        volume_frame = ttk.Frame(self.tabs)
        self.tabs.add(volume_frame, text="Volume Data")
        self.frames.append(volume_frame)

        # Create treeview for volume analysis
        volume_tree = ttk.Treeview(volume_frame, show="headings", style='Treeview')
        volume_tree.pack(expand=1, fill="both")
        
        # Add scrollbar for volume analysis
        volume_scrollbar = ttk.Scrollbar(volume_frame, orient="vertical", command=volume_tree.yview)
        volume_scrollbar.pack(side="right", fill="y")
        volume_tree.configure(yscrollcommand=volume_scrollbar.set)
        
        self.tables.append(volume_tree)

        self.run_cycle()

    def display_table(self, frame, df):
        try:
            idx = self.frames.index(frame)
            tree = self.tables[idx]

            # Clear existing widgets
            for widget in frame.winfo_children():
                widget.destroy()

            # Create new Treeview
            new_tree = ttk.Treeview(frame, show="headings", style='Treeview')
            
            # Create and configure scrollbar
            scrollbar = ttk.Scrollbar(frame, orient="vertical", command=new_tree.yview)
            new_tree.configure(yscrollcommand=scrollbar.set)
            
            # Pack widgets
            new_tree.pack(side="left", expand=1, fill="both")
            scrollbar.pack(side="right", fill="y")

            # Define columns with their display names and widths
            columns = {
                'fetched_date': ('Date', 100),
                'time_window': ('Time', 80),
                'option_type': ('Type', 60),
                'strike_price': ('Strike', 80),
                'total_volume': ('Volume', 100),
                'volume_pct_change': ('Vol %', 80),
                'total_oi': ('OI', 100),
                'oi_pct_change': ('OI %', 80),
                'ltp': ('LTP', 80),
                'ltp_pct_change': ('LTP %', 80),
                'iv': ('IV', 80),
                'iv_pct_change': ('IV %', 80),
                'signal': ('Signal', 150),
                'action': ('Action', 150)
            }

            # Configure columns
            new_tree["columns"] = list(columns.keys())
            for col, (display_name, width) in columns.items():
                new_tree.heading(col, text=display_name, anchor="center")
                new_tree.column(col, width=width, anchor="center", stretch=True)

            # Insert data with alternating row colors and special highlighting
            for i, (_, row) in enumerate(df.iterrows()):
                # Default tag for alternating rows
                tag = 'even' if i % 2 == 0 else 'odd'
                
                # Add special tags for different signals
                if row['signal'] == 'CALL Unwinding':
                    tag = 'call_unwind'
                elif row['signal'] == 'PUT Unwinding':
                    tag = 'put_unwind'
                elif row['signal'] == 'No Clear Signal':
                    tag = 'no_signal'
                elif row['signal'] == 'STRONG BUY CE':
                    tag = 'strong_buy_ce'
                elif row['signal'] == 'STRONG BUY PE':
                    tag = 'strong_buy_pe'
                elif row['signal'] == 'Insufficient data':
                    tag = 'insufficient_data'
                
                # Add fetched date to the row data
                row_data = list(row[list(columns.keys())[1:]])  # Get all columns except fetched_date
                row_data.insert(0, datetime.now().strftime('%Y-%m-%d'))  # Insert fetched date at the beginning
                new_tree.insert("", "end", values=row_data, tags=(tag,))

            # Configure tag colors and fonts
            new_tree.tag_configure('even', background='#E8F5E9', font=('Arial', 8))
            new_tree.tag_configure('odd', background='#C8E6C9', font=('Arial', 8))
            new_tree.tag_configure('call_unwind', background='#FF0000', foreground='#FFFFFF', font=('Arial Black', 8))
            new_tree.tag_configure('put_unwind', background='#006400', foreground='#FFFFFF', font=('Arial Black', 8))
            new_tree.tag_configure('no_signal', background='#FFD700', foreground='#000000', font=('Arial Black', 8))
            new_tree.tag_configure('strong_buy_ce', background='#006400', foreground='#FFFFFF', font=('Arial Black', 8))
            new_tree.tag_configure('strong_buy_pe', background='#FF0000', foreground='#FFFFFF', font=('Arial Black', 8))
            new_tree.tag_configure('insufficient_data', background='#000000', foreground='#FFFFFF', font=('Arial Black', 8))

            # Configure default font for Treeview
            style = ttk.Style()
            style.configure('Treeview', font=('Arial', 8))
            style.configure('Treeview.Heading', font=('Arial', 8, 'bold'))

            # Update the table reference
            self.tables[idx] = new_tree

            # Print debug information
            print(f"Displayed {len(df)} rows with {len(columns)} columns")
            print("Column configuration:", columns)
            
        except Exception as e:
            print(f"Error in display_table: {e}")

    def display_iv_analysis(self, frame, df):
        try:
            idx = self.frames.index(frame)
            tree = self.tables[idx]

            # Clear existing widgets
            for widget in frame.winfo_children():
                widget.destroy()

            # Create new Treeview
            new_tree = ttk.Treeview(frame, show="headings", style='Treeview')
            
            # Create and configure scrollbar
            scrollbar = ttk.Scrollbar(frame, orient="vertical", command=new_tree.yview)
            new_tree.configure(yscrollcommand=scrollbar.set)
            
            # Pack widgets
            new_tree.pack(side="left", expand=1, fill="both")
            scrollbar.pack(side="right", fill="y")

            # Define columns with their display names and widths
            columns = {
                'time_window': ('Time', 80),
                'option_type': ('Type', 60),
                'strike_price': ('Strike', 80),
                'iv': ('IV', 80),
                'iv_change_pct': ('IV %', 80),
                'iv_percentile': ('IV %ile', 80),
                'ltp': ('LTP', 80),
                'total_volume': ('Volume', 100),
                'total_oi': ('OI', 100),
                'iv_signal': ('IV Signal', 120),
                'price_iv_relationship': ('Price-IV', 120),
                'trading_signal': ('Signal', 150)
            }

            # Configure columns
            new_tree["columns"] = list(columns.keys())
            for col, (display_name, width) in columns.items():
                new_tree.heading(col, text=display_name, anchor="center")
                new_tree.column(col, width=width, anchor="center", stretch=True)

            # Insert data with alternating row colors and special highlighting
            for i, (_, row) in enumerate(df.iterrows()):
                # Default tag for alternating rows
                tag = 'even' if i % 2 == 0 else 'odd'
                
                # Add special tags for different signals
                if row['iv_signal'] == 'High IV Spike':
                    tag = 'high_iv'
                elif row['iv_signal'] == 'Low IV Spike':
                    tag = 'low_iv'
                elif row['trading_signal'] == 'Strong Reversal Signal':
                    tag = 'reversal'
                elif row['trading_signal'] == 'High IV - Consider Selling':
                    tag = 'sell_signal'
                elif row['trading_signal'] == 'Low IV - Consider Buying':
                    tag = 'buy_signal'
                
                # Convert row values to list and handle None values
                values = []
                for col in columns.keys():
                    val = row[col]
                    if pd.isna(val):
                        values.append('')
                    else:
                        values.append(str(val))
                
                new_tree.insert("", "end", values=values, tags=(tag,))

            # Configure tag colors and fonts
            new_tree.tag_configure('even', background='#E8F5E9', font=('Arial', 8))
            new_tree.tag_configure('odd', background='#C8E6C9', font=('Arial', 8))
            new_tree.tag_configure('high_iv', background='#FF0000', foreground='#FFFFFF', font=('Arial Black', 8))
            new_tree.tag_configure('low_iv', background='#006400', foreground='#FFFFFF', font=('Arial Black', 8))
            new_tree.tag_configure('reversal', background='#FFD700', foreground='#000000', font=('Arial Black', 8))
            new_tree.tag_configure('sell_signal', background='#FF4500', foreground='#FFFFFF', font=('Arial Black', 8))
            new_tree.tag_configure('buy_signal', background='#32CD32', foreground='#FFFFFF', font=('Arial Black', 8))

            # Update the table reference
            self.tables[idx] = new_tree

            print(f"Displayed {len(df)} rows in IV analysis grid")
            
        except Exception as e:
            print(f"Error in display_iv_analysis: {e}")
            print("DataFrame info:")
            print(df.info())
            print("\nDataFrame head:")
            print(df.head())

    def display_volume_analysis(self, frame, df):
        try:
            idx = self.frames.index(frame)
            tree = self.tables[idx]

            # Clear existing widgets
            for widget in frame.winfo_children():
                widget.destroy()

            # Create new Treeview
            new_tree = ttk.Treeview(frame, show="headings", style='Treeview')
            
            # Create and configure scrollbar
            scrollbar = ttk.Scrollbar(frame, orient="vertical", command=new_tree.yview)
            new_tree.configure(yscrollcommand=scrollbar.set)
            
            # Pack widgets
            new_tree.pack(side="left", expand=1, fill="both")
            scrollbar.pack(side="right", fill="y")

            # Define columns with their display names and widths
            columns = {
                'time_window': ('Time', 80),
                'option_type': ('Type', 60),
                'strike_price': ('Strike', 80),
                'total_volume': ('Volume', 100),
                'volume_pct_change': ('Vol %', 80),
                'volume_percentile': ('Vol %ile', 80),
                'total_oi': ('OI', 100),
                'oi_pct_change': ('OI %', 80),
                'oi_percentile': ('OI %ile', 80),
                'ltp': ('LTP', 80),
                'volume_signal': ('Volume Signal', 150),
                'oi_signal': ('OI Signal', 150),
                'trading_signal': ('Signal', 150)
            }

            # Configure columns
            new_tree["columns"] = list(columns.keys())
            for col, (display_name, width) in columns.items():
                new_tree.heading(col, text=display_name, anchor="center")
                new_tree.column(col, width=width, anchor="center", stretch=True)

            # Insert data with alternating row colors and special highlighting
            for i, (_, row) in enumerate(df.iterrows()):
                # Default tag for alternating rows
                tag = 'even' if i % 2 == 0 else 'odd'
                
                # Add special tags for different signals
                if row['volume_signal'] == 'New Position Building':
                    tag = 'new_position'
                elif row['volume_signal'] == 'Position Squaring Off':
                    tag = 'squaring_off'
                elif row['trading_signal'] == 'Strong Buy Signal':
                    tag = 'strong_buy'
                elif row['trading_signal'] == 'Strong Sell Signal':
                    tag = 'strong_sell'
                elif row['trading_signal'] == 'Potential Breakout':
                    tag = 'breakout'
                elif row['trading_signal'] == 'Potential Reversal':
                    tag = 'reversal'
                
                # Convert row values to list and handle None values
                values = []
                for col in columns.keys():
                    val = row[col]
                    if pd.isna(val):
                        values.append('')
                    else:
                        values.append(str(val))
                
                new_tree.insert("", "end", values=values, tags=(tag,))

            # Configure tag colors and fonts
            new_tree.tag_configure('even', background='#E8F5E9', font=('Arial', 8))
            new_tree.tag_configure('odd', background='#C8E6C9', font=('Arial', 8))
            new_tree.tag_configure('new_position', background='#006400', foreground='#FFFFFF', font=('Arial Black', 8))
            new_tree.tag_configure('squaring_off', background='#FF0000', foreground='#FFFFFF', font=('Arial Black', 8))
            new_tree.tag_configure('strong_buy', background='#32CD32', foreground='#FFFFFF', font=('Arial Black', 8))
            new_tree.tag_configure('strong_sell', background='#FF4500', foreground='#FFFFFF', font=('Arial Black', 8))
            new_tree.tag_configure('breakout', background='#FFD700', foreground='#000000', font=('Arial Black', 8))
            new_tree.tag_configure('reversal', background='#FF69B4', foreground='#FFFFFF', font=('Arial Black', 8))

            # Update the table reference
            self.tables[idx] = new_tree

            print(f"Displayed {len(df)} rows in volume analysis grid")
            
        except Exception as e:
            print(f"Error in display_volume_analysis: {e}")
            print("DataFrame info:")
            print(df.info())
            print("\nDataFrame head:")
            print(df.head())

    def run_cycle(self):
        try:
            current_time = datetime.now()
            
            # Check if we should fetch new data (only during market hours)
            if is_market_hours():
                print(f"\nRunning data fetch cycle at {current_time}")
                
                # Run the fetch and store
                asyncio.run(self.fetch_store_display())
                
                # Calculate next update time (5 minutes from now)
                next_update = current_time + timedelta(minutes=5)
                next_update = next_update.replace(second=0, microsecond=0)
                
                # Update status label
                self.status_label.config(
                    text=f"Last data fetch: {current_time.strftime('%H:%M:%S')} - Next fetch at {next_update.strftime('%H:%M:%S')}"
                )
                
                # Schedule next fetch
                delay = (next_update - current_time).total_seconds() * 1000
                print(f"Scheduling next data fetch in {delay/1000:.1f} seconds")
                self.root.after(int(delay), self.run_cycle)
                
            else:
                # Even if market is closed, continue analyzing existing data
                print(f"\nRunning analysis cycle at {current_time}")
                
                # Fetch and display existing data for all tabs
                df = fetch_sql_results()
                if not df.empty:
                    self.root.after_idle(lambda: self.display_table(self.frames[0], df))
                    print(f"Displayed {len(df)} rows in main grid at {current_time}")
                
                # Fetch and display IV analysis
                try:
                    conn = sqlite3.connect(DB_PATH)
                    print("Executing IV analysis query...")
                    iv_df = pd.read_sql_query(IV_ANALYSIS_QUERY, conn)
                    
                    # Check data availability for volume analysis
                    print("\nChecking data availability...")
                    cursor = conn.cursor()
                    
                    # Check available dates
                    cursor.execute("""
                        SELECT DISTINCT date(date_time) as date
                        FROM nifty_option_chain_data
                        ORDER BY date
                    """)
                    available_dates = cursor.fetchall()
                    print("Available dates in database:", [date[0] for date in available_dates])
                    
                    # Check data for 2025-06-12
                    cursor.execute("""
                        SELECT COUNT(*) as count
                        FROM nifty_option_chain_data
                        WHERE date_time LIKE '2025-06-12%'
                    """)
                    count = cursor.fetchone()[0]
                    print(f"Records found for 2025-06-12: {count}")
                    
                    if count > 0:
                        # Check expiry dates for 2025-06-12
                        cursor.execute("""
                            SELECT DISTINCT expiry_date
                            FROM nifty_option_chain_data
                            WHERE date_time LIKE '2025-06-12%'
                            ORDER BY expiry_date
                        """)
                        expiry_dates = cursor.fetchall()
                        print("Available expiry dates:", [date[0] for date in expiry_dates])
                    
                    # Fetch and display volume analysis
                    print("\nExecuting volume analysis query...")
                    volume_df = pd.read_sql_query(VOLUME_ANALYSIS_QUERY, conn)
                    conn.close()
                    
                    if not iv_df.empty:
                        print(f"IV Analysis: Found {len(iv_df)} rows")
                        self.root.after_idle(lambda: self.display_iv_analysis(self.frames[1], iv_df))
                        print(f"Displayed {len(iv_df)} rows in IV analysis grid")
                    
                    if not volume_df.empty:
                        print(f"Volume Analysis: Found {len(volume_df)} rows")
                        self.root.after_idle(lambda: self.display_volume_analysis(self.frames[2], volume_df))
                        print(f"Displayed {len(volume_df)} rows in volume analysis grid")
                    else:
                        print("Volume Analysis: No data found for 2025-06-12")
                        print("Please check if data exists for this date in the database")
                except Exception as e:
                    print(f"Error in analysis: {e}")
                    print("Full error details:", str(e))
                
                # Calculate next analysis update (every 5 minutes)
                next_analysis = current_time + timedelta(minutes=5)
                next_analysis = next_analysis.replace(second=0, microsecond=0)
                
                # Update status label
                if current_time.hour >= 15 and current_time.minute >= 40:
                    self.status_label.config(
                        text=f"Market Closed - Last fetch: {current_time.strftime('%H:%M:%S')} - Next analysis at {next_analysis.strftime('%H:%M:%S')}"
                    )
                else:
                    self.status_label.config(
                        text=f"Market Closed - Next analysis at {next_analysis.strftime('%H:%M:%S')}"
                    )
                
                # Schedule next analysis
                delay = (next_analysis - current_time).total_seconds() * 1000
                if delay > 0:
                    self.root.after(int(delay), self.run_cycle)
                else:
                    self.root.after(1000, self.run_cycle)
                    
        except Exception as e:
            print(f"Error in run_cycle: {e}")
            # If there's an error, try again in 5 seconds
            self.root.after(5000, self.run_cycle)

    async def fetch_store_display(self):
        try:
            print(f"\nStarting data fetch at {datetime.now()}")
            raw_data = await fetch_nse_option_chain()
            
            if not raw_data:
                print("Failed to fetch data from NSE")
                return
                
            print("Raw data structure:", raw_data.keys() if raw_data else "None")
            rows = extract_option_chain_data(raw_data, EXPIRY_DATE)
            
            if not rows:
                print("No data extracted from NSE response")
                return
                
            # Store in main table
            insert_data_to_db(rows)
            print(f"Stored {len(rows)} rows in database at {datetime.now()}")
            
            # Store in signal comparison table
            for row in rows:
                signal_data = (
                    row[0],  # date_time
                    row[1],  # strike_price
                    row[2],  # option_type
                    row[8],  # ltp
                    row[4],  # oi
                    row[6],  # volume
                    0,  # ma_5min (will be calculated)
                    0,  # ma_15min (will be calculated)
                    0,  # ma_30min (will be calculated)
                    0,  # vol_ma_5min (will be calculated)
                    0,  # vol_ma_15min (will be calculated)
                    'No Signal',  # signal_type
                    0,  # signal_strength
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # created_at
                )
                insert_signal_comparison_data(signal_data)
            
            # Always fetch and display latest data
            df = fetch_sql_results()
            if not df.empty:
                self.root.after_idle(lambda: self.display_table(self.frames[0], df))
                print(f"Displayed {len(df)} rows in grid at {datetime.now()}")
            else:
                print("No data available for display")
                
        except Exception as e:
            print(f"Error in fetch_store_display: {e}")
            # If there's an error, try to display existing data
            try:
                df = fetch_sql_results()
                if not df.empty:
                    self.root.after_idle(lambda: self.display_table(self.frames[0], df))
                    print(f"Displayed existing {len(df)} rows after error")
            except Exception as display_error:
                print(f"Error displaying existing data: {display_error}")

# --- Main ---
if __name__ == "__main__":
    create_signal_comparison_table()
    root = tk.Tk()
    app = NiftyApp(root)
    root.mainloop()

