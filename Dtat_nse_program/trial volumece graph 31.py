import tkinter as tk
from tkinter import ttk, messagebox
import aiohttp
import asyncio
import json
import sqlite3
from datetime import datetime, timedelta
import platform
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


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
        self.url_nf = 'https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY'
        self.headers = {
            'User -Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36',
            'Accept-Language': 'en,gu;q=0.9,hi;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://www.nseindia.com/'
        }
        self.cookies = {}
        self.session = None

    async def initialize_session(self):
        self.session = aiohttp.ClientSession()
        try:
            async with self.session.get(self.url_nf, headers=self.headers, timeout=5) as response:
                if response.status == 200:
                    self.cookies = {k: v.value for k, v in response.cookies.items()}
                else:
                    print(f"Failed to initialize session, status: {response.status}")
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
                print(f"Response status: {response.status}")  # Log the response status
                if response.status == 200:
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
        self.root = root
        self.root.title("Nifty Option Chain Viewer")
        self.root.geometry("1900x1600")
        self.nifty_client = NiftyOptionChain()
        self.setup_database()  # Initialize the database first
        self.setup_ui()        # Then set up the UI
        self.setup_async_loop()

    def setup_ui(self):
        # Main container
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Header frame
        header_frame = ttk.Frame(main_container)
        header_frame.pack(fill=tk.X, pady=(0, 10))

        # Price displays
        price_frame = ttk.Frame(header_frame)
        price_frame.pack(side=tk.LEFT)

        ttk.Label(price_frame, text="Current Market Price:", font=("Arial", 12)).pack(side=tk.LEFT)
        self.price_label = ttk.Label(price_frame, text="--", font=("Arial", 12, 'bold'))
        self.price_label.pack(side=tk.LEFT, padx=(5, 20))

        ttk.Label(price_frame, text="ATM Strike Price:", font=("Arial", 12)).pack(side=tk.LEFT)
        self.atm_label = ttk.Label(price_frame, text="--", font=("Arial", 12, 'bold'))
        self.atm_label.pack(side=tk.LEFT, padx=5)

        # Last updated timestamp
        self.timestamp_label = ttk.Label(header_frame, text="Last Updated: --", font=("Arial", 10))
        self.timestamp_label.pack(side=tk.RIGHT)

        # Option chain display frame
        chain_frame = ttk.Frame(main_container)
        chain_frame.pack(fill=tk.BOTH, expand=True)

        # CE Frame (Left Side)
        ce_frame = ttk.LabelFrame(chain_frame, text="Call Options (CE)", padding=0, width=30, height=20)
        ce_frame.pack(side=tk.LEFT, fill=tk.NONE, expand=False, padx=(0, 0))
        ce_frame.place(x=1250, y=0)

        # PE Frame (Right Side)
        pe_frame = ttk.LabelFrame(chain_frame, text="Put Options (PE)", padding=0, width=30, height=20)
        pe_frame.pack(side=tk.LEFT, fill=tk.NONE, expand=False, padx=(0, 0))
        pe_frame.place(x=1250, y=435)

        # Create treeviews with updated columns
        columns = ("Strike", "OI", "Chng in OI", "Volume", "LTP", "Chng", "IV")

        # CE Treeview
        self.ce_tree = CustomTreeview(ce_frame, columns=columns, show="headings", height=19)
        ce_scroll = ttk.Scrollbar(ce_frame, orient=tk.VERTICAL, command=self.ce_tree.yview)
        self.ce_tree.configure(yscrollcommand=ce_scroll.set)
        ce_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.ce_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # PE Treeview
        self.pe_tree = CustomTreeview(pe_frame, columns=columns, show="headings", height=19)
        pe_scroll = ttk.Scrollbar(pe_frame, orient=tk.VERTICAL, command=self.pe_tree.yview)
        self.pe_tree.configure(yscrollcommand=pe_scroll.set)
        pe_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.pe_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Volume CE Frame (Bottom Left)
        volume_ce_frame = ttk.LabelFrame(main_container, text="Top 3 High Volume CE", padding=5)
        volume_ce_frame.pack(side=tk.LEFT, fill=tk.X, expand=False, pady=(10, 0))
        volume_ce_frame.place(x=1210, y=750)

        # Volume PE Frame (Bottom Right)
        volume_pe_frame = ttk.LabelFrame(main_container, text="Top 3 High Volume PE", padding=5)
        volume_pe_frame.pack(side=tk.RIGHT, fill=tk.X, expand=False, pady=(10, 0))
        volume_pe_frame.place(x=1000, y=850)

        # Treeview for Volume CE Track
        volume_ce_columns = ("Strike", "Volume", "OI", "Chng in OI", "LTP", "Chng", "Trend")
        self.volume_ce_tree = ttk.Treeview(volume_ce_frame, columns=volume_ce_columns, show="headings", height=5)
        volume_ce_scroll = ttk.Scrollbar(volume_ce_frame, orient=tk.VERTICAL, command=self.volume_ce_tree.yview)
        self.volume_ce_tree.configure(yscrollcommand=volume_ce_scroll.set)

        # Treeview for Volume PE Track
        volume_pe_columns = ("Strike", "Volume", "OI", "Chng in OI", "LTP", "Chng", "Trend")
        self.volume_pe_tree = ttk.Treeview(volume_pe_frame, columns=volume_pe_columns, show="headings", height=5)
        volume_pe_scroll = ttk.Scrollbar(volume_pe_frame, orient=tk.VERTICAL, command=self.volume_pe_tree.yview)
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
        self.volume_ce_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        volume_ce_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Pack the treeview and scrollbar for PE
        self.volume_pe_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        volume_pe_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Configure columns for both treeviews
        for tree in (self.ce_tree, self.pe_tree):
            for col in columns:
                tree.heading(col, text=col)
                tree.column(col, width=80, anchor="center")

        # Status bar
        self.status_label = ttk.Label(main_container, text="Ready", font=("Arial", 10))
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)

        # Frame for plots
        self.plot_frame = ttk.Frame(main_container)
        self.plot_frame.place(x=50, y=100, width=600, height=600)

        # Create a canvas for the plots
        self.canvas = FigureCanvasTkAgg(plt.figure(), master=self.plot_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

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
        for i in range(1, 10):
            strikes.append(atm_strike + (i * strike_step))
        return sorted(strikes)

    async def update_data(self):
        try:
            data = await self.nifty_client.get_data()
            print("Data fetched successfully.")  # Log success
            self.process_and_display_data(data)
            self.status_label.config(text="Data updated successfully")
            self.timestamp_label.config(text=f"Last Updated: {datetime.now().strftime('%H:%M:%S')}")
        except Exception as e:
            print(f"Error in update_data: {str(e)}")  # Log the error
            self.status_label.config(text=f"Error: {str(e)}")
            messagebox.showerror("Error", f"Failed to fetch data: {str(e)}")
        finally:
            self.root.after(300000, lambda: self.loop.create_task(self.update_data()))  # Fetch data every 5 minutes

    def process_and_display_data(self, data):
        try:
            data = json.loads(data)
            current_price = data["records"]["underlyingValue"]
            self.price_label.config(text=f"{current_price:.2f}")

            atm_strike = self.calculate_atm_strike(current_price)
            self.atm_label.config(text=f"{atm_strike:.2f}")

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
                if ce_data:
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
                    self.ce_tree.insert("", "end", values=ce_values)

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

                    ce_data_list.append((strike, ce_data.get("totalTradedVolume", 0), ce_data.get("openInterest", 0), ce_data.get("changeinOpenInterest", 0), ce_data.get("lastPrice", 0), ce_change_value))

                # Process PE data
                pe_data = item.get("PE", {})
                if pe_data:
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
                    self.pe_tree.insert("", "end", values=pe_values)

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

                    pe_data_list.append((strike, pe_data.get("totalTradedVolume", 0), pe_data.get("openInterest", 0), pe_data.get("changeinOpenInterest", 0), pe_data.get("lastPrice", 0), pe_change_value))

            # Fetch previous data from database
            prev_ce_data = self.fetch_previous_data('option_ce_data')
            prev_pe_data = self.fetch_previous_data('option_pe_data')

            # Display top 3 high volume CE strike prices in the new grid
            ce_data_list.sort(key=lambda x: x[1], reverse=True)
            top_ce_data = ce_data_list[:3]

            for item in self.volume_ce_tree.get_children():
                self.volume_ce_tree.delete(item)

            for strike, volume, oi, changein_oi, ltp, chng in top_ce_data:
                trend = self.calculate_trend(strike, volume, prev_ce_data)
                self.volume_ce_tree.insert("", "end", values=(strike, volume, oi, changein_oi, ltp, chng, trend))

            # Display top 3 high volume PE strike prices in the new grid
            pe_data_list.sort(key=lambda x: x[1], reverse=True)
            top_pe_data = pe_data_list[:3]

            for item in self.volume_pe_tree.get_children():
                self.volume_pe_tree.delete(item)

            for strike, volume, oi, changein_oi, ltp, chng in top_pe_data:
                trend = self.calculate_trend(strike, volume, prev_pe_data)
                self.volume_pe_tree.insert("", "end", values=(strike, volume, oi, changein_oi, ltp, chng, trend))

        except Exception as e:
            print(f"Error processing data: {str(e)}")  # Log the error
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

    def on_closing(self):
        """
        Handles the window close event.
        """
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            # Close the database connection
            if hasattr(self, 'conn'):
                self.conn.close()
                print("Database connection closed.")

            # Stop any running tasks
            asyncio.run(self.cleanup())

            # Destroy the root window
            self.root.destroy()

    async def cleanup(self):
        await self.nifty_client.close()
        for task in asyncio.all_tasks(self.loop):
            task.cancel()
        await asyncio.gather(*asyncio.all_tasks(self.loop), return_exceptions=True)
        self.loop.stop()


def main():
    root = tk.Tk()
    app = NiftyApp(root)

    root.protocol("WM_DELETE_WINDOW", app.on_closing)

    root.mainloop()


if __name__ == "__main__":
    main()