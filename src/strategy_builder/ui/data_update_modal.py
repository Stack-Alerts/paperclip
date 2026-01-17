"""
Data Update Modal - Strategy Builder Startup Check

Shows on Strategy Builder launch to:
- Check for data gaps (LakeAPI cutoff → current)
- Offer to download missing data from Binance
- Display progress during update
- Safe: Only downloads to data/binance/ (never touches LakeAPI!)

Author: Strategy Builder Team
Date: 2026-01-17
"""

from datetime import datetime, timedelta
from typing import Optional
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QTextEdit, QGroupBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont

# Import UnifiedDataManager - THE ONLY DATA SOURCE!
from src.data_manager.unified_manager import UnifiedDataManager, DataSource


class DataUpdateThread(QThread):
    """
    Background thread for downloading data from Binance
    
    Signals:
        progress: (current, total, message) - Progress updates
        finished: (success, message) - Completion status
    """
    
    progress = pyqtSignal(int, int, str)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, start_date: datetime, end_date: datetime):
        super().__init__()
        self.start_date = start_date
        self.end_date = end_date
        self.manager = UnifiedDataManager()
    
    def run(self):
        """Download missing data from Binance"""
        try:
            self.progress.emit(0, 100, "Initializing Binance connection...")
            
            # Download 15min bars (primary timeframe)
            self.progress.emit(20, 100, "Downloading 15min bars from Binance...")
            bars_15m = self.manager.get_bars(
                timeframe='15m',
                start_date=self.start_date,
                end_date=self.end_date,
                source=DataSource.BINANCE  # Force Binance only!
            )
            
            self.progress.emit(60, 100, f"Downloaded {len(bars_15m)} bars (15min)")
            
            # Download 1h bars (secondary timeframe)
            self.progress.emit(70, 100, "Downloading 1h bars from Binance...")
            bars_1h = self.manager.get_bars(
                timeframe='1h',
                start_date=self.start_date,
                end_date=self.end_date,
                source=DataSource.BINANCE
            )
            
            self.progress.emit(90, 100, f"Downloaded {len(bars_1h)} bars (1h)")
            
            # Success!
            self.progress.emit(100, 100, "Download complete!")
            self.finished.emit(
                True,
                f"✅ Successfully updated!\n\n"
                f"15min bars: {len(bars_15m)}\n"
                f"1h bars: {len(bars_1h)}\n\n"
                f"Data saved to: data/binance/"
            )
            
        except Exception as e:
            self.finished.emit(
                False,
                f"❌ Download failed:\n\n{str(e)}\n\n"
                f"You can try again later or continue without update."
            )


class DataUpdateModal(QDialog):
    """
    Modal dialog for checking and updating data
    
    Shown on Strategy Builder startup to ensure data is current
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.manager = UnifiedDataManager()
        self.update_thread: Optional[DataUpdateThread] = None
        self.gap_days = 0
        self.lakeapi_end: Optional[datetime] = None
        self.current_time: Optional[datetime] = None
        
        self._init_ui()
        self._check_data_gap()
    
    def _init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Data Update Check")
        
        # Make dialog moveable and independent (30% bigger)
        # Use Window flag instead of Dialog to allow dragging
        self.setWindowFlags(Qt.Window | Qt.WindowTitleHint | Qt.WindowCloseButtonHint | Qt.WindowStaysOnTopHint)
        self.setModal(True)  # Keep modal behavior but allow dragging
        
        # MASSIVE to avoid scrolling - institutional grade
        self.setMinimumWidth(1400)
        self.setMinimumHeight(1000)
        self.resize(1400, 1000)
        
        # Dark theme
        self.setStyleSheet("""
            QDialog {
                background-color: #1E2128;
                color: #E8EAED;
            }
            QLabel {
                color: #E8EAED;
                background: transparent;
            }
            QGroupBox {
                background-color: #2A2F3A;
                border: 1px solid #3C4149;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 12px;
                color: #E8EAED;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QTextEdit {
                background-color: #2A2F3A;
                border: 1px solid #3C4149;
                border-radius: 4px;
                padding: 8px;
                color: #BDC1C6;
            }
            QProgressBar {
                background-color: #2A2F3A;
                border: 1px solid #3C4149;
                border-radius: 4px;
                text-align: center;
                color: #E8EAED;
            }
            QProgressBar::chunk {
                background-color: #2070FF;
                border-radius: 3px;
            }
            QPushButton {
                background-color: #2070FF;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 4px;
                border: none;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #1860EF;
            }
            QPushButton:pressed {
                background-color: #1550DF;
            }
            QPushButton:disabled {
                background-color: #555555;
                color: #888888;
            }
            QPushButton#skipButton {
                background-color: #555555;
            }
            QPushButton#skipButton:hover {
                background-color: #666666;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header = QLabel("📊 Historical Data Update Check")
        header_font = QFont()
        header_font.setBold(True)
        header_font.setPointSize(12)
        header.setFont(header_font)
        header.setStyleSheet("color: #00A3BF; padding: 10px;")
        layout.addWidget(header)
        
        # Status group
        status_group = QGroupBox("Data Status")
        status_layout = QVBoxLayout()
        status_layout.setSpacing(10)
        
        self.status_label = QLabel("Checking data availability...")
        self.status_label.setWordWrap(True)
        status_layout.addWidget(self.status_label)
        
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        # Details text
        details_group = QGroupBox("Details")
        details_layout = QVBoxLayout()
        
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)  
        self.details_text.setMinimumHeight(700)  # EXTRA tall - ZERO scrolling
        details_layout.addWidget(self.details_text)
        
        details_group.setLayout(details_layout)
        layout.addWidget(details_group)
        
        # Progress bar (initially hidden)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Progress message
        self.progress_label = QLabel("")
        self.progress_label.setVisible(False)
        self.progress_label.setStyleSheet("color: #00A3BF; font-style: italic;")
        layout.addWidget(self.progress_label)
        
        layout.addStretch()
        
        # Buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        self.skip_button = QPushButton("Skip for Now")
        self.skip_button.setObjectName("skipButton")
        self.skip_button.clicked.connect(self.reject)
        buttons_layout.addWidget(self.skip_button)
        
        self.update_button = QPushButton("Update Data")
        self.update_button.clicked.connect(self._start_update)
        self.update_button.setEnabled(False)
        buttons_layout.addWidget(self.update_button)
        
        self.close_button = QPushButton("Continue")
        self.close_button.clicked.connect(self.accept)
        self.close_button.setVisible(False)
        buttons_layout.addWidget(self.close_button)
        
        layout.addLayout(buttons_layout)
        
        self.setLayout(layout)
    
    def _check_data_gap(self):
        """Check for gaps across ALL data types"""
        try:
            # Get status for ALL data types
            all_status = self.manager.get_all_data_types_status()
            
            # Build comprehensive report
            any_gaps = False
            max_gap = 0
            report_lines = []
            
            self.current_time = datetime.now()
            report_lines.append("📊 DATA TYPE STATUS:\n")
            
            for data_type, info in all_status.items():
                if info['status'] == 'complete':
                    report_lines.append(f"  ✅ {data_type.upper()}: Complete")
                    if info['start'] and info['end']:
                        report_lines.append(f"     Range: {info['start'].strftime('%Y-%m-%d')} → {info['end'].strftime('%Y-%m-%d')}\n")
                elif info['status'] == 'gap':
                    any_gaps = True
                    max_gap = max(max_gap, info['gap_days'])
                    self.lakeapi_end = info['end']  # Store for download
                    self.gap_days = info['gap_days']
                    report_lines.append(f"  ❌ {data_type.upper()}: GAP DETECTED")
                    if info['start'] and info['end']:
                        report_lines.append(f"     Range: {info['start'].strftime('%Y-%m-%d')} → {info['end'].strftime('%Y-%m-%d %H:%M')}")
                    
                    # Show precise gap for futures trading
                    gap_minutes = info.get('gap_minutes', info['gap_days'] * 1440)
                    if gap_minutes < 60:
                        report_lines.append(f"     Missing: {gap_minutes} minutes ({int(gap_minutes/15)} candles @ 15min)\n")
                    elif gap_minutes < 1440:
                        hours = int(gap_minutes / 60)
                        mins = int(gap_minutes % 60)
                        report_lines.append(f"     Missing: {hours}h {mins}m ({int(gap_minutes/15)} candles @ 15min)\n")
                    else:
                        report_lines.append(f"     Missing: {info['gap_days']} days ({int(gap_minutes/15)} candles @ 15min)\n")
                elif info['status'] == 'missing':
                    any_gaps = True
                    max_gap = 999
                    report_lines.append(f"  ❌ {data_type.upper()}: MISSING")
                    report_lines.append(f"     No data found in data/raw/{data_type}/\n")
                else:
                    report_lines.append(f"  ⚠️  {data_type.upper()}: ERROR")
                    if 'error' in info:
                        report_lines.append(f"     {info['error']}\n")
            
            report_lines.append(f"Current Time: {self.current_time.strftime('%Y-%m-%d %H:%M')}\n")
            
            if any_gaps:
                self.status_label.setText(
                    f"⚠️ DATA GAPS DETECTED: Up to {max_gap} days MISSING"
                )
                self.status_label.setStyleSheet("color: #EF4444; font-weight: bold;")
                
                report_lines.append("❌ CRITICAL: Building blocks need ALL data types!")
                report_lines.append("   - Trade management needs funding rates")
                report_lines.append("   - Building blocks need liquidations")
                report_lines.append("   - Advanced blocks need orderbook\n")
                report_lines.append("Click 'Update Data' to fill ALL gaps.")
                
                self.details_text.setText("\n".join(report_lines))
                self.update_button.setEnabled(True)
            else:
                self.status_label.setText("✅ ALL DATA COMPLETE - 100% ACCURATE")
                self.status_label.setStyleSheet("color: #4ADE80; font-weight: bold;")
                
                report_lines.append("✅ PERFECT: All data types complete!")
                report_lines.append("   Building blocks have full data access")
                report_lines.append("   Trade Manager ready for deployment")
                
                self.details_text.setText("\n".join(report_lines))
                self.skip_button.setText("Continue")
        
        except Exception as e:
            self.status_label.setText("❌ Error checking data")
            self.status_label.setStyleSheet("color: #EF4444; font-weight: bold;")
            
            self.details_text.setText(
                f"Error occurred while checking data:\n\n"
                f"{str(e)}\n\n"
                f"You can skip this check and continue."
            )
    
    def _start_update(self):
        """Start the data update process"""
        if not self.lakeapi_end or not self.current_time:
            return
        
        # Disable buttons
        self.update_button.setEnabled(False)
        self.skip_button.setEnabled(False)
        
        # Show progress
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_label.setVisible(True)
        self.progress_label.setText("Starting download...")
        
        # Create and start update thread
        self.update_thread = DataUpdateThread(
            self.lakeapi_end,
            self.current_time
        )
        
        # Connect signals
        self.update_thread.progress.connect(self._on_progress)
        self.update_thread.finished.connect(self._on_finished)
        
        # Start download
        self.update_thread.start()
    
    def _on_progress(self, current: int, total: int, message: str):
        """Handle progress updates"""
        self.progress_bar.setValue(current)
        self.progress_label.setText(message)
    
    def _on_finished(self, success: bool, message: str):
        """Handle completion"""
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        
        if success:
            self.status_label.setText("✅ Update Complete!")
            self.status_label.setStyleSheet("color: #4ADE80; font-weight: bold;")
        else:
            self.status_label.setText("❌ Update Failed")
            self.status_label.setStyleSheet("color: #EF4444; font-weight: bold;")
        
        self.details_text.setText(message)
        
        # Show close button
        self.update_button.setVisible(False)
        self.skip_button.setVisible(False)
        self.close_button.setVisible(True)
