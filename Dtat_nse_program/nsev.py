import sys
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import asyncio
import aiohttp
import json
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QFrame, QTextEdit, QPushButton, QScrollArea, QGroupBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer, Signal, QObject, QThread
from PySide6.QtGui import QColor, QFont, QPalette
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

class Worker(QObject):
    data_updated = Signal(dict)
    finished = Signal()

    def __init__(self):
        super().__init__()
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
        self.running = True

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

    async def get_option_chain_data(self):
        if not self.session:
            await self.initialize_session()

        try:
            async with self.session.get(self.url_nf, headers=self.headers, 
                                      cookies=self.cookies, timeout=30) as response:
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
            await self.initialize_session()
            raise

    async def run(self):
        while self.running:
            try:
                data = await self.get_option_chain_data()
                processed_data = self.process_data(data)
                self.data_updated.emit(processed_data)
                await asyncio.sleep(60)  # Update every minute
            except Exception as e:
                print(f"Error in worker: {e}")
                await asyncio.sleep(10)
        self.finished.emit()

    def process_data(self, data):
        # Extract relevant data for GUI
        underlying_value = data["records"]["underlyingValue"]
        current_expiry = data["records"]["expiryDates"][0]
        
        # Calculate PCR
        total_ce_oi = sum(item["CE"]["openInterest"] for item in data["records"]["data"] if "CE" in item)
        total_pe_oi = sum(item["PE"]["openInterest"] for item in data["records"]["data"] if "PE" in item)
        pcr = total_pe_oi / total_ce_oi if total_ce_oi != 0 else 0
        
        # Calculate ATM strike
        atm_strike = round(underlying_value / 50) * 50
        
        # Find max pain
        strikes = []
        pain_values = []
        for item in data["records"]["data"]:
            if "strikePrice" in item:
                strike = item["strikePrice"]
                ce_oi = item["CE"]["openInterest"] if "CE" in item else 0
                pe_oi = item["PE"]["openInterest"] if "PE" in item else 0
                pain = (ce_oi * max(0, strike - underlying_value)) + (pe_oi * max(0, underlying_value - strike))
                strikes.append(strike)
                pain_values.append(pain)
        
        max_pain = strikes[pain_values.index(min(pain_values))] if pain_values else atm_strike
        
        # Prepare entry signals
        call_vol = sum(item["CE"]["totalTradedVolume"] for item in data["records"]["data"] if "CE" in item)
        put_vol = sum(item["PE"]["totalTradedVolume"] for item in data["records"]["data"] if "PE" in item)
        net_flow = call_vol - put_vol
        
        return {
            "underlying_value": underlying_value,
            "atm_strike": atm_strike,
            "max_pain": max_pain,
            "total_ce_oi": total_ce_oi,
            "total_pe_oi": total_pe_oi,
            "pcr": pcr,
            "call_vol": call_vol,
            "put_vol": put_vol,
            "net_flow": net_flow,
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "raw_data": data
        }

    def stop(self):
        self.running = False

class OptionMonitor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NSE Option Chain Monitor with Entry Signals")
        self.setGeometry(100, 100, 1800, 1200)
        
        # Initialize database
        self.setup_database()
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget)
        
        # Create header
        self.create_header()
        
        # Create analysis section
        self.create_analysis_section()
        
        # Create entry signals section
        self.create_entry_signals_section()
        
        # Create strike cards section
        self.create_strike_cards_section()
        
        # Initialize worker thread
        self.worker = Worker()
        self.thread = QThread()
        self.worker.moveToThread(self.thread)
        self.worker.data_updated.connect(self.update_data)
        self.thread.started.connect(lambda: asyncio.ensure_future(self.worker.run()))
        self.thread.start()
        
        # Set up timer for periodic updates
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_ui)
        self.update_timer.start(1000)  # Update UI every second
        
        # Store last data
        self.last_data = None
        self.historical_data = []
        
    def setup_database(self):
        """Setup the database and create necessary tables"""
        with sqlite3.connect('nifty_data.db') as conn:
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

    def create_header(self):
        """Create the header section with market metrics"""
        header_frame = QFrame()
        header_frame.setFrameShape(QFrame.StyledPanel)
        header_layout = QVBoxLayout(header_frame)
        
        # Title
        title_label = QLabel("NSE Option Chain Monitor with Entry Signals")
        title_label.setAlignment(Qt.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title_label.setFont(title_font)
        header_layout.addWidget(title_label)
        
        # Market metrics
        metrics_frame = QFrame()
        metrics_layout = QHBoxLayout(metrics_frame)
        
        # Spot price and ATM
        spot_atm_frame = QFrame()
        spot_atm_layout = QVBoxLayout(spot_atm_frame)
        
        self.spot_price_label = QLabel("Nifty: --")
        self.spot_price_label.setFont(QFont("Arial", 14, QFont.Bold))
        
        self.atm_label = QLabel("ATM Strike: --")
        self.atm_label.setFont(QFont("Arial", 14, QFont.Bold))
        
        self.max_pain_label = QLabel("Max Pain: --")
        self.max_pain_label.setFont(QFont("Arial", 14, QFont.Bold))
        
        spot_atm_layout.addWidget(self.spot_price_label)
        spot_atm_layout.addWidget(self.atm_label)
        spot_atm_layout.addWidget(self.max_pain_label)
        metrics_layout.addWidget(spot_atm_frame)
        
        # PCR
        pcr_frame = QFrame()
        pcr_layout = QVBoxLayout(pcr_frame)
        
        self.total_ce_oi_label = QLabel("Total CE OI: --")
        self.total_pe_oi_label = QLabel("Total PE OI: --")
        self.pcr_label = QLabel("PCR: --")
        self.pcr_label.setFont(QFont("Arial", 12, QFont.Bold))
        
        pcr_layout.addWidget(self.total_ce_oi_label)
        pcr_layout.addWidget(self.total_pe_oi_label)
        pcr_layout.addWidget(self.pcr_label)
        metrics_layout.addWidget(pcr_frame)
        
        # Volume
        volume_frame = QFrame()
        volume_layout = QVBoxLayout(volume_frame)
        
        self.call_vol_label = QLabel("Call Volume: --")
        self.put_vol_label = QLabel("Put Volume: --")
        self.net_flow_label = QLabel("Net Flow: --")
        self.net_flow_label.setFont(QFont("Arial", 12, QFont.Bold))
        
        volume_layout.addWidget(self.call_vol_label)
        volume_layout.addWidget(self.put_vol_label)
        volume_layout.addWidget(self.net_flow_label)
        metrics_layout.addWidget(volume_frame)
        
        # Status
        status_frame = QFrame()
        status_layout = QVBoxLayout(status_frame)
        
        self.status_label = QLabel("Status: Initializing...")
        self.time_label = QLabel("Last Update: --")
        
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.time_label)
        metrics_layout.addWidget(status_frame)
        
        header_layout.addWidget(metrics_frame)
        self.main_layout.addWidget(header_frame)

    def create_analysis_section(self):
        """Create the analysis section with tabs"""
        analysis_frame = QFrame()
        analysis_frame.setFrameShape(QFrame.StyledPanel)
        analysis_layout = QHBoxLayout(analysis_frame)
        
        # Left side - Summary
        summary_group = QGroupBox("Market Summary")
        summary_layout = QVBoxLayout()
        
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        self.summary_text.setFont(QFont("Courier New", 10))
        
        summary_layout.addWidget(self.summary_text)
        summary_group.setLayout(summary_layout)
        analysis_layout.addWidget(summary_group, stretch=2)
        
        # Right side - Entry Signals
        signals_group = QGroupBox("Entry Signals Analysis")
        signals_layout = QVBoxLayout()
        
        self.signals_text = QTextEdit()
        self.signals_text.setReadOnly(True)
        self.signals_text.setFont(QFont("Courier New", 10))
        
        signals_layout.addWidget(self.signals_text)
        signals_group.setLayout(signals_layout)
        analysis_layout.addWidget(signals_group, stretch=1)
        
        self.main_layout.addWidget(analysis_frame)

    def create_entry_signals_section(self):
        """Create the entry signals section with historical data"""
        entry_frame = QFrame()
        entry_frame.setFrameShape(QFrame.StyledPanel)
        entry_layout = QVBoxLayout(entry_frame)
        
        # Title
        entry_title = QLabel("Historical Entry Signals")
        entry_title.setAlignment(Qt.AlignCenter)
        entry_title.setFont(QFont("Arial", 14, QFont.Bold))
        entry_layout.addWidget(entry_title)
        
        # Table
        self.entry_table = QTableWidget()
        self.entry_table.setColumnCount(7)
        self.entry_table.setHorizontalHeaderLabels([
            "Time", "Nifty", "Change", "Call Vol", "Put Vol", "Net Flow", "Signal"
        ])
        self.entry_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.entry_table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        entry_layout.addWidget(self.entry_table)
        self.main_layout.addWidget(entry_frame)

    def create_strike_cards_section(self):
        """Create the strike cards section"""
        cards_frame = QFrame()
        cards_frame.setFrameShape(QFrame.StyledPanel)
        cards_layout = QVBoxLayout(cards_frame)
        
        # Title
        cards_title = QLabel("Key Strike Levels")
        cards_title.setAlignment(Qt.AlignCenter)
        cards_title.setFont(QFont("Arial", 14, QFont.Bold))
        cards_layout.addWidget(cards_title)
        
        # Scroll area for cards
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QHBoxLayout(scroll_content)
        
        # Create cards for different strikes
        self.strike_cards = []
        strikes = ["ATM", "ATM+100", "ATM+200", "ATM-100", "ATM-200"]
        
        for strike in strikes:
            card = QGroupBox(strike)
            card_layout = QVBoxLayout()
            
            ce_label = QLabel("CE: --")
            pe_label = QLabel("PE: --")
            oi_label = QLabel("OI Change: --")
            iv_label = QLabel("IV: --")
            
            card_layout.addWidget(ce_label)
            card_layout.addWidget(pe_label)
            card_layout.addWidget(oi_label)
            card_layout.addWidget(iv_label)
            
            card.setLayout(card_layout)
            scroll_layout.addWidget(card)
            
            self.strike_cards.append({
                "widget": card,
                "ce_label": ce_label,
                "pe_label": pe_label,
                "oi_label": oi_label,
                "iv_label": iv_label
            })
        
        scroll_area.setWidget(scroll_content)
        cards_layout.addWidget(scroll_area)
        self.main_layout.addWidget(cards_frame)

    def update_data(self, data):
        """Update the GUI with new data"""
        self.last_data = data
        self.historical_data.append(data)
        
        # Keep only last 30 minutes of data
        if len(self.historical_data) > 30:
            self.historical_data.pop(0)
        
        # Update UI
        self.update_ui()

    def update_ui(self):
        """Update all UI elements"""
        if not self.last_data:
            return
            
        data = self.last_data
        
        # Update basic metrics
        self.spot_price_label.setText(f"Nifty: {data['underlying_value']:.2f}")
        self.atm_label.setText(f"ATM Strike: {data['atm_strike']}")
        self.max_pain_label.setText(f"Max Pain: {data['max_pain']}")
        
        # Update PCR
        self.total_ce_oi_label.setText(f"Total CE OI: {data['total_ce_oi']:,}")
        self.total_pe_oi_label.setText(f"Total PE OI: {data['total_pe_oi']:,}")
        self.pcr_label.setText(f"PCR: {data['pcr']:.2f}")
        
        # Update volume
        self.call_vol_label.setText(f"Call Volume: {data['call_vol']:,}")
        self.put_vol_label.setText(f"Put Volume: {data['put_vol']:,}")
        self.net_flow_label.setText(f"Net Flow: {data['net_flow']:,}")
        
        # Update status
        self.status_label.setText("Status: Running")
        self.time_label.setText(f"Last Update: {data['timestamp']}")
        
        # Update summary
        self.update_summary(data)
        
        # Update entry signals
        self.update_entry_signals(data)
        
        # Update historical table
        self.update_historical_table()
        
        # Update strike cards
        self.update_strike_cards(data)

    def update_summary(self, data):
        """Update the market summary"""
        summary = f"=== Market Summary ===\n"
        summary += f"Time: {data['timestamp']}\n"
        summary += f"Nifty: {data['underlying_value']:.2f}\n"
        summary += f"ATM Strike: {data['atm_strike']}\n"
        summary += f"Max Pain: {data['max_pain']}\n\n"
        
        # PCR analysis
        pcr = data['pcr']
        if pcr > 1.5:
            pcr_signal = "Extremely Bullish (PCR > 1.5)"
        elif pcr > 1.2:
            pcr_signal = "Bullish (PCR > 1.2)"
        elif pcr > 0.8:
            pcr_signal = "Neutral (PCR 0.8-1.2)"
        elif pcr > 0.5:
            pcr_signal = "Bearish (PCR 0.5-0.8)"
        else:
            pcr_signal = "Extremely Bearish (PCR < 0.5)"
        
        summary += f"PCR: {pcr:.2f} - {pcr_signal}\n\n"
        
        # Volume analysis
        call_vol = data['call_vol']
        put_vol = data['put_vol']
        net_flow = data['net_flow']
        
        if net_flow > 0:
            vol_signal = "Call Buying Dominant"
        else:
            vol_signal = "Put Buying Dominant"
        
        summary += f"Call Volume: {call_vol:,}\n"
        summary += f"Put Volume: {put_vol:,}\n"
        summary += f"Net Flow: {net_flow:,} - {vol_signal}\n"
        
        self.summary_text.setPlainText(summary)

    def update_entry_signals(self, data):
        """Update the entry signals analysis"""
        signals = "=== Entry Signals ===\n\n"
        
        # Calculate price change if we have historical data
        if len(self.historical_data) >= 2:
            prev_data = self.historical_data[-2]
            price_change = data['underlying_value'] - prev_data['underlying_value']
        else:
            price_change = 0
        
        # Call entry signals
        signals += "Call Buy Opportunities:\n"
        
        # 1. Bullish Divergence (Puts↑ but Nifty↑)
        if (data['put_vol'] > self.historical_data[-2]['put_vol'] if len(self.historical_data) >= 2 else False) and price_change > 0:
            signals += "- BULLISH DIVERGENCE (Puts↑ but Nifty↑)\n"
        
        # 2. Calls Dominant with Price Rise
        if data['net_flow'] > 0 and price_change > 0:
            signals += "- CALLS DOMINANT WITH PRICE RISE\n"
        
        # Put entry signals
        signals += "\nPut Buy Opportunities:\n"
        
        # 1. Bearish Divergence (Calls↑ but Nifty↓)
        if (data['call_vol'] > self.historical_data[-2]['call_vol'] if len(self.historical_data) >= 2 else False) and price_change < 0:
            signals += "- BEARISH DIVERGENCE (Calls↑ but Nifty↓)\n"
        
        # 2. Puts Dominant with Price Fall
        if data['net_flow'] < 0 and price_change < 0:
            signals += "- PUTS DOMINANT WITH PRICE FALL\n"
        
        # Warning signals
        signals += "\nWarning Signals:\n"
        
        # Calls Dominant but Nifty Falling
        if data['net_flow'] > 0 and price_change < 0:
            signals += "- CALLS DOMINANT BUT NIFTY FALLING (Possible Trap)\n"
        
        # Puts Dominant but Nifty Rising
        if data['net_flow'] < 0 and price_change > 0:
            signals += "- PUTS DOMINANT BUT NIFTY RISING (Possible Trap)\n"
        
        self.signals_text.setPlainText(signals)

    def update_historical_table(self):
        """Update the historical entry signals table"""
        self.entry_table.setRowCount(len(self.historical_data))
        
        for i, data in enumerate(self.historical_data):
            # Calculate price change
            if i > 0:
                prev_data = self.historical_data[i-1]
                price_change = data['underlying_value'] - prev_data['underlying_value']
            else:
                price_change = 0
            
            # Determine signal
            signal = ""
            
            # Call signals
            call_conditions = []
            if i > 0:
                if (data['put_vol'] > prev_data['put_vol']) and price_change > 0:
                    call_conditions.append("Bullish Divergence")
                if data['net_flow'] > 0 and price_change > 0:
                    call_conditions.append("Calls Dominant")
            
            # Put signals
            put_conditions = []
            if i > 0:
                if (data['call_vol'] > prev_data['call_vol']) and price_change < 0:
                    put_conditions.append("Bearish Divergence")
                if data['net_flow'] < 0 and price_change < 0:
                    put_conditions.append("Puts Dominant")
            
            if call_conditions:
                signal = "Call Buy: " + ", ".join(call_conditions)
            elif put_conditions:
                signal = "Put Buy: " + ", ".join(put_conditions)
            else:
                signal = "Neutral"
            
            # Add warning conditions
            if i > 0:
                if data['net_flow'] > 0 and price_change < 0:
                    signal += " (Warning: Calls Dominant but Nifty Falling)"
                if data['net_flow'] < 0 and price_change > 0:
                    signal += " (Warning: Puts Dominant but Nifty Rising)"
            
            # Populate table
            self.entry_table.setItem(i, 0, QTableWidgetItem(data['timestamp']))
            self.entry_table.setItem(i, 1, QTableWidgetItem(f"{data['underlying_value']:.2f}"))
            self.entry_table.setItem(i, 2, QTableWidgetItem(f"{price_change:.2f}"))
            self.entry_table.setItem(i, 3, QTableWidgetItem(f"{data['call_vol']:,}"))
            self.entry_table.setItem(i, 4, QTableWidgetItem(f"{data['put_vol']:,}"))
            self.entry_table.setItem(i, 5, QTableWidgetItem(f"{data['net_flow']:,}"))
            self.entry_table.setItem(i, 6, QTableWidgetItem(signal))
            
            # Color code based on signal
            if "Call Buy" in signal:
                for col in range(7):
                    self.entry_table.item(i, col).setBackground(QColor(200, 255, 200))  # Light green
            elif "Put Buy" in signal:
                for col in range(7):
                    self.entry_table.item(i, col).setBackground(QColor(255, 200, 200))  # Light red
            elif "Warning" in signal:
                for col in range(7):
                    self.entry_table.item(i, col).setBackground(QColor(255, 255, 150))  # Light yellow

    def update_strike_cards(self, data):
        """Update the strike cards with option data"""
        if not data.get('raw_data'):
            return
            
        raw_data = data['raw_data']
        current_expiry = raw_data["records"]["expiryDates"][0]
        atm_strike = data['atm_strike']
        
        strikes = [
            atm_strike,       # ATM
            atm_strike + 100, # ATM+100
            atm_strike + 200, # ATM+200
            atm_strike - 100, # ATM-100
            atm_strike - 200  # ATM-200
        ]
        
        for i, strike in enumerate(strikes):
            # Find the option data for this strike
            ce_data = None
            pe_data = None
            
            for item in raw_data["records"]["data"]:
                if item.get("strikePrice") == strike:
                    ce_data = item.get("CE")
                    pe_data = item.get("PE")
                    break
            
            # Update the card
            card = self.strike_cards[i]
            
            if ce_data:
                card["ce_label"].setText(f"CE: {ce_data['lastPrice']:.2f} (ΔOI: {ce_data['changeinOpenInterest']:,})")
            else:
                card["ce_label"].setText("CE: --")
            
            if pe_data:
                card["pe_label"].setText(f"PE: {pe_data['lastPrice']:.2f} (ΔOI: {pe_data['changeinOpenInterest']:,})")
            else:
                card["pe_label"].setText("PE: --")
            
            # Calculate total OI change
            oi_change = 0
            if ce_data:
                oi_change += ce_data['changeinOpenInterest']
            if pe_data:
                oi_change -= pe_data['changeinOpenInterest']
            
            card["oi_label"].setText(f"OI Change: {oi_change:,}")
            
            # Calculate IV (if available)
            iv_text = "IV: "
            if ce_data and pe_data:
                ce_iv = ce_data.get('impliedVolatility', 0)
                pe_iv = pe_data.get('impliedVolatility', 0)
                iv_text += f"CE {ce_iv:.2f}% / PE {pe_iv:.2f}%"
                iv_diff = ce_iv - pe_iv
                
                if iv_diff > 5:
                    iv_text += " (Skew Bullish)"
                elif iv_diff < -5:
                    iv_text += " (Skew Bearish)"
                else:
                    iv_text += " (Skew Neutral)"
            else:
                iv_text += "--"
            
            card["iv_label"].setText(iv_text)

    def closeEvent(self, event):
        """Clean up when closing the application"""
        self.worker.stop()
        self.thread.quit()
        self.thread.wait()
        super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Set dark theme
    app.setStyle("Fusion")
    
    dark_palette = QPalette()
    dark_palette.setColor(QPalette.Window, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.WindowText, Qt.white)
    dark_palette.setColor(QPalette.Base, QColor(25, 25, 25))
    dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ToolTipBase, Qt.white)
    dark_palette.setColor(QPalette.ToolTipText, Qt.white)
    dark_palette.setColor(QPalette.Text, Qt.white)
    dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ButtonText, Qt.white)
    dark_palette.setColor(QPalette.BrightText, Qt.red)
    dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.HighlightedText, Qt.black)
    
    app.setPalette(dark_palette)
    
    window = OptionMonitor()
    window.show()
    sys.exit(app.exec())