import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
import aiohttp
import asyncio
import json
from datetime import datetime
import logging
from typing import Dict, List, Optional, Union
import platform

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('nifty_options.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_name: str = "E:/nifty_data.db"):
        """Initialize database connection with proper error handling."""
        try:
            self.conn = sqlite3.connect(db_name)
            self.cursor = self.conn.cursor()
            self.create_table()
        except sqlite3.Error as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    def create_table(self) -> None:
        """Create the options data table with proper indexing for performance."""
        try:
            self.cursor.executescript("""
                CREATE TABLE IF NOT EXISTS option_data (
                    timestamp DATETIME,
                    strike REAL,
                    oi_ce INTEGER,
                    chng_oi_ce INTEGER,
                    volume_ce INTEGER,
                    ltp_ce REAL,
                    chng_ce REAL,
                    implied_volatility_ce REAL,
                    oi_pe INTEGER,
                    chng_oi_pe INTEGER,
                    volume_pe INTEGER,
                    ltp_pe REAL,
                    chng_pe REAL,
                    implied_volatility_pe REAL,
                    PRIMARY KEY (timestamp, strike)
                );
                
                CREATE INDEX IF NOT EXISTS idx_volume_ce ON option_data(volume_ce);
                CREATE INDEX IF NOT EXISTS idx_volume_pe ON option_data(volume_pe);
                CREATE INDEX IF NOT EXISTS idx_timestamp ON option_data(timestamp);
            """)
            self.conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Failed to create table: {e}")
            raise

    def insert_data(self, data: Dict[str, Union[datetime, float, int]]) -> None:
        """Insert data with proper parameter binding and error handling."""
        try:
            self.cursor.execute("""
                INSERT OR REPLACE INTO option_data (
                    timestamp, strike,
                    oi_ce, chng_oi_ce, volume_ce, ltp_ce, chng_ce, implied_volatility_ce,
                    oi_pe, chng_oi_pe, volume_pe, ltp_pe, chng_pe, implied_volatility_pe
                ) VALUES (
                    :timestamp, :strike,
                    :oi_ce, :chng_oi_ce, :volume_ce, :ltp_ce, :chng_ce, :iv_ce,
                    :oi_pe, :chng_oi_pe, :volume_pe, :ltp_pe, :chng_pe, :iv_pe
                )
            """, data)
            self.conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Failed to insert data: {e}")
            raise

    def get_top_volume_data(self, option_type: str) -> List[tuple]:
        """Get top volume data with proper error handling and input validation."""
        if option_type not in ('CE', 'PE'):
            raise ValueError("Option type must be 'CE' or 'PE'")
            
        try:
            volume_col = f"volume_{option_type.lower()}"
            change_col = f"chng_{option_type.lower()}"
            
            query = f"""
                WITH RankedData AS (
                    SELECT DISTINCT strike, {volume_col} as volume, {change_col} as change,
                           ROW_NUMBER() OVER (PARTITION BY strike ORDER BY timestamp DESC) as rn
                    FROM option_data
                    WHERE {volume_col} > 0
                )
                SELECT strike, volume, change
                FROM RankedData
                WHERE rn = 1
                ORDER BY volume DESC
                LIMIT 3
            """
            
            self.cursor.execute(query)
            rows = self.cursor.fetchall()
            return [(strike, volume, f"{(change/volume)*100:.2f}%" if volume else "0%")
                    for strike, volume, change in rows]
        except sqlite3.Error as e:
            logger.error(f"Failed to fetch top volume data: {e}")
            raise

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self) -> None:
        """Close database connection with proper error handling."""
        try:
            self.conn.close()
        except sqlite3.Error as e:
            logger.error(f"Error closing database connection: {e}")
            raise

class CustomTreeview(ttk.Treeview):
    """Enhanced Treeview with proper styling and configuration."""
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        
        # Configure tags for different styling scenarios
        style = ttk.Style()
        style.configure("Treeview", rowheight=25)
        
        self.tag_configure('negative_value', foreground='#FF4444')
        self.tag_configure('atm', background='#FFFFD1')
        self.tag_configure('above_atm', background='#F8F8F8')
        self.tag_configure('below_atm', background='#F0F0F0')

    def insert(self, parent_iid: str, index: str, **kwargs) -> str:
        """Enhanced insert method with proper type checking and error handling."""
        item = super().insert(parent_iid, index, **kwargs)
        values = kwargs.get('values', [])
        
        try:
            if len(values) >= 6:
                change_value = float(values[5])
                if change_value < 0:
                    current_tags = list(self.item(item)['tags'] or [])
                    current_tags.append('negative_value')
                    self.item(item, tags=current_tags)
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to process value for styling: {e}")
        
        return item

class NiftyOptionChain:
    """Enhanced Options Chain fetcher with proper session management and error handling."""
    def __init__(self):
        self.url_oc = "https://www.nseindia.com/option-chain"
        self.url_nf = 'https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY'
        self.headers = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'accept-language': 'en,gu;q=0.9,hi;q=0.8',
            'accept-encoding': 'gzip, deflate, br'
        }
        self.cookies: Dict[str, str] = {}
        self.session: Optional[aiohttp.ClientSession] = None
        self._retry_count = 0
        self._max_retries = 3

    async def initialize_session(self) -> None:
        """Initialize session with retry logic and proper error handling."""
        if self.session and not self.session.closed:
            await self.session.close()
            
        self.session = aiohttp.ClientSession()
        try:
            async with self.session.get(
                self.url_oc,
                headers=self.headers,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                if response.status == 200:
                    self.cookies = {k: v.value for k, v in response.cookies.items()}
                else:
                    raise aiohttp.ClientError(f"Failed to initialize session: {response.status}")
        except Exception as e:
            logger.error(f"Session initialization failed: {e}")
            await self.session.close()
            self.session = None
            raise

    async def get_data(self) -> str:
        """Fetch data with retry logic and proper error handling."""
        if not self.session or self.session.closed:
            await self.initialize_session()

        try:
            async with self.session.get(
                self.url_nf,
                headers=self.headers,
                cookies=self.cookies,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                if response.status == 401 and self._retry_count < self._max_retries:
                    self._retry_count += 1
                    await self.initialize_session()
                    return await self.get_data()
                elif response.status == 200:
                    self._retry_count = 0
                    return await response.text()
                else:
                    raise aiohttp.ClientError(f"Unexpected status: {response.status}")
        except Exception as e:
            logger.error(f"Failed to fetch data: {e}")
            raise

    async def close(self) -> None:
        """Close session with proper error handling."""
        if self.session and not self.session.closed:
            try:
                await self.session.close()
            except Exception as e:
                logger.error(f"Error closing session: {e}")
                raise

    async def __aenter__(self):
        await self.initialize_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
        
        
class NiftyApp:
    """Main application class with proper UI management and async operations."""
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Nifty Option Chain Viewer")
        self.root.geometry("1600x600")
        
        self.nifty_client = NiftyOptionChain()
        self.db = Database()
        self.data_to_save = []
        self.update_task = None
        self.is_running = False
        
        # Configure async loop based on platform
        if platform.system() == 'Windows':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        self.setup_ui()
        self.start_async_updates()

    def setup_ui(self) -> None:
        """Initialize and configure the UI components."""
        # Main container
        main_container = ttk.Frame(self.root, padding="5")
        main_container.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Control Panel
        control_frame = ttk.LabelFrame(main_container, text="Controls", padding="5")
        control_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        self.update_button = ttk.Button(
            control_frame, 
            text="Start Updates", 
            command=self.toggle_updates
        )
        self.update_button.grid(row=0, column=0, padx=5)
        
        self.status_label = ttk.Label(control_frame, text="Status: Stopped")
        self.status_label.grid(row=0, column=1, padx=5)
        
        # Options Chain Display
        tree_frame = ttk.Frame(main_container)
        tree_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure Treeview
        columns = (
            'strike', 
            'oi_ce', 'chng_oi_ce', 'volume_ce', 'ltp_ce', 'chng_ce', 'iv_ce',
            'oi_pe', 'chng_oi_pe', 'volume_pe', 'ltp_pe', 'chng_pe', 'iv_pe'
        )
        
        self.tree = CustomTreeview(
            tree_frame,
            columns=columns,
            show='headings',
            selectmode='none'
        )
        
        # Configure column headings
        column_headings = {
            'strike': 'Strike Price',
            'oi_ce': 'OI (CE)', 'chng_oi_ce': 'Change in OI (CE)',
            'volume_ce': 'Volume (CE)', 'ltp_ce': 'LTP (CE)',
            'chng_ce': 'Change (CE)', 'iv_ce': 'IV (CE)',
            'oi_pe': 'OI (PE)', 'chng_oi_pe': 'Change in OI (PE)',
            'volume_pe': 'Volume (PE)', 'ltp_pe': 'LTP (PE)',
            'chng_pe': 'Change (PE)', 'iv_pe': 'IV (PE)'
        }
        
        for col in columns:
            self.tree.heading(col, text=column_headings[col])
            self.tree.column(col, width=100, anchor=tk.CENTER)
        
        # Add scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        # Grid layout for tree and scrollbars
        self.tree.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        vsb.grid(row=0, column=1, sticky=(tk.N, tk.S))
        hsb.grid(row=1, column=0, sticky=(tk.E, tk.W))
        
        # Configure grid weights
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)
        main_container.columnconfigure(0, weight=1)
        main_container.rowconfigure(1, weight=1)

    def start_async_updates(self) -> None:
        """Initialize async update loop."""
        self.is_running = True
        self.loop.create_task(self.update_data_periodically())

    def toggle_updates(self) -> None:
        """Toggle data updates on/off."""
        if self.is_running:
            self.is_running = False
            self.update_button.configure(text="Start Updates")
            self.status_label.configure(text="Status: Stopped")
        else:
            self.is_running = True
            self.update_button.configure(text="Stop Updates")
            self.status_label.configure(text="Status: Running")
            self.loop.create_task(self.update_data_periodically())

    async def update_data_periodically(self) -> None:
        """Periodically fetch and update options data."""
        while self.is_running:
            try:
                await self.fetch_and_process_data()
                await asyncio.sleep(60)  # Update every minute
            except Exception as e:
                logger.error(f"Error in periodic update: {e}")
                self.show_error("Update Error", f"Failed to update data: {str(e)}")
                self.is_running = False
                self.update_button.configure(text="Start Updates")
                self.status_label.configure(text="Status: Error")
                break

    async def fetch_and_process_data(self) -> None:
        """Fetch and process options chain data."""
        try:
            async with self.nifty_client as client:
                data = await client.get_data()
                json_data = json.loads(data)
                
                self.process_and_display_data(json_data)
                self.save_data_to_db()
                
                self.root.update_idletasks()
        except Exception as e:
            logger.error(f"Error fetching/processing data: {e}")
            raise

    def process_and_display_data(self, json_data: dict) -> None:
        """Process and display options chain data in the Treeview."""
        try:
            self.tree.delete(*self.tree.get_children())
            self.data_to_save.clear()
            
            records = json_data.get('records', {})
            timestamp = datetime.now()
            
            for option in records.get('data', []):
                ce_data = option.get('CE', {})
                pe_data = option.get('PE', {})
                strike = option.get('strikePrice', 0)
                
                row_data = {
                    'timestamp': timestamp,
                    'strike': strike,
                    'oi_ce': ce_data.get('openInterest', 0),
                    'chng_oi_ce': ce_data.get('changeinOpenInterest', 0),
                    'volume_ce': ce_data.get('totalTradedVolume', 0),
                    'ltp_ce': ce_data.get('lastPrice', 0),
                    'chng_ce': ce_data.get('change', 0),
                    'iv_ce': ce_data.get('impliedVolatility', 0),
                    'oi_pe': pe_data.get('openInterest', 0),
                    'chng_oi_pe': pe_data.get('changeinOpenInterest', 0),
                    'volume_pe': pe_data.get('totalTradedVolume', 0),
                    'ltp_pe': pe_data.get('lastPrice', 0),
                    'chng_pe': pe_data.get('change', 0),
                    'iv_pe': pe_data.get('impliedVolatility', 0)
                }
                
                self.data_to_save.append(row_data)
                
                # Insert into Treeview
                values = [row_data[key] for key in row_data.keys()]
                self.tree.insert('', tk.END, values=values)
                
        except Exception as e:
            logger.error(f"Error processing data: {e}")
            raise

    def save_data_to_db(self) -> None:
        """Save processed data to database."""
        try:
            for row_data in self.data_to_save:
                self.db.insert_data(row_data)
        except Exception as e:
            logger.error(f"Error saving to database: {e}")
            self.show_error("Database Error", f"Failed to save data: {str(e)}")

    def show_error(self, title: str, message: str) -> None:
        """Display error message to user."""
        messagebox.showerror(title, message)

    def on_closing(self) -> None:
        """Clean up resources when closing the application."""
        self.is_running = False
        
        try:
            # Close database connection
            self.db.close()
            
            # Stop async loop
            pending = asyncio.all_tasks(self.loop)
            for task in pending:
                task.cancel()
            
            self.loop.stop()
            self.loop.close()
            
            self.root.destroy()
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            raise

def main():
    """Main entry point for the application."""
    try:
        root = tk.Tk()
        app = NiftyApp(root)
        root.protocol("WM_DELETE_WINDOW", app.on_closing)
        root.mainloop()
    except Exception as e:
        logger.error(f"Application error: {e}")
        raise

if __name__ == "__main__":
    main()        