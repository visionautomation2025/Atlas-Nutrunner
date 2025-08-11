import tkinter as tk
from tkinter import ttk, messagebox
import aiohttp
import pandas as pd
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


def show_mouse_position(event):
    print(f"x={event.x}, y={event.y}")


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
        self.root.geometry("1800x1000")  # Set geometry to 1000x1000
        self.nifty_client = NiftyOptionChain()
        self.setup_database()  # Initialize the database first
        self.setup_ui()        # Then set up the UI
        self.setup_async_loop()

    def setup_ui(self):
        # Main container
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create a Notebook (tabs)
        self.notebook = ttk.Notebook(main_container)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Create tabs
        self.tab1 = ttk.Frame(self.notebook)
        self.tab2 = ttk.Frame(self.notebook)
        self.tab3 = ttk.Frame(self.notebook)
        self.tab4 = ttk.Frame(self.notebook)

        self.notebook.add(self.tab1, text="CE and PE Data")
        self.notebook.add(self.tab2, text="Graph Data")
        self.notebook.add(self.tab3, text="Ask/Bid Data")
        self.notebook.add(self.tab4, text="IV Data")

        # Setup the first tab with tree views and volume widgets
        self.setup_first_tab()

        # Setup other tabs (you can fill these with your desired content)
        #self.setup_second_tab()
        self.setup_third_tab()
        self.setup_fourth_tab()

        # Status label
        self.status_label = ttk.Label(main_container, text="Ready", font=("Arial", 10))
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)

        # Price displays
        price_frame = ttk.Frame(main_container)
        price_frame.pack(side=tk.TOP, fill=tk.X)

        ttk.Label(price_frame, text="Current Market Price:", font=("Arial", 12)).pack(side=tk.LEFT)
        self.price_label = ttk.Label(price_frame, text="--", font=("Arial", 12, 'bold'))
        self.price_label.pack(side=tk.LEFT, padx=(5, 20))

        ttk.Label(price_frame, text="ATM Strike Price:", font=("Arial", 12)).pack(side=tk.LEFT)
        self.atm_label = ttk.Label(price_frame, text="--", font=("Arial", 12, 'bold'))
        self.atm_label.pack(side=tk.LEFT, padx=5)

        # Timestamp label
        self.timestamp_label = ttk.Label(price_frame, text="Last Updated: --", font=("Arial", 10))
        self.timestamp_label.pack(side=tk.RIGHT)

    def setup_first_tab(self):
        # Create a grid layout for the first tab
        self.tab1.columnconfigure(0, weight=1)
        self.tab1.columnconfigure(1, weight=1)
        self.tab1.rowconfigure(0, weight=1)
        self.tab1.rowconfigure(1, weight=1)

        # CE Frame
        ce_frame = ttk.LabelFrame(self.tab1, text="Call Options (CE)", padding=5)
        ce_frame.grid(row=0, column=0, sticky="nsew", padx=(5, 2), pady=5)

        # PE Frame
        pe_frame = ttk.LabelFrame(self.tab1, text="Put Options (PE)", padding=5)
        pe_frame.grid(row=0, column=1, sticky="nsew", padx=(2, 5), pady=5)

        # Volume CE Frame
        volume_ce_frame = ttk.LabelFrame(self.tab1, text="Top 3 High Volume CE", padding=5)
        volume_ce_frame.grid(row=1, column=0, sticky="nsew", padx=(5, 2), pady=5)

        # Volume PE Frame
        volume_pe_frame = ttk.LabelFrame(self.tab1, text="Top 3 High Volume PE", padding=5)
        volume_pe_frame.grid(row=1, column=1, sticky="nsew", padx=(2, 5), pady=5)

        # Create treeviews with updated columns
        columns = ("Strike", "OI", "Chng in OI", "Volume", "LTP", "IV")

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

        # Treeview for Volume CE Track
        volume_ce_columns = ("Strike", "Volume", "OI", "Chng in OI", "LTP", "IV")
        self.volume_ce_tree = ttk.Treeview(volume_ce_frame, columns=volume_ce_columns, show="headings", height=5 )
        volume_ce_scroll = ttk.Scrollbar(volume_ce_frame, orient=tk.VERTICAL, command=self.volume_ce_tree.yview)
        self.volume_ce_tree.configure(yscrollcommand=volume_ce_scroll.set)

        # Treeview for Volume PE Track
        volume_pe_columns = ("Strike", "Volume", "OI", "Chng in OI", "LTP", "IV")
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
        
        for col in columns:
          self.ce_tree.heading(col, text=col)
          self.ce_tree.column(col, width=100, anchor="center")

# Configure columns for PE Treeview
        for col in columns:
          self.pe_tree.heading(col, text=col)
          self.pe_tree.column(col, width=100, anchor="center")

    def setup_second_tab(self):
    # Clear the second tab
        current_date = datetime.today().strftime('%Y-%m-%d')
        for widget in self.tab2.winfo_children():
            widget.destroy()

        # Create a frame for the graphs
        graph_frame = ttk.Frame(self.tab2)
        graph_frame.pack(fill=tk.BOTH, expand=True)
        
        # Define strike prices
        strike_price_ce = strike_price_ce1
        strike_price_pe = strike_price_pe1
        strike_price_ce21 = strike_price_ce2
        strike_price_pe21 = strike_price_pe2
        
        messagebox.showinfo("Title", f"This is your message: {strike_price_ce}")
        # Query to fetch data for CE
        query_ce = f"""
        SELECT date_time, oi, changein_oi, ltp, volume
        FROM option_ce_data
        WHERE strike_price = {strike_price_ce} AND date_time BETWEEN '{current_date} 09:00:00' AND '{current_date} 15:30:00'
        """

        # Query to fetch data for PE
        query_pe = f"""
        SELECT date_time, oi, changein_oi, ltp, volume
        FROM option_pe_data
        WHERE strike_price = {strike_price_pe} AND date_time BETWEEN '{current_date} 09:00:00' AND '{current_date} 15:30:00'
        """
         # Query to fetch data for second CE
        query_ce2 = f"""
        SELECT date_time, oi, changein_oi, ltp, volume
        FROM option_ce_data
        WHERE strike_price = {strike_price_ce21} AND date_time BETWEEN '{current_date} 09:00:00' AND '{current_date} 15:30:00'
        """

        # Query to fetch data for second PE
        query_pe2 = f"""
        SELECT date_time, oi, changein_oi, ltp, volume
        FROM option_pe_data
        WHERE strike_price = {strike_price_pe21} AND date_time BETWEEN '{current_date} 09:00:00' AND '{current_date} 15:30:00'
        """

        # Fetch data
        with sqlite3.connect('E:/nifty_data.db') as conn:
            df_ce = pd.read_sql_query(query_ce, conn)
            df_pe = pd.read_sql_query(query_pe, conn)
            df_ce2 = pd.read_sql_query(query_ce2, conn)
            df_pe2 = pd.read_sql_query(query_pe2, conn)

        # Convert date_time to datetime format
        df_ce['date_time'] = pd.to_datetime(df_ce['date_time'])
        df_pe['date_time'] = pd.to_datetime(df_pe['date_time'])
        df_ce2['date_time'] = pd.to_datetime(df_ce2['date_time'])
        df_pe2['date_time'] = pd.to_datetime(df_pe2['date_time'])

        # -------- CE Graph --------
        frame_ce_graph = ttk.Frame(graph_frame)
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
        frame_pe_graph = ttk.Frame(graph_frame)
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
        
        
        
        
        frame_ce_graph2 = ttk.Frame(graph_frame)
        frame_ce_graph2.pack(side='left', padx=10)

        fig_ce2, ax_ce2 = plt.subplots(figsize=(5, 3))  # Small figure size

        # Primary y-axis (Change in OI)
        ax_ce2.plot(df_ce2['date_time'], df_ce2['changein_oi'], label="CE Change in OI", color='green')
        ax_ce2.set_xlabel("Time")
        ax_ce2.set_ylabel("Change in OI", color='green')
        ax_ce2.tick_params(axis='y', labelcolor='green')

        # Secondary y-axis (LTP)
        ax_ce2_ltp = ax_ce2.twinx()
        ax_ce2_ltp.plot(df_ce2['date_time'], df_ce2['ltp'], label="CE LTP", color='red')
        ax_ce2_ltp.set_ylabel("LTP", color='red')
        ax_ce2_ltp.tick_params(axis='y', labelcolor='red')

        # Legends
        lines_ce2, labels_ce2 = ax_ce2.get_legend_handles_labels()
        lines_ltp_ce2, labels_ltp_ce2 = ax_ce2_ltp.get_legend_handles_labels()
        ax_ce2.legend(lines_ce2 + lines_ltp_ce2, labels_ce2 + labels_ltp_ce2, loc="upper left")

        # **Title with Strike Price**
        ax_ce2.set_title(f"CE Data (Strike Price: {strike_price_ce2})")

        canvas_ce2 = FigureCanvasTkAgg(fig_ce2, master=frame_ce_graph2)
        canvas_ce2_widget = canvas_ce2.get_tk_widget()
        canvas_ce2_widget.pack()

        # -------- Second PE Graph --------
        frame_pe_graph2 = ttk.Frame(graph_frame)
        frame_pe_graph2.pack(side='right', padx=10)

        fig_pe2, ax_pe2 = plt.subplots(figsize=(5, 3))  # Small figure size

        # Primary y-axis (Change in OI)
        ax_pe2.plot(df_pe2['date_time'], df_pe2['changein_oi'], label="PE Change in OI", color='blue')
        ax_pe2.set_xlabel("Time")
        ax_pe2.set_ylabel("Change in OI", color='blue')
        ax_pe2.tick_params(axis='y', labelcolor='blue')

        # Secondary y-axis (LTP)
        ax_pe2_ltp = ax_pe2.twinx()
        ax_pe2_ltp.plot(df_pe2['date_time'], df_pe2['ltp'], label="PE LTP", color='orange')
        ax_pe2_ltp.set_ylabel("LTP", color='orange')
        ax_pe2_ltp.tick_params(axis='y', labelcolor='orange')

        # Legends
        lines_pe2, labels_pe2 = ax_pe2.get_legend_handles_labels()
        lines_ltp_pe2, labels_ltp_pe2 = ax_pe2_ltp.get_legend_handles_labels()
        ax_pe2.legend(lines_pe2 + lines_ltp_pe2, labels_pe2 + labels_ltp_pe2, loc="upper left")

        # **Title with Strike Price**
        ax_pe2.set_title(f"PE Data (Strike Price: {strike_price_pe2})")

        canvas_pe2 = FigureCanvasTkAgg(fig_pe2, master=frame_pe_graph2)
        canvas_pe2_widget = canvas_pe2.get_tk_widget()
        canvas_pe2_widget.pack()

    def setup_third_tab(self):
        # Placeholder for Ask/Bid Data tab
        ttk.Label(self.tab3, text="Ask/Bid Data will be displayed here.").pack(pady=20)

    def setup_fourth_tab(self):
        # Placeholder for IV Data tab
        ttk.Label(self.tab4, text="IV Data will be displayed here.").pack(pady=20)

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
            self.process_and_display_data(data)
            self.status_label.config(text="Data updated successfully")
            self.timestamp_label.config(text=f"Last Updated: {datetime.now().strftime('%H:%M:%S')}")
        except Exception as e:
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
            top_ce_data = ce_data_list[:5]  # Changed to 3
            
            for item in self.volume_ce_tree.get_children():
                self.volume_ce_tree.delete(item)

            for strike, volume, oi, changein_oi, ltp, chng in top_ce_data:
                self.volume_ce_tree.insert("", "end", values=(strike, volume, oi, changein_oi, ltp, chng))

            # Display top 3 high volume PE strike prices in the new grid
            pe_data_list.sort(key=lambda x: x[1], reverse=True)
            top_pe_data = pe_data_list[:5]  # Changed to 3

            for item in self.volume_pe_tree.get_children():
                self.volume_pe_tree.delete(item)

            for strike, volume, oi, changein_oi, ltp, chng in top_pe_data:
                self.volume_pe_tree.insert("", "end", values=(strike, volume, oi, changein_oi, ltp, chng))
            global strike_price_ce1
            global strike_price_pe1
            global strike_price_ce2
            global strike_price_pe2
            
            last_ce_data = top_ce_data[0]
            strike_price_ce1 = last_ce_data[0]
            last_ce_data2 = top_ce_data[1]
            strike_price_ce2 = last_ce_data2[0]
            
            last_pe_data = top_pe_data[0]
            strike_price_pe1 = last_pe_data[0]
            last_pe_data2 = top_pe_data[1]
            strike_price_pe2 = last_pe_data2[0]
            
            messagebox.showinfo("Title", f"This second: {strike_price_ce2}")
            self.setup_second_tab()
            
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
    root.bind('<Motion>', show_mouse_position)
    root.mainloop()


if __name__ == "__main__":
    main()