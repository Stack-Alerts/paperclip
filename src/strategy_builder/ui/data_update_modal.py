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
from src.data_manager.unified_manager import UnifiedDataManager


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
                source='binance'  # Force Binance only!
            )
            
            self.progress.emit(60, 100, f"Downloaded {len(bars_15m)} bars (15min)")
            
            # Download 1h bars (secondary timeframe)
            self.progress.emit(70, 100, "Downloading 1h bars from Binance...")
            bars_1h = self.manager.get_bars(
                timeframe='1h',
                start_date=self.start_date,
                end_date=self.end_date,
                source='binance'
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
        
        # Much bigger to avoid any scrolling
        self.setMinimumWidth(1100)
        self.setMinimumHeight(750)
        self.resize(1100, 750)
        
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
        self.details_text.setMinimumHeight(450)  # Extra tall - definitely no scrolling
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
        """Check for gaps between LakeAPI and current time"""
        try:
            # Get available ranges
            ranges = self.manager.get_available_date_range('15m')
            
            lakeapi_range = ranges.get('lakeapi_range')
            
            if lakeapi_range and lakeapi_range[0]:
                # LakeAPI data exists
                self.lakeapi_end = lakeapi_range[1]
                self.current_time = datetime.now()
                
                # Calculate gap
                self.gap_days = (self.current_time - self.lakeapi_end).days
                
                if self.gap_days > 1:
                    # Gap exists - offer update
                    self.status_label.setText(
                        f"⚠️ Data Gap Detected: {self.gap_days} days missing"
                    )
                    self.status_label.setStyleSheet("color: #FFA500; font-weight: bold;")
                    
                    self.details_text.setText(
                        f"Historical Data (LakeAPI):\n"
                        f"  Available through: {self.lakeapi_end.strftime('%Y-%m-%d')}\n\n"
                        f"Current Time:\n"
                        f"  {self.current_time.strftime('%Y-%m-%d %H:%M')}\n\n"
                        f"Missing Gap:\n"
                        f"  {self.gap_days} days ({self.gap_days * 96} bars @ 15min)\n\n"
                        f"Recommendation:\n"
                        f"  Click 'Update Data' to download missing data from Binance.\n"
                        f"  This will fill the gap safely without touching your LakeAPI data.\n\n"
                        f"Note: Download will be saved to data/binance/ directory."
                    )
                    
                    self.update_button.setEnabled(True)
                else:
                    # No significant gap
                    self.status_label.setText("✅ Data is up to date!")
                    self.status_label.setStyleSheet("color: #4ADE80; font-weight: bold;")
                    
                    self.details_text.setText(
                        f"Historical Data (LakeAPI):\n"
                        f"  Available through: {self.lakeapi_end.strftime('%Y-%m-%d')}\n\n"
                        f"Current Time:\n"
                        f"  {self.current_time.strftime('%Y-%m-%d %H:%M')}\n\n"
                        f"Gap: {self.gap_days} day(s) (acceptable)\n\n"
                        f"Your data is current. Click 'Continue' to proceed."
                    )
                    
                    self.skip_button.setText("Continue")
            else:
                # No LakeAPI data found
                self.status_label.setText("⚠️ No historical data found")
                self.status_label.setStyleSheet("color: #EF4444; font-weight: bold;")
                
                self.details_text.setText(
                    f"No LakeAPI data detected in: data/lakeapi/\n\n"
                    f"You can either:\n"
                    f"1. Continue without historical data (limited functionality)\n"
                    f"2. Import LakeAPI data first\n\n"
                    f"Note: Recent data can be downloaded from Binance,\n"
                    f"but for full historical analysis, LakeAPI data is recommended."
                )
                
                self.skip_button.setText("Continue Anyway")
        
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
