import tkinter as tk
from tkinter import ttk, messagebox
import aiohttp
import asyncio
import json
import sqlite3
from datetime import datetime
import platform

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
        self.root = root
        self.root.title("Nifty Option Chain Viewer")
        self.root.geometry("1600x600")
        self.nifty_client = NiftyOptionChain()
        self.setup_ui()
        self.setup_database()  # Initialize the database
        self.setup_async_loop()

    def setup_database(self):
        # Connect to SQLite database (or create it)
        self.conn = sqlite3.connect('E:/nifty_data.db')
        self.cursor = self.conn.cursor()
        # Create a table if it doesn't exist
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS option_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date_time TEXT,
                strike_price REAL,
                oi_ce INTEGER,
                changein_oi_ce INTEGER,
                volume_ce INTEGER,
                ltp_ce REAL,
                chng_ce REAL,
                oi_pe INTEGER,
                changein_oi_pe INTEGER,
                volume_pe INTEGER,
                ltp_pe REAL,
                chng_pe REAL
            )
        ''')
        self.conn.commit()

    def setup_ui(self):
        # Main container
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True , padx=10, pady=10)

        # Header frame
        header_frame = ttk.Frame(main_container)
        header_frame.pack(fill=tk.X, pady=(0, 10))

        # Price displays
        price_frame = ttk.Frame(header_frame)
        price_frame.pack(side=tk.LEFT)

        ttk.Label(price_frame, text="Current Market Price:", font=("Arial", 12)).pack(side=tk.LEFT)
        self.price_label = ttk.Label(price_frame, text="--", font=("Arial", 12, 'bold'))
        self.price_label.pack(side=tk.LEFT, padx=(5, 20))

        ttk.Label(price_frame, text="ATM Strike:", font=("Arial", 12)).pack(side=tk.LEFT)
        self.atm_label = ttk.Label(price_frame, text="--", font=("Arial", 12, 'bold'))
        self.atm_label.pack(side=tk.LEFT, padx=5)

        # Last updated timestamp
        self.timestamp_label = ttk.Label(header_frame, text="Last Updated: --", font=("Arial", 10))
        self.timestamp_label.pack(side=tk.RIGHT)

        # Option chain display frame
        chain_frame = ttk.Frame(main_container)
        chain_frame.pack(fill=tk.BOTH, expand=True)

        # CE Frame (Left Side)
        ce_frame = ttk.LabelFrame(chain_frame, text="Call Options (CE)", padding=5)
        ce_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        # PE Frame (Right Side)
        pe_frame = ttk.LabelFrame(chain_frame, text="Put Options (PE)", padding=5)
        pe_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))

        # Create treeviews with updated columns
        columns = ("Strike", "OI", "Chng in OI", "Volume", "LTP", "Chng")
        
        # CE Treeview
        self.ce_tree = CustomTreeview(ce_frame, columns=columns, show="headings")
        ce_scroll = ttk.Scrollbar(ce_frame, orient=tk.VERTICAL, command=self.ce_tree.yview)
        self.ce_tree.configure(yscrollcommand=ce_scroll.set)
        
        # PE Treeview
        self.pe_tree = CustomTreeview(pe_frame, columns=columns, show="headings")
        pe_scroll = ttk.Scrollbar(pe_frame, orient=tk.VERTICAL, command=self.pe_tree.yview)
        self.pe_tree.configure(yscrollcommand=pe_scroll.set)

        # Configure columns for both treeviews
        for tree in (self.ce_tree, self.pe_tree):
            for col in columns:
                tree.heading(col, text=col)
                tree.column(col, width=100, anchor="center")

        # Pack treeviews and scrollbars
        self.ce_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ce_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.pe_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        pe_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Status bar
        self.status_label = ttk.Label(main_container, text="Ready", font=("Arial", 10))
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)

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
            self.root.after(60000, lambda: self.loop.create_task(self.update_data()))

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

            for strike in relevant_strikes:
                item = strike_data.get(strike, {})

                # Prepare CE data
                ce_data = item.get("CE", {})
                ce_change_value = ce_data.get("change", 0) if "CE" in item else 0
                ce_values = (
                    strike,
                    ce_data.get("openInterest", 0) if "CE" in item else "-",
                    ce_data.get("changeinOpenInterest", 0) if "CE" in item else "-",
                    ce_data.get("totalTradedVolume", 0) if "CE" in item else "-",
                    ce_data.get("lastPrice", 0) if "CE" in item else "-",
                    ce_change_value if "CE" in item else "-"
                )

                # Prepare PE data
                pe_data = item.get("PE", {})
                pe_change_value = pe_data.get("change", 0) if "PE" in item else 0
                pe_values = (
                    strike,
                    pe_data.get("openInterest", 0) if "PE" in item else "-",
                    pe_data.get("changeinOpenInterest", 0) if "PE" in item else "-",
                    pe_data.get("totalTradedVolume", 0) if "PE" in item else "-",
                    pe_data.get("lastPrice", 0) if "PE" in item else "-",
                    pe_change_value if "PE" in item else "-"
                )

                # Insert into trees
                ce_tree_item = self.ce_tree.insert("", "end", values=ce_values)
                pe_tree_item = self.pe_tree.insert("", "end", values=pe_values)

                # Apply tags for both trees
                for tree_item, tree in [(ce_tree_item, self.ce_tree), (pe_tree_item, self.pe_tree)]:
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

                # Insert into database - single row for both CE and PE data
                self.insert_data_to_db(
                    current_time, 
                    strike,
                    ce_data.get("openInterest", None) if "CE" in item else None,
                    ce_data.get("changeinOpenInterest", None) if "CE" in item else None,
                    ce_data.get("totalTradedVolume", None) if "CE" in item else None,
                    ce_data.get("lastPrice", None) if "CE" in item else None,
                    ce_change_value if "CE" in item else None,
                    pe_data.get("openInterest", None) if "PE" in item else None,
                    pe_data.get("changeinOpenInterest", None) if "PE" in item else None,
                    pe_data.get("totalTradedVolume", None) if "PE" in item else None,
                    pe_data.get("lastPrice", None) if "PE" in item else None,
                    pe_change_value if "PE" in item else None
                )

        except Exception as e:
            self.status_label.config(text=f"Error processing data: {str(e)}")
            raise

    @staticmethod
    def calculate_atm_strike(current_price):
        return round(current_price / 50) * 50

    def insert_data_to_db(self, date_time, strike_price, oi_ce, changein_oi_ce, volume_ce, ltp_ce, chng_ce, oi_pe, changein_oi_pe, volume_pe, ltp_pe, chng_pe):
        self.cursor.execute('''
            INSERT INTO option_data (date_time, strike_price, oi_ce, changein_oi_ce, volume_ce, ltp_ce, chng_ce, oi_pe, changein_oi_pe, volume_pe, ltp_pe, chng_pe)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (date_time, strike_price, oi_ce, changein_oi_ce, volume_ce, ltp_ce, chng_ce, oi_pe, changein_oi_pe, volume_pe, ltp_pe, chng_pe))
        self.conn.commit()

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
    root = tk.Tk()
    app = NiftyApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()
