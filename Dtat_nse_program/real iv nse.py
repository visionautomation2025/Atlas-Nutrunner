import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
import aiohttp
import asyncio
import json
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats
from scipy.optimize import brentq
from datetime import datetime
import platform

class Database:
    def __init__(self, db_name="E:/nifty_data.db"):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.create_table()

    def create_table(self):
        """Create tables if not exists"""
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS option_data (
            strike REAL,
            oi INTEGER,
            chng_oi INTEGER,
            volume INTEGER,
            ltp REAL,
            chng REAL,
            option_type TEXT,
            timestamp DATETIME
        )
        """)
        # Create table for implied volatility
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS iv_data (
            strike REAL,
            option_type TEXT,
            implied_volatility REAL,
            timestamp DATETIME
        )
        """)
        self.conn.commit()

    def insert_data(self, strike, oi, chng_oi, volume, ltp, chng, option_type):
        """Insert data into the option_data table"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.cursor.execute("""
        INSERT INTO option_data (strike, oi, chng_oi, volume, ltp, chng, option_type, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (strike, oi, chng_oi, volume, ltp, chng, option_type, timestamp))
        self.conn.commit()

    def insert_iv_data(self, strike, option_type, implied_volatility):
        """Insert implied volatility data into iv_data table"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.cursor.execute("""
        INSERT INTO iv_data (strike, option_type, implied_volatility, timestamp)
        VALUES (?, ?, ?, ?)
        """, (strike, option_type, implied_volatility, timestamp))
        self.conn.commit()

    def close(self):
        self.conn.close()

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
        if len(values) >= 6:
            try:
                change_value = float(values[5])
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
        self.root = root
        self.root.title("Nifty Option Chain Viewer")
        self.root.geometry("1600x600")
        self.nifty_client = NiftyOptionChain()
        self.db = Database()
        self.setup_ui()
        self.setup_async_loop()
        self.data_to_save = [] 

    def setup_ui(self):
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        header_frame = ttk.Frame(main_container)
        header_frame.pack(fill=tk.X, pady=(0, 10))

        price_frame = ttk.Frame(header_frame)
        price_frame.pack(side=tk.LEFT)

        ttk.Label(price_frame, text="Current Market Price:", font=("Arial", 12)).pack(side=tk.LEFT)
        self.price_label = ttk.Label(price_frame, text="--", font=("Arial", 12, 'bold'))
        self.price_label.pack(side=tk.LEFT, padx=(5, 20))

        ttk.Label(price_frame, text="ATM Strike:", font=("Arial", 12)).pack(side=tk.LEFT)
        self.atm_label = ttk.Label(price_frame, text="--", font=("Arial", 12, 'bold'))
        self.atm_label.pack(side=tk.LEFT, padx=5)

        self.timestamp_label = ttk.Label(header_frame, text="Last Updated: --", font=("Arial", 10))
        self.timestamp_label.pack(side=tk.RIGHT)

        chain_frame = ttk.Frame(main_container)
        chain_frame.pack(fill=tk.BOTH, expand=True)

        ce_frame = ttk.LabelFrame(chain_frame, text="Call Options (CE)", padding=5)
        ce_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        pe_frame = ttk.LabelFrame(chain_frame, text="Put Options (PE)", padding=5)
        pe_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))

        columns = ("Strike", "OI", "Chng in OI", "Volume", "LTP", "Chng", "CE IV")  # Added "CE IV"
        self.ce_tree = CustomTreeview(ce_frame, columns=columns, show="headings")
        
        columns_pe = ("Strike", "OI", "Chng in OI", "Volume", "LTP", "Chng", "PE IV")  # Added "PE IV"
        self.pe_tree = CustomTreeview(pe_frame, columns=columns_pe, show="headings")

        ce_scroll = ttk.Scrollbar(ce_frame, orient=tk.VERTICAL, command=self.ce_tree.yview)
        self.ce_tree.configure(yscrollcommand=ce_scroll.set)
        pe_scroll = ttk.Scrollbar(pe_frame, orient=tk.VERTICAL, command=self.pe_tree.yview)
        self.pe_tree.configure(yscrollcommand=pe_scroll.set)

        for tree in (self.ce_tree, self.pe_tree):
            for col in (columns if tree == self.ce_tree else columns_pe):
                tree.heading(col, text=col)
                tree.column(col, width=100, anchor="center")

        self.ce_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ce_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.pe_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        pe_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.status_label = ttk.Label(main_container, text="Ready", font=("Arial", 10))
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)

        # Add IV Check button
        self.iv_check_btn = ttk.Button(header_frame, text="IV Check", command=self.show_iv_analysis)
        self.iv_check_btn.pack(side=tk.LEFT, padx=(10, 0))

        # Add a button for getting volume ranking
        self.volume_btn = ttk.Button(header_frame, text="Get Volume Ranking", command=self.show_volume_ranking)
        self.volume_btn.pack(side=tk.LEFT, padx=(10, 0))

    def setup_async_loop(self):
        if platform.system() == 'Windows':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.root.after(0, self.start_async_tasks)

    def start_async_tasks(self):
        self.loop.create_task(self.update_data())
        self.root.after(100, self.check_tasks)
        self.root.after(300000, self.save_data_to_db)

    def check_tasks(self):
        self.loop.stop()
        self.loop.run_forever()
        self.root.after(100, self.check_tasks)

    async def update_data(self):
        try:
            data = await self.nifty_client.get_data()
            self.process_and_display_data(data)
            self.status_label.config(text="Data updated successfully")
            self.timestamp_label.config(text=f"Last Updated: {datetime.now().strftime('%H:%M:%S')}")
        except Exception as e:
            self.status_label.config(text=f"Error: {str(e)}")
            messagebox.showerror("Error", f"Failed to fetch data: {str(e)}")
        finally:
            self.root.after(300000, lambda: self.loop.create_task(self.update_data()))

    def save_data_to_db(self):
        if self.data_to_save:
            for strike, oi, chng_oi, volume, ltp, chng, option_type, ce_iv, pe_iv in self.data_to_save:
                self.db.insert_data(strike, oi, chng_oi, volume, ltp, chng, option_type)
                # Consider saving IV data as well
                if ce_iv is not None:
                    self.db.insert_iv_data(strike, "CE", ce_iv)
                if pe_iv is not None:
                    self.db.insert_iv_data(strike, "PE", pe_iv)
            self.data_to_save.clear()
            self.status_label.config(text="Data saved to database successfully")
        self.root.after(300000, self.save_data_to_db)

    def get_relevant_strikes(self, atm_strike):
        strike_step = 50
        strikes = []
        for i in range(4):
            strikes.append(atm_strike - (i * strike_step))
        for i in range(1, 5):
            strikes.append(atm_strike + (i * strike_step))
        return sorted(strikes)

    def process_and_display_data(self, data):
        try:
            data = json.loads(data)
            current_price = data["records"]["underlyingValue"]
            self.price_label.config(text=f"{current_price:.2f}")

            atm_strike = self.calculate_atm_strike(current_price)
            self.atm_label.config(text=f"{atm_strike:.2f}")

            relevant_strikes = self.get_relevant_strikes(atm_strike)

            for tree in (self.ce_tree, self.pe_tree):
                for item in tree.get_children():
                    tree.delete(item)

            current_expiry = data["records"]["expiryDates"][0]
            
            strike_data = {}
            ce_iv_data = {}
            pe_iv_data = {}
            for item in data["records"]["data"]:
                if item["expiryDate"] == current_expiry and item["strikePrice"] in relevant_strikes:
                    strike_data[item["strikePrice"]] = item
                    # Assuming IV data is included in the response
                    if "CE" in item:
                        ce_iv_data[item["strikePrice"]] = item["CE"].get("impliedVolatility", 0)
                    if "PE" in item:
                        pe_iv_data[item["strikePrice"]] = item["PE"].get("impliedVolatility", 0)

            for strike in relevant_strikes:
                item = strike_data.get(strike, {})

                ce_iv = ce_iv_data.get(strike, None)
                if "CE" in item:
                    ce_data = item["CE"]
                    change_value = ce_data.get("change", 0)
                    values = (
                        strike,
                        ce_data.get("openInterest", 0),
                        ce_data.get("changeinOpenInterest", 0),
                        ce_data.get("totalTradedVolume", 0),
                        ce_data.get("lastPrice", 0),
                        change_value,
                        ce_iv   # Include CE IV
                    )
                    tree_item = self.ce_tree.insert("", "end", values=values)

                    self.data_to_save.append((strike, ce_data.get("openInterest", 0), 
                                               ce_data.get("changeinOpenInterest", 0),
                                               ce_data.get("totalTradedVolume", 0),
                                               ce_data.get("lastPrice", 0),
                                               change_value, "CE", ce_iv, None))  # Saving CE IV
                    
                    if strike == atm_strike:
                        tags = list(self.ce_tree.item(tree_item)['tags'] or [])
                        tags.append('atm')
                        self.ce_tree.item(tree_item, tags=tags)
                    elif strike > atm_strike:
                        tags = list(self.ce_tree.item(tree_item)['tags'] or [])
                        tags.append('above_atm')
                        self.ce_tree.item(tree_item, tags=tags)
                    else:
                        tags = list(self.ce_tree.item(tree_item)['tags'] or [])
                        tags.append('below_atm')
                        self.ce_tree.item(tree_item, tags=tags)
                else:
                    self.ce_tree.insert("", "end", values=(strike, "-", "-", "-", "-", "-", ce_iv))

                pe_iv = pe_iv_data.get(strike, None)
                if "PE" in item:
                    pe_data = item["PE"]
                    change_value = pe_data.get("change", 0)
                    values = (
                        strike,
                        pe_data.get("openInterest", 0),
                        pe_data.get("changeinOpenInterest", 0),
                        pe_data.get("totalTradedVolume", 0),
                        pe_data.get("lastPrice", 0),
                        change_value,
                        pe_iv   # Include PE IV
                    )
                    tree_item = self.pe_tree.insert("", "end", values=values)

                    self.data_to_save.append((strike, pe_data.get("openInterest", 0), 
                                               pe_data.get("changeinOpenInterest", 0),
                                               pe_data.get("totalTradedVolume", 0),
                                               pe_data.get("lastPrice", 0),
                                               change_value, "PE", None, pe_iv))  # Saving PE IV
                    
                    if strike == atm_strike:
                        tags = list(self.pe_tree.item(tree_item)['tags'] or [])
                        tags.append('atm')
                        self.pe_tree.item(tree_item, tags=tags)
                    elif strike > atm_strike:
                        tags = list(self.pe_tree.item(tree_item)['tags'] or [])
                        tags.append('above_atm')
                        self.pe_tree.item(tree_item, tags=tags)
                    else:
                        tags = list(self.pe_tree.item(tree_item)['tags'] or [])
                        tags.append('below_atm')
                        self.pe_tree.item(tree_item, tags=tags)
                else:
                    self.pe_tree.insert("", "end", values=(strike, "-", "-", "-", "-", "-", pe_iv))

        except Exception as e:
            self.status_label.config(text=f"Error processing data: {str(e)}")
            raise

    @staticmethod
    def calculate_atm_strike(current_price):
        return round(current_price / 50) * 50

    def on_closing(self):
        self.db.close()
        self.loop.create_task(self.cleanup())
        self.root.after(100, self.root.destroy)

    async def cleanup(self):
        await self.nifty_client.close()
        for task in asyncio.all_tasks(self.loop):
            task.cancel()
        await asyncio.gather(*asyncio.all_tasks(self.loop), return_exceptions=True)
        self.loop.stop()

    def show_iv_analysis(self):
        """Open a new window to display IV analysis."""
        iv_window = tk.Toplevel(self.root)
        iv_window.title("IV Analysis")

        self.iv_status_label = ttk.Label(iv_window, text="Calculating IV data...", font=("Arial", 10))
        self.iv_status_label.pack(padx=10, pady=10)

        # Assuming you have defined the necessary parameters for IV calculation
        S = float(self.price_label.cget("text"))  # Current market price
        r = 0.05  # Example risk-free rate
        T = 30/365  # Example time until expiration in years

        ce_iv_data = {}
        pe_iv_data = {}

        # Fetching the IV data
        for tree in (self.ce_tree, self.pe_tree):
            for item in tree.get_children():
                values = tree.item(item)["values"]
                strike_price = values[0]
                if tree == self.ce_tree:
                    market_price = values[6]
                    ce_iv = implied_volatility(S, strike_price, T, r, market_price, option_type='call')
                    ce_iv_data[strike_price] = ce_iv
                else:
                    market_price = values[6]
                    pe_iv = implied_volatility(S, strike_price, T, r, market_price, option_type='put')
                    pe_iv_data[strike_price] = pe_iv

        self.plot_iv(ce_iv_data, pe_iv_data)
        self.iv_status_label.config(text="IV data calculated successfully.")

    def plot_iv(self, ce_iv_data, pe_iv_data):
        """Plot the IV for CE and PE."""
        strikes = sorted(ce_iv_data.keys())
        ce_iv_values = [ce_iv_data[strike] for strike in strikes]
        pe_iv_values = [pe_iv_data[strike] for strike in strikes if strike in pe_iv_data]

        plt.figure(figsize=(10, 5))
        plt.plot(strikes, ce_iv_values, marker='o', label='CE IV', color='blue')
        plt.plot(strikes, pe_iv_values, marker='o', label='PE IV', color='orange')
        plt.title('Implied Volatility for CE and PE Options')
        plt.xlabel('Strike Price')
        plt.ylabel('Implied Volatility (%)')
        plt.axhline(y=0, color='k', linestyle='--')  # Add a horizontal line at y = 0
        plt.legend()
        plt.grid()
        plt.show()

    @staticmethod
    def implied_volatility(S, K, T, r, market_price, option_type='call'):
        """Calculate implied volatility using the Black-Scholes model."""
        objective_function = lambda sigma: black_scholes(S, K, T, r, sigma, option_type) - market_price
        try:
            iv = brentq(objective_function, 0.01, 1) # Adjust bounds if necessary
            return iv
        except ValueError:
            return None

def black_scholes(S, K, T, r, sigma, option_type='call'):
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)

    if option_type == 'call':
        return (S * stats.norm.cdf(d1) - K * np.exp(-r * T) * stats.norm.cdf(d2))
    else:
        return (K * np.exp(-r * T) * stats.norm.cdf(-d2) - S * stats.norm.cdf(-d1))

def main():
    root = tk.Tk()
    app = NiftyApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()