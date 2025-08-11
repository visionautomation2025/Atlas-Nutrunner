  import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk
import aiohttp
import asyncio
import json
import sqlite3
from datetime import datetime, timedelta
import platform
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Set CustomTkinter appearance and color theme
ctk.set_appearance_mode("DARK")
ctk.set_default_color_theme("blue")

class CustomBooleanControl(tk.Canvas):
    def __init__(self, parent, *args, **kwargs):
        tk.Canvas.__init__(self, parent, *args, **kwargs)
        self.circle = self.create_oval(10, 10, 50, 50, fill="grey")
    
    def set_state(self, state):
        if state:
            self.itemconfig(self.circle, fill="green")
        else:
            self.itemconfig(self.circle, fill="red")

class CustomTreeview(ttk.ttkTreeview):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self.tag_configure('negative_value', foreground='red')
        self.tag_configure('negative_value', foreground='black')
        self.tag_configure('atm', background='#FFFFD1')
        self.tag_configure('above_atm', background='#F8F8F8')
        self.tag_configure('below_atm', background='#F0F0F0')
        
        
class CustomBooleanControl(tk.Canvas):
    def __init__(self, parent, *args, **kwargs):
        tk.Canvas.__init__(self, parent, *args, **kwargs)
        self.circle = self.create_oval(10, 10, 50, 50, fill="grey")
    
    def set_state(self, state):
        if state:
            self.itemconfig(self.circle, fill="green")
        else:
            self.itemconfig(self.circle, fill="red")
class CustomTreeview(ttk.Treeview):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self.tag_configure('negative_value', foreground='red')
        self.tag_configure('atm', background='#FFFFD1')
        self.tag_configure('above_atm', background='#F8F8F8')
        self.tag_configure('below_atm', background='#F0F0F0')
        
    def insert(self, parent_iid, index, **kwargs):
        """Override insert method to handle cell styling"""
        item = super().insert(parent_iid, index, **kwargs)
        values = kwargs.get('values', [])
        if len(values) >= 6:  # Updated for new column count
            try:
                change_value = float(values[5])  # Updated index for change value
                if change_value < 0:
                    super().set(item, "Chng", f"{change_value}")
                    tags = list(self.item(item)['tags'] or [])
                    tags.append('negative_value')
                    self.item(item, tags=tags)
            except (ValueError, TypeError):
                pass
        return item

class NiftyOptionChain:
    def __init__(self):
        self.url_oc = "https://www.nseindia.com/option-chain"
        self.url_nf = 'https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY'
        self.headers = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36',
            'accept-language': 'en,gu;q=0.9,hi;q=0.8',
            'accept-encoding': 'gzip, deflate, br'
        }
        self.cookies = {}
        self.session = None

    async def initialize_session(self):
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

    async def get_data(self):
        if not self.session:
            await self.initialize_session()
        
        try:
            async with self.session.get(self.url_nf, headers=self.headers, cookies=self.cookies, timeout=5) as response:
                if response.status == 401:
                    await self.initialize_session()
                    async with self.session.get(self.url_nf, headers=self.headers, cookies=self.cookies, timeout=5) as response:
                        return await response.text()
                elif response.status == 200:
                    return await response.text()
                else:
                    raise Exception(f"Unexpected status code: {response.status}")
        except Exception as e:
            print(f"Error fetching data: {e}")
            raise

    async def close(self):
        if self.session:
            await self.session.close()

class NiftyApp:
    def __init__(self, root):
        # Ensure root is a CustomTkinter window
        if not isinstance(root, ctk.CTk):
            root = ctk.CTk()
        
        self.root = root
        self.root.title("Nifty Option Chain Viewer")
        self.root.geometry("1600x800")
        
        self.nifty_client = NiftyOptionChain()
        self.setup_database()
        self.setup_ui()
        self.setup_async_loop()

    def setup_ui(self):
        # Main CustomTkinter container
        main_container = ctk.CTkFrame(self.root)
        main_container.pack(fill="both", expand=True, padx=10, pady=10)

        # Header frame
        header_frame = ctk.CTkFrame(main_container)
        header_frame.pack(fill="x", pady=(0, 10))

        # Price displays
        price_frame = ctk.CTkFrame(header_frame)
        price_frame.pack(side="left")

        ctk.CTkLabel(price_frame, text="Current Market Price:", font=("Arial", 12)).pack(side="left")
        self.price_label = ctk.CTkLabel(price_frame, text="--", font=("Arial", 12, 'bold'))
        self.price_label.pack(side="left", padx=(5, 20))

        ctk.CTkLabel(price_frame, text="ATM Strike:", font=("Arial", 12)).pack(side="left")
        self.atm_label = ctk.CTkLabel(price_frame, text="--", font=("Arial", 12, 'bold'))
        self.atm_label.pack(side="left", padx=5)

        # Timestamp 
        self.timestamp_label = ctk.CTkLabel(header_frame, text="Last Updated: --", font=("Arial", 10))
        self.timestamp_label.pack(side="right")

        # Chain frame setup (similar to previous implementation)
        chain_frame = ctk.CTkFrame(main_container)
        chain_frame.pack(fill="both", expand=True)

        # CE Frame 
        ce_frame = ctk.CTkFrame(chain_frame)
        ce_frame.pack(side="left", fill="both", expand=True, padx=(0, 5), pady=5)
        
        ce_label = ctk.CTkLabel(ce_frame, text="Call Options (CE)", font=("Arial", 12, "bold"))
        ce_label.pack(pady=5)

        # PE Frame
        pe_frame = ctk.CTkFrame(chain_frame)
        pe_frame.pack(side="left", fill="both", expand=True, padx=(5, 0))
        
        pe_label = ctk.CTkLabel(pe_frame, text="Put Options (PE)", font=("Arial", 12, "bold"))
        pe_label.pack(pady=5)

        # Columns definition
        columns = ("Strike", "OI", "Chng in OI", "Volume", "LTP", "Chng", "IV")

        # CE Treeview
        self.ce_tree = CustomTreeview(ce_frame, columns=columns, show="headings", height=15)
        ce_scroll = ctk.CTkScrollbar(ce_frame, orientation="vertical", command=self.ce_tree.yview)
        self.ce_tree.configure(yscrollcommand=ce_scroll.set)

        # PE Treeview
        self.pe_tree = CustomTreeview(pe_frame, columns=columns, show="headings", height=15)
        pe_scroll = ctk.CTkScrollbar(pe_frame, orientation="vertical", command=self.pe_tree.yview)
        self.pe_tree.configure(yscrollcommand=pe_scroll.set)

        # Configure columns for both treeviews
        for tree in (self.ce_tree, self.pe_tree):
            for col in columns:
                tree.heading(col, text=col)
                tree.column(col, width=80, anchor="center")

        # Pack treeviews and scrollbars
        self.ce_tree.pack(side="left", fill="both", expand=True)
        ce_scroll.pack(side="right", fill="y")
        self.pe_tree.pack(side="left", fill="both", expand=True)
        pe_scroll.pack(side="right", fill="y")
        
                # Volume CE Frame (Bottom Left)
        volume_ce_frame = ctk.CTkFrame(main_container, border_width=1, border_color="gray")
        volume_ce_frame.pack(side="left", fill="x", expand=False, pady=(10, 0))
        ctk.CTkLabel(volume_ce_frame, text="Top 3 High Volume CE", font=("Arial", 12, "bold")).pack(pady=(5,5))

        # Volume PE Frame (Bottom Right)
        volume_pe_frame = ctk.CTkFrame(main_container, border_width=1, border_color="gray")
        volume_pe_frame.pack(side="right", fill="x", expand=False, pady=(10, 0))
        ctk.CTkLabel(volume_pe_frame, text="Top 3 High Volume PE", font=("Arial", 12, "bold")).pack(pady=(5,5))

        # Treeview for Volume CE Track
        volume_ce_columns = ("Strike", "Volume", "OI", "Chng in OI", "LTP", "Chng", "Trend")
        self.volume_ce_tree = CustomTreeview(volume_ce_frame, columns=volume_ce_columns, show="headings", height=5)
        volume_ce_scroll = ctk.CTkScrollbar(volume_ce_frame, orientation="vertical", command=self.volume_ce_tree.yview)
        self.volume_ce_tree.configure(yscrollcommand=volume_ce_scroll.set)

        # Treeview for Volume PE Track
        volume_pe_columns = ("Strike", "Volume", "OI", "Chng in OI", "LTP", "Chng", "Trend")
        self.volume_pe_tree = CustomTreeview(volume_pe_frame, columns=volume_pe_columns, show="headings", height=5)
        volume_pe_scroll = ctk.CTkScrollbar(volume_pe_frame, orientation="vertical", command=self.volume_pe_tree.yview)
        self.volume_pe_tree.configure(yscrollcommand=volume_pe_scroll.set)

        # Configure columns for Volume CE Track
        for col in volume_ce_columns:
            self.volume_ce_tree.heading(col, text=col)
            self.volume_ce_tree.column(col, width=100, anchor="center")

        # Configure columns for Volume PE Track
        for col in volume_pe_columns:
            self.volume_pe_tree.heading(col, text=col)
            self.volume_pe_tree.column(col, width=100, anchor="center")

        # Pack the treeview and scrollbar for CE
        self.volume_ce_tree.pack(side="left", fill="both", expand=True)
        volume_ce_scroll.pack(side="right", fill="y")

        # Pack the treeview and scrollbar for PE
        self.volume_pe_tree.pack(side="left", fill="both", expand=True)
        volume_pe_scroll.pack(side="right", fill="y")

        # Status bar
        self.status_label = ctk.CTkLabel(main_container, text="Ready", font=("Arial", 10))
        self.status_label.pack(side="bottom", fill="x")

        # IV Track button
        self.iv_button = ctk.CTkButton(main_container, text="IV Track", command=self.open_iv_track_window)
        self.iv_button.pack(side="bottom", pady=10)

        # Status label
        self.status_label = ctk.CTkLabel(main_container, text="Ready", font=("Arial", 10))
        self.status_label.pack(side="bottom", fill="x")

        # IV Track button
        self.iv_button = ctk.CTkButton(main_container, text="IV Track", command=self.open_iv_track_window)
        self.iv_button.pack(side="bottom", pady=10)

    # [Rest of the methods remain the same as in the previous implementation]
    def setup_database(self):
        # Connect to SQLite database (or create it)
        self.conn = sqlite3.connect('E:/nifty_data.db')
        self.cursor = self.conn.cursor()
        
        # Create CE data table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS option_ce_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date_time TEXT,
                strike_price REAL,
                oi INTEGER,
                changein_oi INTEGER,
                volume INTEGER,
                ltp REAL,
                chng REAL,
                iv REAL
            )
        ''')
        
        # Create PE data table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS option_pe_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date_time TEXT,
                strike_price REAL,
                oi INTEGER,
                changein_oi INTEGER,
                volume INTEGER,
                ltp REAL,
                chng REAL,
                iv REAL
            )
        ''')
        
        # Create IV CE data table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS iv_ce_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date_time TEXT,
                strike_price REAL,
                iv REAL
            )
        ''')

        # Create IV PE data table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS iv_pe_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date_time TEXT,
                strike_price REAL,
                iv REAL
            )
        ''')

        self.conn.commit()

    def setup_async_loop(self):
        if platform.system() == 'Windows':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.root.after(0, self.start_async_tasks)

    def start_async_tasks(self):
        self.loop.create_task(self.update_data())
        self.root.after(100, self.check_tasks)

    def check_tasks(self):
        self.loop.stop()
        self.loop.run_forever()
        self.root.after(100, self.check_tasks)

    def insert_ce_data(self, date_time, strike_price, oi, changein_oi, volume, ltp, chng, iv):
        self.cursor.execute('''
            INSERT INTO option_ce_data (date_time, strike_price, oi, changein_oi, volume, ltp, chng, iv)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (date_time, strike_price, oi, changein_oi, volume, ltp, chng, iv))
        self.conn.commit()

    def insert_pe_data(self, date_time, strike_price, oi, changein_oi, volume, ltp, chng, iv):
        self.cursor.execute('''
            INSERT INTO option_pe_data (date_time, strike_price, oi, changein_oi, volume, ltp, chng, iv)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (date_time, strike_price, oi, changein_oi, volume, ltp, chng, iv))
        self.conn.commit()

    def insert_iv_ce_data(self, date_time, strike_price, iv):
        self.cursor.execute('''
            INSERT INTO iv_ce_data (date_time, strike_price, iv)
            VALUES (?, ?, ?)
        ''', (date_time, strike_price, iv))
        self.conn.commit()

    def insert_iv_pe_data(self, date_time, strike_price, iv):
        self.cursor.execute('''
            INSERT INTO iv_pe_data (date_time, strike_price, iv)
            VALUES (?, ?, ?)
        ''', (date_time, strike_price, iv))
        self.conn.commit()

    @staticmethod
    def calculate_atm_strike(current_price):
        return round(current_price / 50) * 50

    def get_relevant_strikes(self, atm_strike):
        strike_step = 50
        strikes = []
        for i in range(9):
            strikes.append(atm_strike - (i * strike_step))
        for i in range(1,10 ):
            strikes.append(atm_strike + (i * strike_step))
        return sorted(strikes)

    async def update_data(self):
        try:
            data = await self.nifty_client.get_data()
            self.process_and_display_data(data)
            self.status_label.configure(text="Data updated successfully")
            self.timestamp_label.configure(text=f"Last Updated: {datetime.now().strftime('%H:%M:%S')}")
        except Exception as e:
            self.status_label.configure(text=f"Error: {str(e)}")
            messagebox.showerror("Error", f"Failed to fetch data: {str(e)}")
        finally:
            self.root.after(300000, lambda: self.loop.create_task(self.update_data()))  # Fetch data every 5 minutes

    def process_and_display_data(self, data):
        try:
            data = json.loads(data)
            current_price = data["records"]["underlyingValue"]
            self.price_label.configure(text=f"{current_price:.2f}")

            atm_strike = self.calculate_atm_strike(current_price)
            self.atm_label.configure(text=f"{atm_strike:.2f}")

            relevant_strikes = self.get_relevant_strikes(atm_strike)

            # Clear existing items
            for tree in (self.ce_tree, self.pe_tree):
                for item in tree.get_children():
                    tree.delete(item)

            current_expiry = data["records"]["expiryDates"][0]

            strike_data = {}
            for item in data["records"]["data"]:
                if item["expiryDate"] == current_expiry and item["strikePrice"] in relevant_strikes:
                    strike_data[item["strikePrice"]] = item

            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            ce_data_list = []
            pe_data_list = []
            for strike in relevant_strikes:
                item = strike_data.get(strike, {})

                # Process CE data
                ce_data = item.get("CE", {})
                ce_tree_item = None
                if "CE" in item:
                    ce_change_value = ce_data.get("change", 0)
                    ce_iv = ce_data.get("impliedVolatility", 0)
                    ce_values = (
                        strike,
                        ce_data.get("openInterest", 0),
                        ce_data.get("changeinOpenInterest", 0),
                        ce_data.get("totalTradedVolume", 0),
                        ce_data.get("lastPrice", 0),
                        ce_change_value,
                        ce_iv
                    )
                    ce_tree_item = self.ce_tree.insert("", "end", values=ce_values)
                    
                    # Insert CE data into database
                    self.insert_ce_data(
                        current_time,
                        strike,
                        ce_data.get("openInterest", None),
                        ce_data.get("changeinOpenInterest", None),
                        ce_data.get("totalTradedVolume", None),
                        ce_data.get("lastPrice", None),
                        ce_change_value,
                        ce_iv
                    )

                    # Insert IV CE data into database
                    self.insert_iv_ce_data(current_time, strike, ce_iv)

                    ce_data_list.append((strike, ce_data.get("totalTradedVolume", 0), ce_data.get("openInterest", 0), ce_data.get("changeinOpenInterest", 0), ce_data.get("lastPrice", 0), ce_change_value))

                # Process PE data
                pe_data = item.get("PE", {})
                pe_tree_item = None
                if "PE" in item:
                    pe_change_value = pe_data.get("change", 0)
                    pe_iv = pe_data.get("impliedVolatility", 0)
                    pe_values = (
                        strike,
                        pe_data.get("openInterest", 0),
                        pe_data.get("changeinOpenInterest", 0),
                        pe_data.get("totalTradedVolume", 0),
                        pe_data.get("lastPrice", 0),
                        pe_change_value,
                        pe_iv
                    )
                    pe_tree_item = self.pe_tree.insert("", "end", values=pe_values)
          
          
          
                    # Insert PE data into database
                    self.insert_pe_data(
                        current_time,
                        strike,
                        pe_data.get("openInterest", None),
                        pe_data.get("changeinOpenInterest", None),
                        pe_data.get("totalTradedVolume", None),
                        pe_data.get("lastPrice", None),
                        pe_change_value,
                        pe_iv
                    )

                    # Insert IV PE data into database
                    self.insert_iv_pe_data(current_time, strike, pe_iv)

                    pe_data_list.append((strike, pe_data.get("totalTradedVolume", 0), pe_data.get("openInterest", 0), pe_data.get("changeinOpenInterest", 0), pe_data.get("lastPrice", 0), pe_change_value))

                # Apply styling tags
                for tree_item, tree in [(ce_tree_item, self.ce_tree), (pe_tree_item, self.pe_tree)]:
                    if tree_item is not None:
                        if strike == atm_strike:
                            tags = list(tree.item(tree_item)['tags'] or [])
                            tags.append('atm')
                            tree.item(tree_item, tags=tags)
                        elif strike > atm_strike:
                            tags = list(tree.item(tree_item)['tags'] or [])
                            tags.append('above_atm')
                            tree.item(tree_item, tags=tags)
                        else:
                            tags = list(tree.item(tree_item)['tags'] or [])
                            tags.append('below_atm')
                            tree.item(tree_item, tags=tags)

            # Fetch previous data from database
            prev_ce_data = self.fetch_previous_data('option_ce_data')
            prev_pe_data = self.fetch_previous_data('option_pe_data')

            # Display top 3 high volume CE strike prices in the new grid
            ce_data_list.sort(key=lambda x: x[1], reverse=True)
            top_ce_data = ce_data_list[:5]

            for item in self.volume_ce_tree.get_children():
                self.volume_ce_tree.delete(item)

            for strike, volume, oi, changein_oi, ltp, chng in top_ce_data:
                trend = self.calculate_trend(strike, volume, prev_ce_data)
                self.volume_ce_tree.insert("", "end", values=(strike, volume, oi, changein_oi, ltp, chng, trend))

            # Display top 3 high volume PE strike prices in the new grid
            pe_data_list.sort(key=lambda x: x[1], reverse=True)
            top_pe_data = pe_data_list[:5]

            for item in self.volume_pe_tree.get_children():
                self.volume_pe_tree.delete(item)

            for strike, volume, oi, changein_oi, ltp, chng in top_pe_data:
                trend = self.calculate_trend(strike, volume, prev_pe_data)
                self.volume_pe_tree.insert("", "end", values=(strike, volume, oi, changein_oi, ltp, chng, trend))

        except Exception as e:
            self.status_label.config(text=f"Error processing data: {str(e)}")
            raise

    def fetch_previous_data(self, table):
        five_minutes_ago = datetime.now() - timedelta(minutes=5)
        self.cursor.execute(f"""
            SELECT strike_price, volume
            FROM {table}
            WHERE date_time >= ?
        """, (five_minutes_ago,))
        rows = self.cursor.fetchall()
        return {row[0]: row[1] for row in rows}

    def calculate_trend(self, strike, current_volume, prev_data):
        prev_volume = prev_data.get(strike)
        if prev_volume is None:
            return "N/A"
        if current_volume > prev_volume:
            return "Increasing"
        elif current_volume < prev_volume:
            return "Decreasing"
        else:
            return "Stable"

    def determine_market_sentiment(self, ce_iv_data, pe_iv_data):
        """
        Determine market sentiment based on IV data for CE and PE.

        Args:
            ce_iv_data (list): List of tuples containing (date_time, strike_price, iv) for CE.
            pe_iv_data (list): List of tuples containing (date_time, strike_price, iv) for PE.

        Returns:
            str: 'Bullish', 'Bearish', or 'Consolidation' based on the analysis.
        """
        if not ce_iv_data or not pe_iv_data:
            return "No data available."

        ce_ivs = [row[2] for row in ce_iv_data]
        pe_ivs = [row[2] for row in pe_iv_data]

        avg_ce_iv = sum(ce_ivs) / len(ce_ivs)
        avg_pe_iv = sum(pe_ivs) / len(pe_ivs)

        if avg_pe_iv > avg_ce_iv:
            return "Bearish"
        elif avg_ce_iv > avg_pe_iv:
            return "Bullish"
        else:
            return "Consolidation"

    def open_iv_track_window(self):
        iv_window = tk.Toplevel(self.root)
        iv_window.title("IV Track for CE and PE")
        iv_window.geometry("1600x1900")

        # Create a figure and a canvas
        figure, ax = plt.subplots(2, 1, figsize=(8, 6))
        canvas = FigureCanvasTkAgg(figure, master=iv_window)
        canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Fetch IV data
        ce_iv_data = self.fetch_iv_data('iv_ce_data')
        pe_iv_data = self.fetch_iv_data('iv_pe_data')

        # Plot IV data
        self.plot_iv_data(ax[0], ce_iv_data, "IV CE Data")
        self.plot_iv_data(ax[1], pe_iv_data, " IV PE Data")
        
        self.plot_iv_data(ax[0], ce_iv_data, "IV CE Data", color='red')
        self.plot_iv_data(ax[1], pe_iv_data, "IV PE Data", color='green')

        # Create a text box for analysis report
        report_text = tk.Text(iv_window, height=10)
        report_text.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)
        
        
        # Generate analysis report
        report = self.generate_analysis_report(ce_iv_data, pe_iv_data)
        report_text.insert(tk.END, report)
        boolean_control = CustomBooleanControl(iv_window, width=60, height=60)
        boolean_control.place(relx=0.75, rely=0.5, anchor='center')
        sentiment = self.determine_market_sentiment(ce_iv_data, pe_iv_data)
        ce_iv = ce_iv_data[-1][2] if ce_iv_data else 0
        pe_iv = pe_iv_data[-1][2] if pe_iv_data else 0
        boolean_state = ce_iv > pe_iv
        boolean_control.set_state(boolean_state)
        
        
        
        report_text.insert(tk.END, f"\nMarket Sentiment: {sentiment}")

    def fetch_iv_data(self, table):
        self.cursor.execute(f"SELECT date_time, strike_price, iv FROM {table} ORDER BY date_time")
        rows = self.cursor.fetchall()
        return rows

    def plot_iv_data(self, ax, data, title,color='blue'):
        dates = [datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S') for row in data]
        ivs = [row[2] for row in data]
        ax.plot(dates, ivs, marker='o' , color=color)
        ax.set_title(title)
        ax.set_xlabel("Date Time")
        ax.set_ylabel("IV")
        ax.grid(True)

    def generate_analysis_report(self, ce_iv_data, pe_iv_data):
        report = "IV Analysis Report:\n\n"
        report += "CE IV Data:\n"
        report += self.analyze_iv_data(ce_iv_data)
        report += "\nPE IV Data:\n"
        report += self.analyze_iv_data(pe_iv_data)
        return report

    def analyze_iv_data(self, data):
        if not data:
            return "No data available.\n"

        ivs = [row[2] for row in data]
        avg_iv = sum(ivs) / len(ivs)
        trend = "Increasing" if ivs[-1] > ivs[0] else "Decreasing" if ivs[-1] < ivs[0] else "Stable"
        if trend == "Increasing":
           sentiment = "Bearish"
        elif trend == "Decreasing":
           sentiment = "Bullish"
        else:
           sentiment = "Consolidate"
        analysis = f"Average IV: {avg_iv:.2f}\n"
        analysis += f"Trend: {trend}\n"
        analysis += f"Market Sentiment: {sentiment}\n"
        return analysis
    
    

    def on_closing(self):
        self.loop.create_task(self.cleanup())
        self.root.after(100, self.root.destroy)

    async def cleanup(self):
        await self.nifty_client.close()
        self.conn.close()  # Close the database connection
        for task in asyncio.all_tasks(self.loop):
            task.cancel()
        await asyncio.gather(*asyncio.all_tasks(self.loop), return_exceptions=True)
        self.loop.stop()
        
        
def main():
    root = ctk.CTk()
    app = NiftyApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()