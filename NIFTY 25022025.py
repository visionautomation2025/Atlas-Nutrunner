import tkinter as tk
from tkinter import ttk
import ttkbootstrap as ttk
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import time
import threading
import aiohttp
import json
import asyncio
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter.messagebox as messagebox

class OptionMonitor:
    def __init__(self, root):
        self.root = root
        self.root.title("Option Price Monitor")
        self.root.geometry("1950x1600")  # Set to your specified size
        
        # NSE API URLs and headers
        self.url_oc = "https://www.nseindia.com/option-chain"
        self.url_nf = 'https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY'
        self.headers = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, '
                         'like Gecko) Chrome/80.0.3987.149 Safari/537.36',
            'accept-language': 'en,gu;q=0.9,hi;q=0.8',
            'accept-encoding': 'gzip, deflate, br'
        }
        self.cookies = {}
        self.session = None
        
        # Setup database
        self.setup_database()
        
        # Initialize strike prices as None
        self.strike_price_ce = None
        self.strike_price_pe = None
        self.strike_price_ce21 = None
        self.strike_price_pe21 = None
        
        # Create main container
        self.container = ttk.Frame(root, padding="10")
        self.container.pack(fill=tk.BOTH, expand=True)
        
        # Create header
        self.create_header()
        
        # Create cards for each strike price
        self.create_strike_cards()
        
        # Add event loop initialization
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        # Start monitoring thread
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self.monitor_prices)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()

        # Add market hours label
        self.market_hours_label = ttk.Label(
            self.container,
            text="Market Hours: 9:15 AM - 3:40 PM",
            font=("Helvetica", 10, "italic"),
            foreground="yellow"
        )
        self.market_hours_label.pack(pady=2)

    def setup_database(self):
        """Setup the database and create necessary tables"""
        with sqlite3.connect('E:/nifty_data.db') as conn:
            cursor = conn.cursor()
            
            # Create nifty option chain data table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS nifty_option_chain_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            
            # Create LTP coefficient table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ltp_coefficient (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date_time TEXT,
                    ce_coefficient REAL,
                    pe_coefficient REAL,
                    ce_strike REAL,
                    pe_strike REAL
                )
            ''')
            conn.commit()

    async def initialize_session(self):
        """Initialize the aiohttp session and get cookies"""
        self.session = aiohttp.ClientSession()
        try:
            async with self.session.get(self.url_oc, headers=self.headers, timeout=5) as response:
                if response.status == 200:
                    self.cookies = {k: v.value for k, v in response.cookies.items()}
        except Exception as e:
            print(f"Error initializing session: {e}")
            await self.session.close()
            self.session = None
            raise

    async def get_option_chain_data(self):
        """Fetch option chain data from NSE"""
        if not self.session:
            await self.initialize_session()

        try:
            async with self.session.get(self.url_nf, headers=self.headers, 
                                      cookies=self.cookies, timeout=30) as response:  # Increased timeout
                if response.status == 401:
                    await self.initialize_session()
                    async with self.session.get(self.url_nf, headers=self.headers, 
                                              cookies=self.cookies, timeout=30) as response:
                        return await response.json()
                elif response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"Unexpected status code: {response.status}")
        except Exception as e:
            print(f"Error fetching option chain data: {e}")
            # Re-initialize session on error
            await self.initialize_session()
            raise

    def get_db_connection(self):
        """Create a new database connection for the current thread"""
        return sqlite3.connect('E:/nifty_data.db')

    def store_option_data(self, data):
        """Store option chain data with IV handling"""
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # Print received data for debugging
                print(f"Received data at {current_time}")
                print(f"Records count: {len(data['records']['data'])}")
                
                underlying_value = data["records"]["underlyingValue"]
                current_expiry = data["records"]["expiryDates"][0]
                
                # Update spot price and ATM strike in GUI
                self.spot_price_label.config(text=f"Nifty: {underlying_value:.2f}")
                atm_strike = self.calculate_atm_strike(underlying_value)
                self.atm_label.config(text=f"ATM Strike: {atm_strike}")
                
                # Get previous IV values
                prev_iv_query = """
                SELECT strike_price, option_type, iv
                FROM nifty_option_chain_data
                WHERE date_time = (
                    SELECT MAX(date_time) FROM nifty_option_chain_data
                    WHERE date_time < ?
                )
                """
                prev_iv_data = pd.read_sql_query(prev_iv_query, conn, params=(current_time,))
                
                # Counter for inserted records
                records_inserted = 0
                
                for item in data["records"]["data"]:
                    try:
                        # Only store data for current expiry
                        if item.get("expiryDate") != current_expiry:
                            continue
                        
                        # Store CE data
                        if "CE" in item:
                            ce_data = item["CE"]
                            # Handle IV value
                            iv_value = ce_data["impliedVolatility"]
                            if iv_value == 0:
                                prev_iv = prev_iv_data[
                                    (prev_iv_data['strike_price'] == ce_data["strikePrice"]) & 
                                    (prev_iv_data['option_type'] == 'CE')
                                ]['iv'].iloc[0] if not prev_iv_data.empty else 0
                                iv_value = prev_iv
                            
                            cursor.execute('''
                                INSERT INTO nifty_option_chain_data (
                                    date_time, strike_price, option_type, expiry_date,
                                    open_interest, changein_oi, volume, iv, ltp, net_change,
                                    total_buy_quantity, total_sell_quantity,
                                    bid_qty, bid_price, ask_qty, ask_price, underlying_value
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ''', (
                                current_time, ce_data["strikePrice"], "CE", current_expiry,
                                ce_data["openInterest"], ce_data["changeinOpenInterest"],
                                ce_data["totalTradedVolume"], iv_value,
                                ce_data["lastPrice"], ce_data["change"],
                                ce_data["totalBuyQuantity"], ce_data["totalSellQuantity"],
                                ce_data["bidQty"], ce_data["bidprice"],
                                ce_data["askQty"], ce_data["askPrice"],
                                underlying_value
                            ))
                            records_inserted += 1
                        
                        # Store PE data
                        if "PE" in item:
                            pe_data = item["PE"]
                            # Handle IV value
                            iv_value = pe_data["impliedVolatility"]
                            if iv_value == 0:
                                prev_iv = prev_iv_data[
                                    (prev_iv_data['strike_price'] == pe_data["strikePrice"]) & 
                                    (prev_iv_data['option_type'] == 'PE')
                                ]['iv'].iloc[0] if not prev_iv_data.empty else 0
                                iv_value = prev_iv
                            
                            cursor.execute('''
                                INSERT INTO nifty_option_chain_data (
                                    date_time, strike_price, option_type, expiry_date,
                                    open_interest, changein_oi, volume, iv, ltp, net_change,
                                    total_buy_quantity, total_sell_quantity,
                                    bid_qty, bid_price, ask_qty, ask_price, underlying_value
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ''', (
                                current_time, pe_data["strikePrice"], "PE", current_expiry,
                                pe_data["openInterest"], pe_data["changeinOpenInterest"],
                                pe_data["totalTradedVolume"], iv_value,
                                pe_data["lastPrice"], pe_data["change"],
                                pe_data["totalBuyQuantity"], pe_data["totalSellQuantity"],
                                pe_data["bidQty"], pe_data["bidprice"],
                                pe_data["askQty"], pe_data["askPrice"],
                                underlying_value
                            ))
                            records_inserted += 1
                            
                    except Exception as e:
                        print(f"Error inserting record: {e}")
                        continue
                
                # Commit the transaction
                conn.commit()
                
                # Verify data was stored
                verify_query = """
                SELECT COUNT(*) FROM nifty_option_chain_data 
                WHERE date_time = ?
                """
                cursor.execute(verify_query, (current_time,))
                stored_count = cursor.fetchone()[0]
                
                if stored_count > 0:
                    print(f"Successfully stored {stored_count} records")
                    self.status_label.config(
                        text=f"Database Updated Successfully at {current_time} ({stored_count} records)",
                        foreground="green"
                    )
                else:
                    print("No records were stored")
                    self.status_label.config(
                        text="Database Update Failed - No records stored",
                        foreground="red"
                    )
                
        except Exception as e:
            print(f"Error in store_option_data: {str(e)}")
            self.status_label.config(
                text=f"Database Error: {str(e)}",
                foreground="red"
            )

    async def fetch_and_store_data(self):
        """Fetch and store option chain data"""
        try:
            data = await self.get_option_chain_data()
            self.store_option_data(data)
            print(f"Data stored successfully at {datetime.now()}")
        except Exception as e:
            print(f"Error in fetch_and_store_data: {e}")

    def create_header(self):
        """Create the header section with three analysis frames"""
        header = ttk.Frame(self.container)
        header.pack(fill=tk.X, pady=(0, 10))
        
        # Create title and status labels
        title_label = ttk.Label(
            header,
            text="NSE Option Chain Monitor",
            font=("Helvetica", 20, "bold")
        )
        title_label.pack(pady=5)
        
        self.status_label = ttk.Label(
            header,
            text="Initializing...",
            font=("Helvetica", 10)
        )
        self.status_label.pack(pady=2)
        
        # Create main info container
        info_container = ttk.Frame(header)
        info_container.pack(fill=tk.X, pady=5)
        
        # Left side metrics frame
        metrics_frame = ttk.LabelFrame(info_container, text="Market Metrics", padding="5")
        metrics_frame.pack(side=tk.LEFT, padx=10, fill=tk.Y)
        metrics_frame.configure(height=80)  # Further reduced height
        
        # Basic metrics
        self.spot_price_label = ttk.Label(metrics_frame, text="Nifty: --", font=("Helvetica", 14, "bold"))
        self.atm_label = ttk.Label(metrics_frame, text="ATM Strike: --", font=("Helvetica", 14, "bold"))
        
        self.spot_price_label.pack(pady=2)
        self.atm_label.pack(pady=2)
        
        # Right side analysis frames container
        analysis_container = ttk.Frame(info_container)
        analysis_container.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10)
        
        # Configure grid for analysis frames
        analysis_container.grid_columnconfigure(0, weight=1)
        analysis_container.grid_columnconfigure(1, weight=1)
        analysis_container.grid_columnconfigure(2, weight=1)
        
        # 1. PCR Analysis Frame
        pcr_frame = ttk.LabelFrame(analysis_container, text="PCR Analysis", padding="5")
        pcr_frame.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        
        self.total_ce_oi_label = ttk.Label(pcr_frame, text="Total CE OI: --", font=("Helvetica", 11))
        self.total_pe_oi_label = ttk.Label(pcr_frame, text="Total PE OI: --", font=("Helvetica", 11))
        self.pcr_label = ttk.Label(pcr_frame, text="PCR: --", font=("Helvetica", 12, "bold"))
        self.pcr_prediction = ttk.Label(pcr_frame, text="PCR Prediction: --", font=("Helvetica", 11))
        
        self.total_ce_oi_label.pack(pady=2)
        self.total_pe_oi_label.pack(pady=2)
        self.pcr_label.pack(pady=2)
        self.pcr_prediction.pack(pady=2)
        
        # 2. IV-LTP Correlation Frame
        correlation_frame = ttk.LabelFrame(analysis_container, text="IV-LTP Correlation", padding="5")
        correlation_frame.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")
        
        self.ce_correlation_label = ttk.Label(correlation_frame, text="CE Correlation: --", font=("Helvetica", 11))
        self.pe_correlation_label = ttk.Label(correlation_frame, text="PE Correlation: --", font=("Helvetica", 11))
        self.correlation_prediction = ttk.Label(correlation_frame, text="Correlation Analysis: --", font=("Helvetica", 11))
        
        self.ce_correlation_label.pack(pady=2)
        self.pe_correlation_label.pack(pady=2)
        self.correlation_prediction.pack(pady=2)
        
        # 3. Strike Pressure Frame
        pressure_frame = ttk.LabelFrame(analysis_container, text="Strike Pressure Analysis", padding="5")
        pressure_frame.grid(row=0, column=2, padx=5, pady=5, sticky="nsew")
        
        self.pressure_text = tk.Text(
            pressure_frame,
            height=6,
            wrap=tk.WORD,
            font=("Helvetica", 11)
        )
        self.pressure_text.pack(fill=tk.BOTH, expand=True, pady=2)
        
        # Create a single button frame for both buttons
        button_frame = ttk.Frame(analysis_container)
        button_frame.grid(row=1, column=0, columnspan=3, pady=5)
        
        # Add IV Skewness button
        self.skew_button = ttk.Button(
            button_frame,
            text="Analyze IV Skewness",
            command=self.show_skewness_analysis,
            style="Accent.TButton"
        )
        self.skew_button.pack(side=tk.LEFT, padx=5)
        
        # Add Graph Data button
        self.graph_button = ttk.Button(
            button_frame,
            text="Strike Analysis Graphs",
            command=self.show_graph_analysis,
            style="Accent.TButton"
        )
        self.graph_button.pack(side=tk.LEFT, padx=5)

        # Add LTP Graph button next to other buttons
        self.ltp_button = ttk.Button(
            button_frame,
            text="LTP Analysis",
            command=self.show_ltp_analysis,
            style="Accent.TButton"
        )
        self.ltp_button.pack(side=tk.LEFT, padx=5)

        # Add Option Greeks button next to other buttons
        self.greeks_button = ttk.Button(
            button_frame,
            text="Option Greeks",
            command=self.show_greeks_analysis,
            style="Accent.TButton"
        )
        self.greeks_button.pack(side=tk.LEFT, padx=5)

        # Move summary report to right side with reduced width
        summary_frame = ttk.LabelFrame(info_container, text="Market Summary Report", padding="5")
        summary_frame.pack(side=tk.RIGHT, padx=5, pady=5, fill=tk.Y)
        
        # Configure summary text with reduced width
        self.summary_text = tk.Text(
            summary_frame,
            height=12,
            width=45,  # Reduced width
            wrap=tk.WORD,
            font=("Helvetica", 10),  # Slightly smaller font
            background="#1a1a2e",
            foreground="#00ff00"
        )
        scrollbar = ttk.Scrollbar(summary_frame, orient="vertical", command=self.summary_text.yview)
        self.summary_text.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.summary_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def calculate_atm_strike(self, spot_price):
        """Calculate ATM strike price"""
        return round(spot_price / 50) * 50

    def create_strike_cards(self):
        """Create compact strike cards aligned to the left"""
        # Create a container frame for cards with fixed width
        self.cards_frame = ttk.Frame(self.container, width=800)  # Fixed width container
        self.cards_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=5)
        self.cards_frame.pack_propagate(False)  # Prevent frame from expanding
        
        # Create grid layout for cards
        for i in range(2):
            self.cards_frame.grid_columnconfigure(i, weight=1, minsize=380)  # Each card width 380px
            self.cards_frame.grid_rowconfigure(i, weight=1, minsize=200)  # Each card height 200px
        
        # Create cards with smaller padding
        self.ce_card1 = self.create_card(self.cards_frame, "CE Strike 1", 0, 0)
        self.pe_card1 = self.create_card(self.cards_frame, "PE Strike 1", 0, 1)
        self.ce_card2 = self.create_card(self.cards_frame, "CE Strike 2", 1, 0)
        self.pe_card2 = self.create_card(self.cards_frame, "PE Strike 2", 1, 1)

    def create_card(self, parent, title, row, col):
        """Create a compact monitoring card"""
        card = ttk.LabelFrame(parent, text=title, padding="3")  # Reduced padding
        card.grid(row=row, column=col, padx=2, pady=2, sticky="nsew")
        
        # Configure background color
        style = ttk.Style()
        style.configure("Card.TLabelframe", background="#1a1a2e")
        style.configure("Card.TLabel", 
                       background="#1a1a2e",
                       foreground="#00ff00",
                       font=("Helvetica", 9))  # Smaller font size
        card.configure(style="Card.TLabelframe")
        
        metrics = {
            'Strike Price': ttk.Label(card, text="Strike Price: --", style="Card.TLabel"),
            'OI': ttk.Label(card, text="OI: --", style="Card.TLabel"),
            'OI Trend': ttk.Label(card, text="OI Trend: --", style="Card.TLabel"),
            'Change in OI': ttk.Label(card, text="Change in OI: --", style="Card.TLabel"),
            'Change in OI Trend': ttk.Label(card, text="Change in OI Trend: --", style="Card.TLabel"),
            'IV': ttk.Label(card, text="IV: --", style="Card.TLabel"),
            'IV Trend': ttk.Label(card, text="IV Trend: --", style="Card.TLabel"),
            'LTP': ttk.Label(card, text="LTP: --", style="Card.TLabel"),
            'LTP Trend': ttk.Label(card, text="LTP Trend: --", style="Card.TLabel")
        }
        
        # Position labels with minimal spacing
        for i, (key, label) in enumerate(metrics.items()):
            label.grid(row=i, column=0, sticky="w", pady=0, padx=2)
        
        return metrics

    def get_latest_data(self, strike_price, option_type):
        current_date = datetime.today().strftime('%Y-%m-%d')
        table = f"option_{option_type.lower()}_data"
        
        query = f"""
        SELECT date_time, oi, changein_oi, iv, ltp
        FROM {table}
        WHERE strike_price = {strike_price} 
        AND date_time BETWEEN '{current_date} 09:00:00' AND '{current_date} 15:30:00'
        ORDER BY date_time DESC
        LIMIT 2
        """
        
        with sqlite3.connect('E:/nifty_data.db') as conn:
            df = pd.read_sql_query(query, conn)
        
        return df if not df.empty else None

    def determine_trend(self, current, previous):
        """Determine trend direction with arrow indicators"""
        if current > previous:
            return "↑ Increasing"
        elif current < previous:
            return "↓ Decreasing"
        return "→ Stable"

    def update_card(self, card_metrics, strike_price, option_type):
        data = self.get_latest_data(strike_price, option_type)
        
        if data is not None and len(data) >= 2:
            current = data.iloc[0]
            previous = data.iloc[1]
            
            card_metrics['Strike Price'].config(text=f"Strike Price: {strike_price}")
            card_metrics['OI'].config(text=f"OI: {current['oi']:.2f}")
            card_metrics['OI Trend'].config(text=f"OI Trend: {self.determine_trend(current['oi'], previous['oi'])}")
            card_metrics['Change in OI'].config(text=f"Change in OI: {current['changein_oi']:.2f}")
            card_metrics['Change in OI Trend'].config(
                text=f"Change in OI Trend: {self.determine_trend(current['changein_oi'], previous['changein_oi'])}")
            card_metrics['IV'].config(text=f"IV: {current['iv']:.2f}")
            card_metrics['IV Trend'].config(text=f"IV Trend: {self.determine_trend(current['iv'], previous['iv'])}")
            card_metrics['LTP'].config(text=f"LTP: {current['ltp']:.2f}")
            card_metrics['LTP Trend'].config(text=f"LTP Trend: {self.determine_trend(current['ltp'], previous['ltp'])}")

    def get_high_volume_strikes(self):
        """Get top 2 high volume strike prices for CE and PE from current expiry"""
        try:
            with self.get_db_connection() as conn:
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # Query for CE strikes
                ce_query = """
                SELECT strike_price, volume 
                FROM nifty_option_chain_data 
                WHERE option_type = 'CE'
                AND date_time = (
                    SELECT MAX(date_time) FROM nifty_option_chain_data
                )
                ORDER BY volume DESC
                LIMIT 2
                """
                
                # Query for PE strikes
                pe_query = """
                SELECT strike_price, volume 
                FROM nifty_option_chain_data 
                WHERE option_type = 'PE'
                AND date_time = (
                    SELECT MAX(date_time) FROM nifty_option_chain_data
                )
                ORDER BY volume DESC
                LIMIT 2
                """
                
                ce_strikes = pd.read_sql_query(ce_query, conn)
                pe_strikes = pd.read_sql_query(pe_query, conn)
                
                if not ce_strikes.empty and not pe_strikes.empty:
                    ce_prices = ce_strikes['strike_price'].tolist()
                    pe_prices = pe_strikes['strike_price'].tolist()
                    
                    # Update strike prices
                    self.strike_price_ce = ce_prices[0]
                    self.strike_price_ce21 = ce_prices[1]
                    self.strike_price_pe = pe_prices[0]
                    self.strike_price_pe21 = pe_prices[1]
                    
                    print(f"Updated strike prices - CE: {ce_prices}, PE: {pe_prices}")
                    
        except Exception as e:
            print(f"Error getting high volume strikes: {e}")

    def monitor_prices(self):
        """Monitor prices with verification"""
        while self.monitoring:
            try:
                current_time = datetime.now()
                
                # Check if it's after market hours (3:40 PM)
                if current_time.hour > 15 or (current_time.hour == 15 and current_time.minute >= 40):
                    if not hasattr(self, 'market_closed_shown'):
                        messagebox.showinfo("Market Status", "Market Closed for Today!")
                        self.status_label.config(
                            text="Market Closed - Data collection stopped",
                            foreground="orange"
                        )
                        self.market_closed_shown = True
                    time.sleep(60)  # Check every minute
                    continue
                    
                # Reset the flag at the start of each day
                if current_time.hour < 9:
                    if hasattr(self, 'market_closed_shown'):
                        delattr(self, 'market_closed_shown')
                
                # Run fetch and store in the event loop
                self.loop.run_until_complete(self.fetch_and_store_data())
                
                # Generate and update market summary
                self.generate_market_summary()
                
                # Get high volume strike prices
                self.get_high_volume_strikes()
                
                # Update the display
                self.update_display()
                
                # Wait for 5 minutes
                time.sleep(300)
                
            except Exception as e:
                print(f"Error in monitoring: {e}")
                self.status_label.config(
                    text=f"Error: {str(e)}",
                    foreground="red"
                )
                self.loop.run_until_complete(self.initialize_session())
                time.sleep(5)

    def stop_monitoring(self):
        """Stop the monitoring thread and cleanup resources"""
        self.monitoring = False
        
        # Cleanup async resources
        if hasattr(self, 'loop'):
            self.loop.run_until_complete(self.cleanup())
            self.loop.close()

    def set_strike_prices(self, ce1, pe1, ce2, pe2):
        self.strike_price_ce = ce1
        self.strike_price_pe = pe1
        self.strike_price_ce21 = ce2
        self.strike_price_pe21 = pe2

    def update_display(self):
        """Update the display with latest data"""
        try:
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Get latest data from database using a new connection
            with self.get_db_connection() as conn:
                # Add logging
                print(f"Attempting to fetch data at {current_time}")
                
                query = """
                SELECT * FROM nifty_option_chain_data 
                WHERE date_time = (
                    SELECT MAX(date_time) FROM nifty_option_chain_data
                )
                """
                
                df = pd.read_sql_query(query, conn)
                
                # Add data validation
                if df.empty:
                    self.status_label.config(
                        text=f"No data available at {current_time}",
                        foreground="orange"
                    )
                    return
                
                print(f"Data fetched successfully. Rows: {len(df)}")
                
                # Update status
                self.status_label.config(text=f"Last Update: {current_time}")
                
                # Update each card
                for option_type, strike_price, card in [
                    ("CE", self.strike_price_ce, self.ce_card1),
                    ("PE", self.strike_price_pe, self.pe_card1),
                    ("CE", self.strike_price_ce21, self.ce_card2),
                    ("PE", self.strike_price_pe21, self.pe_card2)
                ]:
                    data = df[(df['option_type'] == option_type) & 
                             (df['strike_price'] == strike_price)]
                    
                    if not data.empty:
                        row = data.iloc[0]
                        card['Strike Price'].config(text=f"Strike Price: {strike_price}")
                        card['OI'].config(text=f"OI: {row['open_interest']:,.0f}")
                        card['Change in OI'].config(text=f"Change in OI: {row['changein_oi']:.2f}")
                        card['IV'].config(text=f"IV: {row['iv']:.2f}%")
                        card['LTP'].config(text=f"LTP: {row['ltp']:.2f}")
                        
                        # Get previous data for trends
                        prev_query = f"""
                        SELECT * FROM nifty_option_chain_data 
                        WHERE option_type = '{option_type}'
                        AND strike_price = {strike_price}
                        AND date_time < '{current_time}'
                        ORDER BY date_time DESC
                        LIMIT 1
                        """
                        prev_data = pd.read_sql_query(prev_query, conn)
                        
                        if not prev_data.empty:
                            prev_row = prev_data.iloc[0]
                            card['OI Trend'].config(text=f"OI Trend: {self.determine_trend(row['open_interest'], prev_row['open_interest'])}")
                            card['Change in OI Trend'].config(text=f"Change in OI Trend: {self.determine_trend(row['changein_oi'], prev_row['changein_oi'])}")
                            card['IV Trend'].config(text=f"IV Trend: {self.determine_trend(row['iv'], prev_row['iv'])}")
                            card['LTP Trend'].config(text=f"LTP Trend: {self.determine_trend(row['ltp'], prev_row['ltp'])}")
        
            # Calculate and update PCR and correlations
            self.calculate_pcr_and_correlations()
            
            # Update pressure analysis
            pressure_analysis = self.analyze_strike_pressure()
            self.pressure_text.delete(1.0, tk.END)
            self.pressure_text.insert(tk.END, pressure_analysis)
            
        except Exception as e:
            print(f"Detailed error in update_display: {type(e).__name__}: {str(e)}")
            self.status_label.config(
                text=f"Update error: {type(e).__name__}",
                foreground="red"
            )

    async def cleanup(self):
        """Cleanup resources"""
        if self.session:
            await self.session.close()
            self.session = None

    def calculate_correlation(self, conn, option_type):
        """Calculate correlation between IV and LTP for highest volume strike price"""
        # First get the strike price with highest volume
        volume_query = f"""
        SELECT strike_price, SUM(volume) as total_volume
        FROM nifty_option_chain_data
        WHERE option_type = '{option_type}'
        AND date_time = (
            SELECT MAX(date_time) FROM nifty_option_chain_data
        )
        GROUP BY strike_price
        ORDER BY total_volume DESC
        LIMIT 1
        """
        
        df_volume = pd.read_sql_query(volume_query, conn)
        if df_volume.empty:
            return 0
        
        high_volume_strike = df_volume['strike_price'].iloc[0]
        
        # Then get IV and LTP data for this strike price
        corr_query = f"""
        SELECT iv, ltp, date_time
        FROM nifty_option_chain_data
        WHERE strike_price = {high_volume_strike}
        AND option_type = '{option_type}'
        ORDER BY date_time DESC
        LIMIT 10
        """
        
        df = pd.read_sql_query(corr_query, conn)
        
        if len(df) > 1:
            correlation = df['iv'].corr(df['ltp'])
            print(f"{option_type} Correlation for Strike {high_volume_strike}:")
            print(f"IV values: {df['iv'].tolist()}")
            print(f"LTP values: {df['ltp'].tolist()}")
            print(f"Correlation: {correlation}")
            return correlation, high_volume_strike
        return 0, high_volume_strike

    def calculate_pcr_and_correlations(self):
        """Calculate PCR and IV-LTP correlations"""
        try:
            with self.get_db_connection() as conn:
                # Get latest data
                latest_data_query = """
                SELECT option_type, SUM(open_interest) as total_oi
                FROM nifty_option_chain_data
                WHERE date_time = (SELECT MAX(date_time) FROM nifty_option_chain_data)
                GROUP BY option_type
                """
                df = pd.read_sql_query(latest_data_query, conn)
                
                # Calculate PCR
                ce_oi = df[df['option_type'] == 'CE']['total_oi'].iloc[0]
                pe_oi = df[df['option_type'] == 'PE']['total_oi'].iloc[0]
                pcr = pe_oi / ce_oi if ce_oi > 0 else 0
                
                # Update OI and PCR labels
                self.total_ce_oi_label.config(text=f"Total CE OI: {ce_oi:,.0f}")
                self.total_pe_oi_label.config(text=f"Total PE OI: {pe_oi:,.0f}")
                self.pcr_label.config(text=f"PCR: {pcr:.2f}")
                
                # Generate and update PCR prediction
                pcr_prediction = self.generate_pcr_prediction(pcr)
                self.pcr_prediction.config(text=pcr_prediction)
                
                # Calculate correlations for highest volume strikes
                ce_corr, ce_strike = self.calculate_correlation(conn, 'CE')
                pe_corr, pe_strike = self.calculate_correlation(conn, 'PE')
                
                # Store coefficients in database
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO ltp_coefficient (
                        date_time, ce_coefficient, pe_coefficient, ce_strike, pe_strike
                    ) VALUES (?, ?, ?, ?, ?)
                ''', (current_time, ce_corr, pe_corr, ce_strike, pe_strike))
                conn.commit()
                
                # Update GUI labels
                self.ce_correlation_label.config(
                    text=f"CE {ce_strike} IV-LTP Correlation: {ce_corr:.2f}"
                )
                self.pe_correlation_label.config(
                    text=f"PE {pe_strike} IV-LTP Correlation: {pe_corr:.2f}"
                )
                
                # Generate prediction
                prediction = self.generate_market_prediction(pcr, ce_corr, pe_corr)
                self.correlation_prediction.config(text=f"Correlation Analysis: {prediction}")
                
        except Exception as e:
            print(f"Error calculating metrics: {e}")

    def generate_pcr_prediction(self, pcr):
        """Generate PCR-based prediction"""
        if pcr > 1.5:
            return (
                "Strong Bullish Signal\n"
                "High Put Writing\n"
                "Expect Upward Movement"
            )
        elif pcr > 1.2:
            return (
                "Moderately Bullish\n"
                "Put Writing Dominates\n"
                "Watch for Breakout"
            )
        elif pcr < 0.5:
            return (
                "Strong Bearish Signal\n"
                "High Call Writing\n"
                "Expect Downward Movement"
            )
        elif pcr < 0.8:
            return (
                "Moderately Bearish\n"
                "Call Writing Dominates\n"
                "Watch for Breakdown"
            )
        else:
            return (
                "Market in Consolidation\n"
                "Balanced Put-Call Activity\n"
                "Range-bound Movement Likely"
            )

    def generate_market_prediction(self, pcr, ce_corr, pe_corr):
        """Generate detailed market prediction based on PCR and correlations"""
        # PCR based prediction
        if pcr > 1.5:
            base_prediction = "Bullish"
            pcr_message = (
                "Strong Bullish Signal\n"
                "• High Put Writing indicates strong support\n"
                "• Traders expecting upward movement\n"
                "• Consider Buy on Dips strategy"
            )
        elif pcr > 1.2:
            base_prediction = "Moderately Bullish"
            pcr_message = (
                "Moderately Bullish Signal\n"
                "• Put Writing dominates\n"
                "• Upward bias in market\n"
                "• Watch for breakout above resistance"
            )
        elif pcr < 0.5:
            base_prediction = "Bearish"
            pcr_message = (
                "Strong Bearish Signal\n"
                "• High Call Writing indicates strong resistance\n"
                "• Traders expecting downward movement\n"
                "• Consider Sell on Rise strategy"
            )
        elif pcr < 0.8:
            base_prediction = "Moderately Bearish"
            pcr_message = (
                "Moderately Bearish Signal\n"
                "• Call Writing dominates\n"
                "• Downward bias in market\n"
                "• Watch for breakdown below support"
            )
        else:
            base_prediction = "Consolidation"
            pcr_message = (
                "Range-bound Movement\n"
                "• Balance between Put and Call writing\n"
                "• No clear directional bias\n"
                "• Consider Range-bound strategies"
            )

        # Correlation based additional insights
        if abs(ce_corr) > 0.7 or abs(pe_corr) > 0.7:
            if ce_corr > 0.7 and pe_corr < -0.7:
                trading_advice = (
                    "\nTrading Advice:\n"
                    "• Premium erosion likely\n"
                    "• Avoid buying OTM options\n"
                    "• Consider writing strategies"
                )
            elif ce_corr < -0.7 and pe_corr > 0.7:
                trading_advice = (
                    "\nTrading Advice:\n"
                    "• Wait for breakout confirmation\n"
                    "• High volatility expected\n"
                    "• Keep strict stop losses"
                )
            else:
                trading_advice = (
                    "\nTrading Advice:\n"
                    "• Monitor option chain for clear signals\n"
                    "• Keep position size moderate\n"
                    "• Use hedging strategies"
                )
        else:
            trading_advice = (
                "\nTrading Advice:\n"
                "• Normal market conditions\n"
                "• Follow your regular trading plan\n"
                "• Keep standard position sizing"
            )

        return f"{base_prediction}\n{pcr_message}{trading_advice}"

    def create_skewness_window(self):
        """Create IV Skewness analysis window"""
        skew_window = tk.Toplevel(self.root)
        skew_window.title("IV Skewness Analysis")
        skew_window.geometry("1200x800")
        
        # Left frame for graph
        left_frame = ttk.Frame(skew_window)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create matplotlib figure
        fig = plt.Figure(figsize=(6, 4))
        ax = fig.add_subplot(111)
        canvas = FigureCanvasTkAgg(fig, left_frame)
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Right frame for analysis
        right_frame = ttk.Frame(skew_window)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Skewness value frame
        skew_value_frame = ttk.LabelFrame(right_frame, text="IV Skewness", padding=10)
        skew_value_frame.pack(fill=tk.X, pady=5)
        
        self.skew_value_label = ttk.Label(
            skew_value_frame, 
            text="--", 
            font=("Helvetica", 14, "bold")
        )
        self.skew_value_label.pack()
        
        # Support/Resistance frame
        levels_frame = ttk.LabelFrame(right_frame, text="Support & Resistance", padding=10)
        levels_frame.pack(fill=tk.X, pady=5)
        
        # Resistance levels
        ttk.Label(levels_frame, text="Resistance Levels", font=("Helvetica", 12, "bold")).pack()
        self.resistance_labels = []
        for i in range(3):
            label = ttk.Label(levels_frame, text="--", font=("Helvetica", 11))
            label.pack()
            self.resistance_labels.append(label)
        
        # Support levels
        ttk.Label(levels_frame, text="Support Levels", font=("Helvetica", 12, "bold")).pack()
        self.support_labels = []
        for i in range(3):
            label = ttk.Label(levels_frame, text="--", font=("Helvetica", 11))
            label.pack()
            self.support_labels.append(label)
        
        # Strategy frame
        strategy_frame = ttk.LabelFrame(right_frame, text="Trading Strategy", padding=10)
        strategy_frame.pack(fill=tk.X, pady=5)
        
        self.strategy_text = tk.Text(
            strategy_frame, 
            height=10, 
            wrap=tk.WORD, 
            font=("Helvetica", 11)
        )
        self.strategy_text.pack(fill=tk.BOTH, expand=True)
        
        return skew_window, ax, canvas

    def calculate_iv_skewness(self):
        """Calculate IV Skewness and support/resistance levels"""
        with self.get_db_connection() as conn:
            query = """
            SELECT strike_price, iv, open_interest, option_type
            FROM nifty_option_chain_data
            WHERE date_time = (SELECT MAX(date_time) FROM nifty_option_chain_data)
            ORDER BY strike_price
            """
            df = pd.read_sql_query(query, conn)
            
            # Calculate IV Skewness
            ce_data = df[df['option_type'] == 'CE']
            skewness = ce_data['iv'].skew()
            
            # Find resistance levels (highest OI in CE)
            resistance_levels = ce_data.nlargest(3, 'open_interest')[['strike_price', 'open_interest']]
            
            # Find support levels (highest OI in PE)
            pe_data = df[df['option_type'] == 'PE']
            support_levels = pe_data.nlargest(3, 'open_interest')[['strike_price', 'open_interest']]
            
            return skewness, ce_data, resistance_levels, support_levels

    def generate_skewness_strategy(self, skewness):
        """Generate trading strategy based on IV Skewness"""
        if skewness > 0.5:
            return (
                "Positive Skew Strategy:\n\n"
                "• Market expecting upward movement\n"
                "• Higher premiums for OTM calls\n"
                "• Consider Bull Call Spread\n"
                "• Buy ATM/Slightly OTM Calls\n"
                "• Sell Far OTM Calls\n\n"
                "Risk Management:\n"
                "• Keep position size small\n"
                "• Use strict stop losses\n"
                "• Monitor IV for mean reversion"
            )
        elif skewness < -0.5:
            return (
                "Negative Skew Strategy:\n\n"
                "• Market expecting downward movement\n"
                "• Higher premiums for OTM puts\n"
                "• Consider Bear Put Spread\n"
                "• Buy ATM/Slightly OTM Puts\n"
                "• Sell Far OTM Puts\n\n"
                "Risk Management:\n"
                "• Keep position size small\n"
                "• Use strict stop losses\n"
                "• Monitor IV for mean reversion"
            )
        else:
            return (
                "Neutral Skew Strategy:\n\n"
                "• Market in equilibrium\n"
                "• Consider Iron Condor\n"
                "• Or Calendar Spreads\n"
                "• Focus on premium decay\n\n"
                "Risk Management:\n"
                "• Use wider spreads\n"
                "• Keep balanced positions\n"
                "• Monitor for skew changes"
            )

    def show_skewness_analysis(self):
        """Show IV Skewness analysis window and update data"""
        skew_window, ax, canvas = self.create_skewness_window()
        
        try:
            # Calculate skewness and levels
            skewness, ce_data, resistance_levels, support_levels = self.calculate_iv_skewness()
            
            # Update skewness value
            self.skew_value_label.config(text=f"Current IV Skewness: {skewness:.3f}")
            
            # Plot IV Curve
            ax.clear()
            ax.plot(ce_data['strike_price'], ce_data['iv'], 'g-', label='IV Curve')
            ax.set_title('IV Skewness Analysis')
            ax.set_xlabel('Strike Price')
            ax.set_ylabel('Implied Volatility')
            ax.grid(True)
            canvas.draw()
            
            # Update resistance levels
            for i, (_, row) in enumerate(resistance_levels.iterrows()):
                self.resistance_labels[i].config(
                    text=f"Strike: {row['strike_price']}, OI: {row['open_interest']:,.0f}"
                )
            
            # Update support levels
            for i, (_, row) in enumerate(support_levels.iterrows()):
                self.support_labels[i].config(
                    text=f"Strike: {row['strike_price']}, OI: {row['open_interest']:,.0f}"
                )
            
            # Update strategy text
            strategy = self.generate_skewness_strategy(skewness)
            self.strategy_text.delete(1.0, tk.END)
            self.strategy_text.insert(tk.END, strategy)
            
        except Exception as e:
            messagebox.showerror("Error", f"Error analyzing IV Skewness: {str(e)}")

    def analyze_strike_pressure(self):
        """Analyze buying/selling pressure around ATM strike"""
        try:
            with self.get_db_connection() as conn:
                # Get latest data and ATM strike
                latest_query = """
                SELECT underlying_value 
                FROM nifty_option_chain_data 
                WHERE date_time = (SELECT MAX(date_time) FROM nifty_option_chain_data)
                LIMIT 1
                """
                df_latest = pd.read_sql_query(latest_query, conn)
                if df_latest.empty:
                    return "No data available"
                
                spot_price = df_latest['underlying_value'].iloc[0]
                atm_strike = self.calculate_atm_strike(spot_price)
                
                # Get data for ATM ±5 strikes
                pressure_query = f"""
                SELECT strike_price, option_type, 
                       bid_price, bid_qty, ask_price, ask_qty,
                       total_buy_quantity, total_sell_quantity
                FROM nifty_option_chain_data
                WHERE date_time = (SELECT MAX(date_time) FROM nifty_option_chain_data)
                AND strike_price BETWEEN {atm_strike - 250} AND {atm_strike + 250}
                ORDER BY strike_price, option_type
                """
                
                df = pd.read_sql_query(pressure_query, conn)
                
                analysis = []
                
                # Analyze each strike
                for strike in df['strike_price'].unique():
                    # Fixed syntax for CE data filtering
                    ce_data = df[(df['strike_price'] == strike) & (df['option_type'] == 'CE')].iloc[0]
                    # Fixed syntax for PE data filtering
                    pe_data = df[(df['strike_price'] == strike) & (df['option_type'] == 'PE')].iloc[0]
                    
                    # Calculate pressure indicators
                    ce_pressure = (ce_data['total_buy_quantity'] / ce_data['total_sell_quantity']) if ce_data['total_sell_quantity'] > 0 else 0
                    pe_pressure = (pe_data['total_buy_quantity'] / pe_data['total_sell_quantity']) if pe_data['total_sell_quantity'] > 0 else 0
                    
                    ce_spread = ce_data['ask_price'] - ce_data['bid_price']
                    pe_spread = pe_data['ask_price'] - pe_data['bid_price']
                    
                    analysis.append({
                        'strike': strike,
                        'ce_pressure': ce_pressure,
                        'pe_pressure': pe_pressure,
                        'ce_spread': ce_spread,
                        'pe_spread': pe_spread
                    })
                
                return self.generate_pressure_prediction(analysis, atm_strike, spot_price)
                
        except Exception as e:
            print(f"Error analyzing strike pressure: {e}")
            return "Error in analysis"

    def generate_pressure_prediction(self, analysis, atm_strike, spot_price):
        """Generate prediction based on pressure analysis"""
        above_pressure = []
        below_pressure = []
        
        for item in analysis:
            if item['strike'] > atm_strike:
                if item['ce_pressure'] > 1.2:  # Strong buying in calls
                    above_pressure.append(f"Strong Call buying at {item['strike']}")
                elif item['ce_pressure'] < 0.8:  # Strong selling in calls
                    above_pressure.append(f"Call writing at {item['strike']}")
                
            elif item['strike'] < atm_strike:
                if item['pe_pressure'] > 1.2:  # Strong buying in puts
                    below_pressure.append(f"Strong Put buying at {item['strike']}")
                elif item['pe_pressure'] < 0.8:  # Strong selling in puts
                    below_pressure.append(f"Put writing at {item['strike']}")
        
        # Generate prediction
        prediction = f"ATM Strike: {atm_strike} (Spot: {spot_price:.2f})\n\n"
        
        if above_pressure:
            prediction += "Above ATM:\n• " + "\n• ".join(above_pressure) + "\n\n"
        if below_pressure:
            prediction += "Below ATM:\n• " + "\n• ".join(below_pressure) + "\n\n"
        
        # Overall market sentiment
        if len([p for p in above_pressure if 'writing' in p.lower()]) > len([p for p in above_pressure if 'buying' in p.lower()]):
            prediction += "Market Outlook: Resistance forming above\n"
        elif len([p for p in below_pressure if 'writing' in p.lower()]) > len([p for p in below_pressure if 'buying' in p.lower()]):
            prediction += "Market Outlook: Support forming below\n"
        
        return prediction

    def show_graph_analysis(self):
        """Show individual strike graphs for CE and PE"""
        graph_window = tk.Toplevel(self.root)
        graph_window.title("Strike Price Analysis")
        graph_window.geometry("1200x800")
        
        try:
            with self.get_db_connection() as conn:
                current_date = datetime.now().strftime('%Y-%m-%d')
                
                # Get top 3 volume strikes for CE and PE
                volume_query = f"""
                SELECT strike_price, option_type, SUM(volume) as total_volume
                FROM nifty_option_chain_data
                WHERE date_time LIKE '{current_date}%'
                GROUP BY strike_price, option_type
                """
                df_volume = pd.read_sql_query(volume_query, conn)
                
                ce_strikes = df_volume[df_volume['option_type'] == 'CE'].nlargest(3, 'total_volume')['strike_price'].tolist()
                pe_strikes = df_volume[df_volume['option_type'] == 'PE'].nlargest(3, 'total_volume')['strike_price'].tolist()
                
                # Create figure with subplots (2 rows x 3 columns)
                fig = plt.Figure(figsize=(15, 10))
                fig.suptitle('Strike Price Analysis - Change in OI vs LTP', fontsize=12)
                
                # Plot CE strikes (top row)
                for i, strike in enumerate(ce_strikes):
                    data_query = f"""
                    SELECT date_time, changein_oi, ltp
                    FROM nifty_option_chain_data
                    WHERE date_time LIKE '{current_date}%'
                    AND strike_price = {strike}
                    AND option_type = 'CE'
                    ORDER BY date_time
                    """
                    df = pd.read_sql_query(data_query, conn)
                    df['time'] = pd.to_datetime(df['date_time']).dt.strftime('%H:%M')
                    
                    # Create subplot with two y-axes
                    ax1 = fig.add_subplot(2, 3, i+1)
                    ax2 = ax1.twinx()
                    
                    # Plot Change in OI
                    color1 = '#1f77b4'  # Blue for Change in OI
                    ax1.plot(df['time'], df['changein_oi'], color=color1, label='Change in OI')
                    ax1.set_xlabel('Time')
                    ax1.set_ylabel('Change in OI', color=color1)
                    ax1.tick_params(axis='y', labelcolor=color1)
                    
                    # Plot LTP on secondary y-axis
                    color2 = '#ff7f0e'  # Orange for LTP
                    ax2.plot(df['time'], df['ltp'], color=color2, label='LTP')
                    ax2.set_ylabel('LTP', color=color2)
                    ax2.tick_params(axis='y', labelcolor=color2)
                    
                    # Title and formatting
                    ax1.set_title(f'CE Strike {strike}', fontsize=10)
                    ax1.tick_params(axis='x', rotation=45)
                    
                    # Add legends
                    lines1, labels1 = ax1.get_legend_handles_labels()
                    lines2, labels2 = ax2.get_legend_handles_labels()
                    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left', fontsize=8)
                
                # Plot PE strikes (bottom row)
                for i, strike in enumerate(pe_strikes):
                    data_query = f"""
                    SELECT date_time, changein_oi, ltp
                    FROM nifty_option_chain_data
                    WHERE date_time LIKE '{current_date}%'
                    AND strike_price = {strike}
                    AND option_type = 'PE'
                    ORDER BY date_time
                    """
                    df = pd.read_sql_query(data_query, conn)
                    df['time'] = pd.to_datetime(df['date_time']).dt.strftime('%H:%M')
                    
                    # Create subplot with two y-axes
                    ax1 = fig.add_subplot(2, 3, i+4)
                    ax2 = ax1.twinx()
                    
                    # Plot Change in OI
                    color1 = '#1f77b4'
                    ax1.plot(df['time'], df['changein_oi'], color=color1, label='Change in OI')
                    ax1.set_xlabel('Time')
                    ax1.set_ylabel('Change in OI', color=color1)
                    ax1.tick_params(axis='y', labelcolor=color1)
                    
                    # Plot LTP on secondary y-axes
                    color2 = '#ff7f0e'
                    ax2.plot(df['time'], df['ltp'], color=color2, label='LTP')
                    ax2.set_ylabel('LTP', color=color2)
                    ax2.tick_params(axis='y', labelcolor=color2)
                    
                    # Title and formatting
                    ax1.set_title(f'PE Strike {strike}', fontsize=10)
                    ax1.tick_params(axis='x', rotation=45)
                    
                    # Add legends
                    lines1, labels1 = ax1.get_legend_handles_labels()
                    lines2, labels2 = ax2.get_legend_handles_labels()
                    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left', fontsize=8)
                
                fig.tight_layout()
                
                # Create canvas
                canvas = FigureCanvasTkAgg(fig, graph_window)
                canvas.draw()
                canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
                
        except Exception as e:
            messagebox.showerror("Error", f"Error creating graphs: {str(e)}")

    def analyze_option_data(self, current_data, historical_data, option_type):
        """Analyze option data and generate predictions"""
        try:
            changein_oi = current_data['changein_oi']
            ltp = current_data['ltp']
            
            # Calculate support and resistance using recent data
            support = historical_data['ltp'].quantile(0.25)  # 25th percentile
            resistance = historical_data['ltp'].quantile(0.75)  # 75th percentile
            
            # Get previous values for trend
            prev_oi = historical_data['changein_oi'].iloc[-2] if len(historical_data) > 1 else 0
            prev_ltp = historical_data['ltp'].iloc[-2] if len(historical_data) > 1 else ltp
            
            analysis = []
            
            # Price levels analysis
            price_level = ""
            if ltp > resistance:
                price_level = "above resistance"
            elif ltp < support:
                price_level = "below support"
            else:
                price_level = "between support/resistance"
            
            # Trend Analysis
            oi_trend = "increasing" if changein_oi > prev_oi else "decreasing"
            price_trend = "increasing" if ltp > prev_ltp else "decreasing"
            
            # Combined Analysis
            if option_type == 'CE':
                if oi_trend == "increasing" and price_trend == "increasing":
                    analysis.append(f"Strong Call Buying at {price_level}")
                    analysis.append("Bullish momentum building")
                elif oi_trend == "increasing" and price_trend == "decreasing":
                    analysis.append(f"Call Writing pressure at {price_level}")
                    analysis.append("Bearish signal")
                elif oi_trend == "decreasing" and price_trend == "increasing":
                    analysis.append(f"Call Short Covering at {price_level}")
                    analysis.append("Short-term bullish")
            else:  # PE
                if oi_trend == "increasing" and price_trend == "increasing":
                    analysis.append(f"Strong Put Buying at {price_level}")
                    analysis.append("Bearish momentum building")
                elif oi_trend == "increasing" and price_trend == "decreasing":
                    analysis.append(f"Put Writing support at {price_level}")
                    analysis.append("Bullish signal")
                elif oi_trend == "decreasing" and price_trend == "increasing":
                    analysis.append(f"Put Short Covering at {price_level}")
                    analysis.append("Short-term bearish")
            
            # Support/Resistance Break Analysis
            if ltp > resistance and changein_oi > 0:
                analysis.append(f"Potential resistance break at {resistance:.2f}")
            elif ltp < support and changein_oi > 0:
                analysis.append(f"Support might break at {support:.2f}")
            
            return {
                'analysis': analysis,
                'support': support,
                'resistance': resistance,
                'oi_trend': oi_trend,
                'price_trend': price_trend
            }
            
        except Exception as e:
            return {'analysis': [f"Analysis Error: {str(e)}"]}

    def generate_market_summary(self):
        """Generate detailed market summary with CE and PE analysis"""
        try:
            with self.get_db_connection() as conn:
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # Get current market price
                price_query = """
                SELECT underlying_value 
                FROM nifty_option_chain_data 
                WHERE date_time = (SELECT MAX(date_time) FROM nifty_option_chain_data)
                LIMIT 1
                """
                current_price = pd.read_sql_query(price_query, conn)['underlying_value'].iloc[0]
                
                # Function to get nearest strike data
                def get_strike_data(option_type, current_price):
                    query = f"""
                    SELECT *
                    FROM nifty_option_chain_data
                    WHERE date_time = (SELECT MAX(date_time) FROM nifty_option_chain_data)
                    AND option_type = '{option_type}'
                    AND strike_price {'>=' if option_type == 'CE' else '<='} {current_price}
                    ORDER BY volume DESC
                    LIMIT 1
                    """
                    return pd.read_sql_query(query, conn).iloc[0]
                
                # Get data for both CE and PE
                ce_data = get_strike_data('CE', current_price)
                pe_data = get_strike_data('PE', current_price)
                
                # Get historical data for both
                def get_historical_data(strike_price, option_type):
                    query = f"""
                    SELECT date_time, changein_oi, ltp
                    FROM nifty_option_chain_data
                    WHERE strike_price = {strike_price}
                    AND option_type = '{option_type}'
                    ORDER BY date_time DESC
                    LIMIT 10
                    """
                    return pd.read_sql_query(query, conn)
                
                ce_hist = get_historical_data(ce_data['strike_price'], 'CE')
                pe_hist = get_historical_data(pe_data['strike_price'], 'PE')
                
                # Generate analysis for both
                ce_analysis = self.analyze_option_data(ce_data, ce_hist, 'CE')
                pe_analysis = self.analyze_option_data(pe_data, pe_hist, 'PE')
                
                # Create summary
                summary = f"\n=== Market Update {current_time} ===\n"
                summary += f"Current Price: {current_price:,.2f}\n\n"
                
                # CE Analysis
                summary += f"CE Strike {ce_data['strike_price']} Analysis:\n"
                summary += f"LTP: {ce_data['ltp']:.2f} | OI Change: {ce_data['changein_oi']:+,d}\n"
                summary += "\n".join(f"• {point}" for point in ce_analysis['analysis'])
                summary += f"\nTrend: {ce_analysis['oi_trend']} OI, {ce_analysis['price_trend']} price\n\n"
                
                # PE Analysis
                summary += f"PE Strike {pe_data['strike_price']} Analysis:\n"
                summary += f"LTP: {pe_data['ltp']:.2f} | OI Change: {pe_data['changein_oi']:+,d}\n"
                summary += "\n".join(f"• {point}" for point in pe_analysis['analysis'])
                summary += f"\nTrend: {pe_analysis['oi_trend']} OI, {pe_analysis['price_trend']} price\n\n"
                
                # Overall Market Sentiment
                summary += "Market Sentiment:\n"
                
                # Analyze CE and PE trends together
                if ce_analysis['oi_trend'] == "increasing" and pe_analysis['oi_trend'] == "decreasing":
                    summary += "• Bullish bias - Call buying with Put unwinding\n"
                    summary += "• Traders building long positions\n"
                    summary += "• Expect upward movement\n"
                elif ce_analysis['oi_trend'] == "decreasing" and pe_analysis['oi_trend'] == "increasing":
                    summary += "• Bearish bias - Put buying with Call unwinding\n"
                    summary += "• Traders building short positions\n"
                    summary += "• Expect downward movement\n"
                elif ce_analysis['oi_trend'] == "increasing" and pe_analysis['oi_trend'] == "increasing":
                    if ce_data['changein_oi'] > pe_data['changein_oi']:
                        summary += "• Moderately Bullish - Stronger Call writing\n"
                        summary += "• Resistance building above\n"
                    else:
                        summary += "• Moderately Bearish - Stronger Put writing\n"
                        summary += "• Support building below\n"
                elif ce_analysis['oi_trend'] == "decreasing" and pe_analysis['oi_trend'] == "decreasing":
                    if ce_data['ltp'] > pe_data['ltp']:
                        summary += "• Short-term Bullish - Call short covering dominant\n"
                        summary += "• Potential upward movement\n"
                    else:
                        summary += "• Short-term Bearish - Put short covering dominant\n"
                        summary += "• Potential downward movement\n"
                else:
                    summary += "• Market in consolidation\n"
                    summary += "• No clear directional bias\n"
                    summary += "• Wait for breakout signals\n"

                # Add price action confirmation
                if ce_analysis['price_trend'] == pe_analysis['price_trend']:
                    if ce_analysis['price_trend'] == "increasing":
                        summary += "• Price action confirms upward momentum\n"
                    else:
                        summary += "• Price action confirms downward momentum\n"
                
                # Add volume-based insight
                if ce_data['volume'] > pe_data['volume']:
                    summary += "• Higher CE volume indicates bullish interest\n"
                else:
                    summary += "• Higher PE volume indicates bearish interest\n"

                # Add to text widget and scroll
                self.summary_text.insert(tk.END, summary)
                self.summary_text.see(tk.END)
                
                # Keep last 8 reports
                content = self.summary_text.get("1.0", tk.END).split("===")
                if len(content) > 16:
                    self.summary_text.delete("1.0", tk.END)
                    self.summary_text.insert(tk.END, "===".join(content[-16:]))
                
        except Exception as e:
            print(f"Error generating summary: {e}")

    def show_ltp_analysis(self):
        """Show detailed analysis graphs for highest volume CE and PE"""
        graph_window = tk.Toplevel(self.root)
        graph_window.title("Option Analysis")
        graph_window.geometry("1800x1000")
        
        # Create main container
        main_container = ttk.Frame(graph_window)
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Create left frame for graphs with reduced width
        graph_frame = ttk.Frame(main_container)
        graph_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5,0))
        
        # Create right frame for status with increased width
        status_frame = ttk.LabelFrame(main_container, text="Market Analysis", padding=10)
        status_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5, ipadx=20)
        
        try:
            with self.get_db_connection() as conn:
                current_date = datetime.now().strftime('%Y-%m-%d')
                
                # Get highest volume strikes
                volume_query = f"""
                SELECT strike_price, option_type, SUM(volume) as total_volume
                FROM nifty_option_chain_data
                WHERE date_time LIKE '{current_date}%'
                GROUP BY strike_price, option_type
                ORDER BY total_volume DESC
                """
                df_volume = pd.read_sql_query(volume_query, conn)
                
                # Ensure we have data
                if df_volume.empty:
                    messagebox.showerror("Error", "No data available for analysis")
                    return
                    
                ce_strike = df_volume[df_volume['option_type'] == 'CE'].iloc[0]['strike_price']
                pe_strike = df_volume[df_volume['option_type'] == 'PE'].iloc[0]['strike_price']
                
                # Get data for both strikes with explicit columns
                data_query = f"""
                SELECT date_time, strike_price, option_type, 
                       open_interest, ltp, iv
                FROM nifty_option_chain_data
                WHERE date_time LIKE '{current_date}%'
                AND strike_price IN ({ce_strike}, {pe_strike})
                ORDER BY date_time
                """
                df = pd.read_sql_query(data_query, conn)
                
                # Check if we have data
                if df.empty:
                    messagebox.showerror("Error", "No data available for selected strikes")
                    return
                    
                df['time'] = pd.to_datetime(df['date_time']).dt.strftime('%H:%M')
                
                # Modify figure size and layout
                fig = plt.Figure(figsize=(10, 12))  # Reduced width, increased height
                fig.subplots_adjust(hspace=0.3, top=0.95)  # Reduced space between plots, moved up
                
                # Filter data for CE and PE
                ce_data = df[(df['option_type'] == 'CE') & (df['strike_price'] == ce_strike)]
                pe_data = df[(df['option_type'] == 'PE') & (df['strike_price'] == pe_strike)]
                
                # Plot 1: Open Interest - adjusted position
                ax1 = fig.add_subplot(311)
                ax1.plot(ce_data['time'], ce_data['open_interest'], 'b-', label=f'CE {ce_strike} OI', linewidth=2)
                ax1.plot(pe_data['time'], pe_data['open_interest'], 'r-', label=f'PE {pe_strike} OI', linewidth=2)
                
                oi_max = max(ce_data['open_interest'].max(), pe_data['open_interest'].max())
                oi_min = min(ce_data['open_interest'].min(), pe_data['open_interest'].min())
                margin = (oi_max - oi_min) * 0.2  # Increased margin
                ax1.set_ylim(oi_min - margin, oi_max + margin)
                
                ax1.set_title('Open Interest Comparison', fontsize=12, pad=10)
                ax1.set_xlabel('Time', fontsize=10)
                ax1.set_ylabel('Open Interest', fontsize=10)
                ax1.tick_params(axis='x', rotation=45)
                ax1.legend(fontsize=10)
                ax1.grid(True)
                
                # Plot 2: LTP - adjusted position
                ax2 = fig.add_subplot(312)
                ax2.plot(ce_data['time'], ce_data['ltp'], 'b-', label=f'CE {ce_strike} LTP', linewidth=2)
                ax2.plot(pe_data['time'], pe_data['ltp'], 'r-', label=f'PE {pe_strike} LTP', linewidth=2)
                
                ltp_max = max(ce_data['ltp'].max(), pe_data['ltp'].max())
                ltp_min = min(ce_data['ltp'].min(), pe_data['ltp'].min())
                margin = (ltp_max - ltp_min) * 0.2  # Increased margin
                ax2.set_ylim(ltp_min - margin, ltp_max + margin)
                
                ax2.set_title('LTP Comparison', fontsize=12, pad=10)
                ax2.set_xlabel('Time', fontsize=10)
                ax2.set_ylabel('LTP', fontsize=10)
                ax2.tick_params(axis='x', rotation=45)
                ax2.legend(fontsize=10)
                ax2.grid(True)
                
                # Plot 3: IV - adjusted position
                ax3 = fig.add_subplot(313)
                ax3.plot(ce_data['time'], ce_data['iv'], 'b-', label=f'CE {ce_strike} IV', linewidth=2)
                ax3.plot(pe_data['time'], pe_data['iv'], 'r-', label=f'PE {pe_strike} IV', linewidth=2)
                
                iv_max = max(ce_data['iv'].max(), pe_data['iv'].max())
                iv_min = min(ce_data['iv'].min(), pe_data['iv'].min())
                margin = (iv_max - iv_min) * 0.2  # Increased margin
                ax3.set_ylim(iv_min - margin, iv_max + margin)
                
                ax3.set_title('IV Comparison', fontsize=12, pad=10)
                ax3.set_xlabel('Time', fontsize=10)
                ax3.set_ylabel('IV', fontsize=10)
                ax3.tick_params(axis='x', rotation=45)
                ax3.legend(fontsize=10)
                ax3.grid(True)
                
                fig.tight_layout(rect=[0, 0, 1, 0.95])  # Adjust layout to move plots up
                
                # Create canvas with adjusted size
                canvas = FigureCanvasTkAgg(fig, graph_frame)
                canvas.draw()
                canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
                
                # Status text with increased width
                status_text = tk.Text(status_frame, width=50, height=40, wrap=tk.WORD, 
                                    font=("Helvetica", 11))
                status_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
                
                # Generate market analysis
                def generate_market_analysis(ce_data, pe_data):
                    analysis = []
                    
                    # Get latest values
                    latest_ce = ce_data.iloc[-1]
                    latest_pe = pe_data.iloc[-1]
                    
                    # OI Analysis
                    ce_oi_change = latest_ce['open_interest'] - ce_data.iloc[-2]['open_interest']
                    pe_oi_change = latest_pe['open_interest'] - pe_data.iloc[-2]['open_interest']
                    
                    analysis.append(f"=== Market Signals Analysis ===\n")
                    
                    # OI-based signals
                    if ce_oi_change > 0 and pe_oi_change < 0:
                        analysis.append("🔵 Strong Bullish Signal:")
                        analysis.append("• CE writing with PE unwinding")
                        analysis.append("• Potential upward breakout")
                    elif ce_oi_change < 0 and pe_oi_change > 0:
                        analysis.append("🔴 Strong Bearish Signal:")
                        analysis.append("• PE writing with CE unwinding")
                        analysis.append("• Potential downward breakout")
                    
                    # LTP Analysis
                    ce_ltp_change = latest_ce['ltp'] - ce_data.iloc[-2]['ltp']
                    pe_ltp_change = latest_pe['ltp'] - pe_data.iloc[-2]['ltp']
                    
                    analysis.append("\n=== Price Action Analysis ===")
                    if ce_ltp_change > 0 and pe_ltp_change < 0:
                        analysis.append("• Bullish price action")
                        analysis.append("• CE gaining strength")
                    elif ce_ltp_change < 0 and pe_ltp_change > 0:
                        analysis.append("• Bearish price action")
                        analysis.append("• PE gaining strength")
                    
                    # IV Analysis
                    analysis.append("\n=== Volatility Analysis ===")
                    if latest_ce['iv'] > latest_pe['iv']:
                        analysis.append("• Higher CE volatility")
                        analysis.append("• Potential upside movement")
                    else:
                        analysis.append("• Higher PE volatility")
                        analysis.append("• Potential downside movement")
                    
                    # Premium Erosion Check
                    analysis.append("\n=== Premium Analysis ===")
                    if (ce_data['iv'].iloc[-3:].is_monotonic_decreasing and 
                        pe_data['iv'].iloc[-3:].is_monotonic_decreasing):
                        analysis.append("⚠️ Premium Erosion Alert:")
                        analysis.append("• Both CE & PE IV declining")
                        analysis.append("• Time decay acceleration")
                    
                    # Consolidation Check
                    analysis.append("\n=== Pattern Analysis ===")
                    ce_ltp_std = ce_data['ltp'].tail(5).std()
                    pe_ltp_std = pe_data['ltp'].tail(5).std()
                    if ce_ltp_std < ce_data['ltp'].mean() * 0.01 and pe_ltp_std < pe_data['ltp'].mean() * 0.01:
                        analysis.append("📊 Consolidation Pattern:")
                        analysis.append("• Low price volatility")
                        analysis.append("• Breakout expected soon")
                    
                    # Breakout Analysis
                    analysis.append("\n=== Breakout Analysis ===")
                    ce_resistance = ce_data['ltp'].tail(10).max()
                    ce_support = ce_data['ltp'].tail(10).min()
                    pe_resistance = pe_data['ltp'].tail(10).max()
                    pe_support = pe_data['ltp'].tail(10).min()
                    
                    if latest_ce['ltp'] > ce_resistance * 0.98:
                        analysis.append("🔼 CE Breakout Potential:")
                        analysis.append("• Near resistance level")
                        analysis.append(f"• Resistance: {ce_resistance:.2f}")
                    elif latest_pe['ltp'] > pe_resistance * 0.98:
                        analysis.append("🔽 PE Breakout Potential:")
                        analysis.append("• Near resistance level")
                        analysis.append(f"• Resistance: {pe_resistance:.2f}")
                    
                    return "\n".join(analysis)
                
                # Generate and display analysis
                analysis = generate_market_analysis(ce_data, pe_data)
                status_text.insert(tk.END, analysis)
                status_text.config(state=tk.DISABLED)
                
        except Exception as e:
            messagebox.showerror("Error", f"Error creating analysis: {str(e)}")

    def analyze_option_trends(self, ce_data, pe_data):
        """Analyze recent trends in option data"""
        try:
            analysis = []
            
            # Analyze OI trends
            ce_oi_trend = "increasing" if ce_data['open_interest'].is_monotonic_increasing else \
                         "decreasing" if ce_data['open_interest'].is_monotonic_decreasing else "flat"
            pe_oi_trend = "increasing" if pe_data['open_interest'].is_monotonic_increasing else \
                         "decreasing" if pe_data['open_interest'].is_monotonic_decreasing else "flat"
            
            # Analyze IV trends
            ce_iv_trend = "increasing" if ce_data['iv'].is_monotonic_increasing else \
                         "decreasing" if ce_data['iv'].is_monotonic_decreasing else "flat"
            pe_iv_trend = "increasing" if pe_data['iv'].is_monotonic_increasing else \
                         "decreasing" if pe_data['iv'].is_monotonic_decreasing else "flat"
            
            # Check for premium erosion
            if ce_iv_trend == "decreasing" and pe_iv_trend == "decreasing":
                analysis.append("Premium Erosion Alert: Both CE and PE IV declining")
            
            # Market direction analysis
            if ce_oi_trend == "increasing" and pe_oi_trend == "decreasing":
                analysis.append("Bullish Signal: Call writing with Put unwinding")
            elif ce_oi_trend == "decreasing" and pe_oi_trend == "increasing":
                analysis.append("Bearish Signal: Put writing with Call unwinding")
            elif ce_oi_trend == "flat" and pe_oi_trend == "flat":
                analysis.append("Market in Consolidation: No clear directional bias")
            
            # IV analysis
            if ce_iv_trend != "flat" or pe_iv_trend != "flat":
                analysis.append(f"Volatility: CE {ce_iv_trend}, PE {pe_iv_trend}")
            
            return "\n".join(analysis)
            
        except Exception as e:
            return f"Analysis Error: {str(e)}"

    def calculate_greeks(self, S, K, T, r, sigma, option_type):
        """Calculate option Greeks"""
        try:
            from scipy.stats import norm
            import numpy as np
            
            # Convert to float and ensure positive values
            S = abs(float(S))  # Spot price
            K = abs(float(K))  # Strike price
            T = max(float(T), 0.00001)  # Time to expiry in years (prevent zero)
            r = float(r)  # Risk-free rate
            sigma = max(float(sigma), 0.00001)  # Volatility (IV)
            
            # Calculate d1 and d2
            d1 = (np.log(S/K) + (r + sigma**2/2)*T) / (sigma*np.sqrt(T))
            d2 = d1 - sigma*np.sqrt(T)
            
            # Standard normal PDF and CDF
            N_d1 = norm.cdf(d1)
            N_d2 = norm.cdf(d2)
            N_prime_d1 = norm.pdf(d1)
            
            if option_type == 'CE':
                delta = N_d1
                # Theta for Call = -(S*sigma*N'(d1))/(2*sqrt(T)) - r*K*e^(-rT)*N(d2)
                theta = (-(S * sigma * N_prime_d1) / (2 * np.sqrt(T)) - 
                        r * K * np.exp(-r * T) * N_d2) / 365  # Convert to daily theta
            else:  # PE
                delta = N_d1 - 1  # or -N(-d1)
                # Theta for Put = -(S*sigma*N'(d1))/(2*sqrt(T)) + r*K*e^(-rT)*N(-d2)
                theta = (-(S * sigma * N_prime_d1) / (2 * np.sqrt(T)) + 
                        r * K * np.exp(-r * T) * (1 - N_d2)) / 365  # Convert to daily theta
            
            return delta, theta
            
        except Exception as e:
            print(f"Error calculating Greeks: {e}")
            return 0, 0

    def show_greeks_analysis(self):
        """Show Greeks analysis for highest volume strikes"""
        graph_window = tk.Toplevel(self.root)
        graph_window.title("Option Greeks Analysis")
        graph_window.geometry("1800x1000")
        
        # Create main container
        main_container = ttk.Frame(graph_window)
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Create left frame for graphs
        graph_frame = ttk.Frame(main_container)
        graph_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5,0))
        
        # Create right frame for analysis
        analysis_frame = ttk.LabelFrame(main_container, text="Greeks Analysis", padding=10)
        analysis_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5, ipadx=20)
        
        try:
            with self.get_db_connection() as conn:
                # Get current date and expiry date
                current_date = datetime.now().strftime('%Y-%m-%d')
                
                # Get expiry date from database
                expiry_query = """
                SELECT DISTINCT expiry_date 
                FROM nifty_option_chain_data 
                WHERE date_time LIKE ? 
                LIMIT 1
                """
                expiry_date = pd.read_sql_query(expiry_query, conn, params=(f"{current_date}%",)).iloc[0]['expiry_date']
                
                # Get highest volume strikes
                volume_query = f"""
                SELECT strike_price, option_type, SUM(volume) as total_volume
                FROM nifty_option_chain_data
                WHERE date_time LIKE '{current_date}%'
                GROUP BY strike_price, option_type
                ORDER BY total_volume DESC
                """
                df_volume = pd.read_sql_query(volume_query, conn)
                
                ce_strike = df_volume[df_volume['option_type'] == 'CE'].iloc[0]['strike_price']
                pe_strike = df_volume[df_volume['option_type'] == 'PE'].iloc[0]['strike_price']
                
                # Get data for Greeks calculation
                data_query = f"""
                SELECT date_time, strike_price, option_type, 
                       underlying_value as spot_price, iv
                FROM nifty_option_chain_data
                WHERE date_time LIKE '{current_date}%'
                AND strike_price IN ({ce_strike}, {pe_strike})
                ORDER BY date_time
                """
                df = pd.read_sql_query(data_query, conn)
                df['time'] = pd.to_datetime(df['date_time']).dt.strftime('%H:%M')
                
                # Calculate time to expiry using actual expiry date
                df['tte'] = (pd.to_datetime(expiry_date) - pd.to_datetime(df['date_time'])).dt.total_seconds()/(365*24*60*60)
                
                # Calculate Greeks
                risk_free_rate = 0.05  # 5% risk-free rate
                
                for idx, row in df.iterrows():
                    if row['tte'] > 0:  # Only calculate for valid time to expiry
                        delta, theta = self.calculate_greeks(
                            row['spot_price'], row['strike_price'], row['tte'],
                            risk_free_rate, row['iv']/100, row['option_type']
                        )
                        df.loc[idx, 'delta'] = delta
                        df.loc[idx, 'theta'] = theta
                    else:
                        df.loc[idx, 'delta'] = 0
                        df.loc[idx, 'theta'] = 0
                
                # Plot CE Greeks
                ce_data = df[df['option_type'] == 'CE']
                pe_data = df[df['option_type'] == 'PE']
                
                # Create figure with subplots
                fig = plt.Figure(figsize=(10, 12))
                fig.subplots_adjust(hspace=0.4)
                
                # CE Delta
                ax1 = fig.add_subplot(321)
                ax1.plot(ce_data['time'], ce_data['delta'], 'b-', label=f'CE {ce_strike}')
                ax1.set_title('CE Delta', fontsize=10)
                ax1.set_xlabel('Time')
                ax1.set_ylabel('Delta')
                ax1.tick_params(axis='x', rotation=45)
                ax1.legend(fontsize=8)
                ax1.grid(True)
                
                # CE Theta
                ax2 = fig.add_subplot(322)
                ax2.plot(ce_data['time'], ce_data['theta'], 'b-', label=f'CE {ce_strike}')
                ax2.set_title('CE Theta', fontsize=10)
                ax2.set_xlabel('Time')
                ax2.set_ylabel('Theta')
                ax2.tick_params(axis='x', rotation=45)
                ax2.legend(fontsize=8)
                ax2.grid(True)
                
                # PE Delta
                ax3 = fig.add_subplot(323)
                ax3.plot(pe_data['time'], pe_data['delta'], 'r-', label=f'PE {pe_strike}')
                ax3.set_title('PE Delta', fontsize=10)
                ax3.set_xlabel('Time')
                ax3.set_ylabel('Delta')
                ax3.tick_params(axis='x', rotation=45)
                ax3.legend(fontsize=8)
                ax3.grid(True)
                
                # PE Theta
                ax4 = fig.add_subplot(324)
                ax4.plot(pe_data['time'], pe_data['theta'], 'r-', label=f'PE {pe_strike}')
                ax4.set_title('PE Theta', fontsize=10)
                ax4.set_xlabel('Time')
                ax4.set_ylabel('Theta')
                ax4.tick_params(axis='x', rotation=45)
                ax4.legend(fontsize=8)
                ax4.grid(True)
                
                fig.tight_layout()
                
                # Create canvas
                canvas = FigureCanvasTkAgg(fig, graph_frame)
                canvas.draw()
                canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
                
                # Generate and display analysis
                analysis_text = tk.Text(analysis_frame, width=50, height=40, wrap=tk.WORD, 
                                      font=("Helvetica", 11))
                analysis_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
                
                # Generate analysis
                analysis = self.analyze_greeks(ce_data.iloc[-1], pe_data.iloc[-1])
                analysis_text.insert(tk.END, analysis)
                analysis_text.config(state=tk.DISABLED)
                
        except Exception as e:
            messagebox.showerror("Error", f"Error in Greeks analysis: {str(e)}")

    def analyze_greeks(self, ce_data, pe_data):
        """Analyze Greeks and generate trading insights"""
        analysis = []
        
        analysis.append(f"=== Greeks Analysis ===\n")
        analysis.append(f"CE Strike: {ce_data['strike_price']}")
        analysis.append(f"PE Strike: {pe_data['strike_price']}")
        analysis.append(f"Days to Expiry: {ce_data['tte']*365:.1f} days\n")
        
        # Delta Analysis
        analysis.append("Delta Analysis:")
        if abs(ce_data['delta']) > 0.5:
            analysis.append("• CE Delta > 0.5: High directional risk")
            analysis.append(f"• Current Delta: {ce_data['delta']:.2f}")
            if ce_data['tte']*365 < 2:  # Less than 2 days to expiry
                analysis.append("• Near expiry - High gamma risk")
        if abs(pe_data['delta']) > 0.5:
            analysis.append("• PE Delta > 0.5: High directional risk")
            analysis.append(f"• Current Delta: {pe_data['delta']:.2f}")
            if pe_data['tte']*365 < 2:  # Less than 2 days to expiry
                analysis.append("• Near expiry - High gamma risk")
        
        # Theta Analysis
        analysis.append("\nTheta Analysis:")
        analysis.append(f"• CE Theta: {ce_data['theta']:.2f}")
        analysis.append(f"• PE Theta: {pe_data['theta']:.2f}")
        if ce_data['theta'] < pe_data['theta']:
            analysis.append("• CE experiencing higher time decay")
            analysis.append(f"• Daily CE theta decay: ₹{abs(ce_data['theta']):.2f}")
        else:
            analysis.append("• PE experiencing higher time decay")
            analysis.append(f"• Daily PE theta decay: ₹{abs(pe_data['theta']):.2f}")
        
        # Time Decay Risk
        if ce_data['tte']*365 < 5:  # Less than 5 days to expiry
            analysis.append("\n⚠️ High Time Decay Risk:")
            analysis.append("• Less than 5 days to expiry")
            analysis.append("• Accelerated theta decay")
            analysis.append("• Consider rolling positions forward")
        
        # Trading Signals based on Greeks
        analysis.append("\nTrading Signals:")
        if ce_data['delta'] > 0.6 and ce_data['theta'] < -10:
            analysis.append("🔵 Strong CE Signal:")
            analysis.append("• High delta indicates strong directional move")
            analysis.append(f"• But theta decay of ₹{abs(ce_data['theta']):.2f} per day")
        elif pe_data['delta'] < -0.6 and pe_data['theta'] < -10:
            analysis.append("🔴 Strong PE Signal:")
            analysis.append("• High delta indicates strong directional move")
            analysis.append(f"• But theta decay of ₹{abs(pe_data['theta']):.2f} per day")
        
        # Risk Assessment
        analysis.append("\nRisk Assessment:")
        total_risk = abs(ce_data['delta']) + abs(pe_data['delta'])
        if total_risk > 1.2:
            analysis.append("⚠️ High Risk Environment:")
            analysis.append(f"• Combined delta exposure: {total_risk:.2f}")
            analysis.append(f"• Total daily theta: ₹{abs(ce_data['theta'] + pe_data['theta']):.2f}")
            analysis.append("• Consider reducing position size")
        else:
            analysis.append("✅ Moderate Risk Environment:")
            analysis.append(f"• Combined delta exposure: {total_risk:.2f}")
            analysis.append(f"• Total daily theta: ₹{abs(ce_data['theta'] + pe_data['theta']):.2f}")
            analysis.append("• Regular position sizing acceptable")
        
        return "\n".join(analysis)

if __name__ == "__main__":
    root = ttk.Window(themename="darkly")
    app = OptionMonitor(root)
    
    def on_closing():
        app.stop_monitoring()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop() 