import tkinter as tk
import numpy as np
from tkinter import ttk, messagebox
import aiohttp
import asyncio
import json
import sqlite3
from datetime import datetime, timedelta
import platform
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

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
        self.root = root
        self.root.title("Nifty Option Chain Viewer")
        self.root.geometry("1600x600")
        self.nifty_client = NiftyOptionChain()
        self.setup_database()
        self.setup_tabs()
        self.setup_ui()
        self.setup_async_loop()

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

    def setup_tabs(self):
    # Create notebook (tab container)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Create main tab for existing content
        self.main_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.main_tab, text="Option Chain")
        
        # Create volume analysis tab
        self.volume_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.volume_tab, text="Volume Analysis")
        
        # Bind tab change event to handle full-screen for Volume Analysis tab
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)
        
        # Setup volume analysis tab content
        self.setup_volume_tab()

def setup_volume_tab(self):
    # Create a frame for combo boxes with some padding
    combo_frame = ttk.Frame(self.volume_tab)
    combo_frame.pack(fill=tk.X, padx=10, pady=10)
    
    # CE Combo Box section
    ce_frame = ttk.LabelFrame(combo_frame, text="High Volume CE Strikes", padding="10 10 10 10")
    ce_frame.pack(side=tk.LEFT, padx=10, fill=tk.BOTH, expand=True)
    
    self.ce_combo = ttk.Combobox(ce_frame, width=15, state="readonly")
    self.ce_combo.pack(pady=5, fill=tk.X)
    self.ce_combo.bind("<<ComboboxSelected>>", self.generate_ce_graph)  # Bind event

    # PE Combo Box section
    pe_frame = ttk.LabelFrame(combo_frame, text="High Volume PE Strikes", padding="10 10 10 10")
    pe_frame.pack(side=tk.LEFT, padx=10, fill=tk.BOTH, expand=True)
    
    self.pe_combo = ttk.Combobox(pe_frame, width=15, state="readonly")
    self.pe_combo.pack(pady=5, fill=tk.X)
    self.pe_combo.bind("<<ComboboxSelected>>", self.generate_pe_graph)  # Bind event

    # Add a placeholder for the graph (you can replace this with your actual graph)
    self.graph_frame = ttk.Frame(self.volume_tab)
    self.graph_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    # Add a label to indicate where the graph will be displayed
    ttk.Label(self.graph_frame, text="Graph will be displayed here", font=("Arial", 14)).pack(expand=True)

def on_tab_changed(self, event):
    """Handle tab change event to make the Volume Analysis tab full screen."""
    selected_tab = self.notebook.tab(self.notebook.select(), "text")
    
    if selected_tab == "Volume Analysis":
        # Hide the main tab and expand the volume tab
        self.main_tab.pack_forget()
        self.volume_tab.pack(fill=tk.BOTH, expand=True)
    else:
        # Hide the volume tab and show the main tab
        self.volume_tab.pack_forget()
        self.main_tab.pack(fill=tk.BOTH, expand=True)

    def generate_ce_graph(self, event):
        selected_ce_strike = self.ce_combo.get()
        self.plot_graph('option_ce_data', selected_ce_strike, "CE")

    def generate_pe_graph(self, event):
        selected_pe_strike = self.pe_combo.get()
        self.plot_graph('option_pe_data', selected_pe_strike, "PE")

    def plot_graph(self, table_name, strike_price, option_type):
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Fetch data for the selected strike price
        self.cursor.execute(f"""
            SELECT date_time, oi, changein_oi, ltp FROM {table_name}
            WHERE strike_price = ? AND date_time LIKE ?
            ORDER BY date_time
        """, (strike_price, f"{today}%"))
        
        data = self.cursor.fetchall()
        
        if not data:
            messagebox.showwarning("No Data", f"No data available for {option_type} strike price {strike_price} for today.")
            return

        # Prepare data for plotting
        dates = [datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S') for row in data]
        oi_values = [row[1] for row in data]
        changein_oi_values = [row[2] for row in data]
        ltp_values = [row[3] for row in data]

        # Create a new window for the graph
        graph_window = tk.Toplevel(self.root)
        graph_window.title(f"{option_type} Strike Price {strike_price} Graph")
        
        # Create a figure and axis
        fig, ax1 = plt.subplots(figsize=(10, 6))

        # Plot OI
        ax1.set_xlabel('Time')
        ax1.set_ylabel('Open Interest', color='blue')
        ax1.plot(dates, oi_values, color='blue', label='Open Interest')
        ax1.tick_params(axis='y', labelcolor='blue')

        # Create a second y-axis for Change in OI and LTP
        ax2 = ax1.twinx()
        ax2.set_ylabel('Change in OI / LTP', color='red')
        ax2.plot(dates, changein_oi_values, color='orange', label='Change in OI')
        ax2.plot(dates, ltp_values, color='red', label='LTP')
        ax2.tick_params(axis='y', labelcolor='red')

        # Add legends
        fig.tight_layout()
        ax1.legend(loc='upper left')
        ax2.legend(loc='upper right')

        # Show the plot
        plt.title(f"{option_type} Strike Price {strike_price} - OI, Change in OI, and LTP")
        plt.show()

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
        ce_frame = ttk.LabelFrame(chain_frame, text="Call Options (CE)", padding=5)
        ce_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        # PE Frame (Right Side)
        pe_frame = ttk.LabelFrame(chain_frame, text="Put Options (PE)", padding=5)
        pe_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))

        # Create treeviews with updated columns
        columns = ("Strike", "OI", "Chng in OI", "Volume", "LTP", "Chng", "IV")
        
        # CE Treeview
        self.ce_tree = CustomTreeview(ce_frame, columns=columns, show="headings", height=15)
        ce_scroll = ttk.Scrollbar(ce_frame, orient=tk.VERTICAL, command=self.ce_tree.yview)
        self.ce_tree.configure(yscrollcommand=ce_scroll.set)
        
        # PE Treeview
        self.pe_tree = CustomTreeview(pe_frame, columns=columns, show="headings", height=15)
        pe_scroll = ttk.Scrollbar(pe_frame, orient=tk.VERTICAL, command=self.pe_tree.yview)
        self.pe_tree.configure(yscrollcommand=pe_scroll.set)

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
            self.root.after(300000, lambda: self.loop.create_task(self.update_data()))  # Fetch data every 5 minutes

    def process_and_display_data(self, data):
        # Implementation of data processing and display logic
        pass  # Replace with your existing logic

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