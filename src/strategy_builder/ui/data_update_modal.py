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
# Import centralized styles
from src.strategy_builder.ui.styles import (
    get_main_stylesheet, get_panel_title_stylesheet, 
    get_label_style, get_status_label_style,
    get_primary_button_stylesheet, get_secondary_button_stylesheet
)


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
        """Download missing data from Binance AND SAVE TO DISK"""
        try:
            from pathlib import Path
            
            self.progress.emit(0, 100, "Initializing Binance connection...")
            
            # Download 15min bars (primary timeframe)
            self.progress.emit(20, 100, "Downloading 15min bars from Binance...")
            bars_15m = self.manager.get_bars(
                timeframe='15m',
                start_date=self.start_date,
                end_date=self.end_date,
                source=DataSource.BINANCE  # Force Binance only!
            )
            
            self.progress.emit(40, 100, f"Downloaded {len(bars_15m)} bars (15min)")
            
            # INSTITUTIONAL: SAVE TO DISK!
            self.progress.emit(45, 100, "Saving 15min bars to disk...")
            saved_files_15m = self._save_bars_to_disk(bars_15m, '15m')
            
            # Download 1h bars (secondary timeframe)
            self.progress.emit(60, 100, "Downloading 1h bars from Binance...")
            bars_1h = self.manager.get_bars(
                timeframe='1h',
                start_date=self.start_date,
                end_date=self.end_date,
                source=DataSource.BINANCE
            )
            
            self.progress.emit(80, 100, f"Downloaded {len(bars_1h)} bars (1h)")
            
            # INSTITUTIONAL: SAVE TO DISK!
            self.progress.emit(85, 100, "Saving 1h bars to disk...")
            saved_files_1h = self._save_bars_to_disk(bars_1h, '1h')
            
            # Success!
            self.progress.emit(100, 100, "Download complete!")
            self.finished.emit(
                True,
                f"✅ Successfully updated!\n\n"
                f"15min bars: {len(bars_15m)} ({len(saved_files_15m)} files saved)\n"
                f"1h bars: {len(bars_1h)} ({len(saved_files_1h)} files saved)\n\n"
                f"Files saved to: data/binance/\n"
                f"Latest timestamp: {bars_15m['timestamp'].iloc[-1]}"
            )
            
        except Exception as e:
            self.finished.emit(
                False,
                f"❌ Download failed:\n\n{str(e)}\n\n"
                f"You can try again later or continue without update."
            )
    
    def _save_bars_to_disk(self, bars, timeframe: str) -> list:
        """INSTITUTIONAL: Merge new bars with existing data"""
        from pathlib import Path
        import pandas as pd
        
        if len(bars) == 0:
            return []
        
        saved_files = []
        base_dir = Path("data/binance")
        base_dir.mkdir(parents=True, exist_ok=True)
        
        # Group bars by month
        bars['month'] = pd.to_datetime(bars['timestamp']).dt.to_period('M')
        
        for month, month_data in bars.groupby('month'):
            # Create month directory (e.g., 2026-01)
            month_dir = base_dir / str(month)
            month_dir.mkdir(exist_ok=True)
            
            # Filename format: BTCUSDT_PERP_15m_2026-01.parquet (month level, not day!)
            filename = f"BTCUSDT_PERP_{timeframe}_{month}.parquet"
            filepath = month_dir / filename
            
            month_data_clean = month_data.drop(columns=['month'])
            
            # INSTITUTIONAL: Merge with existing data if file exists
            if filepath.exists():
                try:
                    # Read existing data
                    existing_data = pd.read_parquet(filepath)
                    
                    # Combine old + new
                    combined = pd.concat([existing_data, month_data_clean], ignore_index=True)
                    
                    # Remove duplicates (keep latest)
                    combined = combined.sort_values('timestamp').drop_duplicates(subset=['timestamp'], keep='last')
                    
                    # Save merged data
                    combined.to_parquet(filepath, index=False)
                    print(f"   💾 Updated: {filepath} ({len(existing_data)} → {len(combined)} bars, +{len(combined)-len(existing_data)} new)")
                except Exception as e:
                    print(f"   ⚠️  Could not merge, overwriting: {e}")
                    month_data_clean.to_parquet(filepath, index=False)
                    print(f"   💾 Saved: {filepath} ({len(month_data_clean)} bars)")
            else:
                # New file - just save
                month_data_clean.to_parquet(filepath, index=False)
                print(f"   💾 Created: {filepath} ({len(month_data_clean)} bars)")
            
            saved_files.append(str(filepath))
        
        return saved_files


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
        self.setWindowTitle("BTC Engine v3 - Data Update Check")
        
        # Make dialog moveable and independent (30% bigger)
        # Use Window flag instead of Dialog to allow dragging
        self.setWindowFlags(Qt.Window | Qt.WindowTitleHint | Qt.WindowCloseButtonHint | Qt.WindowStaysOnTopHint)
        self.setModal(True)  # Keep modal behavior but allow dragging
        
        # MASSIVE to avoid scrolling - institutional grade (75px taller)
        self.setMinimumWidth(1400)
        self.setMinimumHeight(1075)
        self.resize(1400, 1075)
        
        # Apply centralized dark theme stylesheet
        self.setStyleSheet(get_main_stylesheet())
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header with centralized styling
        header = QLabel("📊 Historical Data Update Check")
        header_font = QFont()
        header_font.setBold(True)
        header_font.setPointSize(14)
        header.setFont(header_font)
        header.setStyleSheet(get_panel_title_stylesheet())
        layout.addWidget(header)
        
        # Status group
        status_group = QGroupBox("Data Status")
        status_layout = QVBoxLayout()
        status_layout.setSpacing(10)
        
        self.status_label = QLabel("Checking data availability...")
        self.status_label.setWordWrap(True)
        self.status_label.setAlignment(Qt.AlignCenter)  # Center text vertically and horizontally
        self.status_label.setMinimumHeight(40)  # Compact height with centered text
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
        
        # Progress message with centralized styling
        self.progress_label = QLabel("")
        self.progress_label.setVisible(False)
        self.progress_label.setStyleSheet(get_label_style('info') + " font-style: italic;")
        layout.addWidget(self.progress_label)
        
        layout.addStretch()
        
        # Buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        self.skip_button = QPushButton("⏭️ Skip for Now")
        self.skip_button.setMinimumWidth(150)
        self.skip_button.setMinimumHeight(40)
        self.skip_button.setStyleSheet(get_secondary_button_stylesheet())
        self.skip_button.clicked.connect(self.reject)
        buttons_layout.addWidget(self.skip_button)
        
        self.update_button = QPushButton("📥 Update Data")
        self.update_button.setMinimumWidth(150)
        self.update_button.setMinimumHeight(40)
        self.update_button.setStyleSheet(get_primary_button_stylesheet())
        self.update_button.clicked.connect(self._start_update)
        self.update_button.setEnabled(False)
        buttons_layout.addWidget(self.update_button)
        
        self.close_button = QPushButton("✅ Continue")
        self.close_button.setMinimumWidth(150)
        self.close_button.setMinimumHeight(40)
        self.close_button.setStyleSheet(get_primary_button_stylesheet())
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
                self.status_label.setStyleSheet(get_status_label_style('error'))
                
                report_lines.append("❌ CRITICAL: Building blocks need ALL data types!")
                report_lines.append("   - Trade management needs funding rates")
                report_lines.append("   - Building blocks need liquidations")
                report_lines.append("   - Advanced blocks need orderbook\n")
                report_lines.append("Click 'Update Data' to fill ALL gaps.")
                
                self.details_text.setText("\n".join(report_lines))
                self.update_button.setEnabled(True)
            else:
                self.status_label.setText("✅ ALL DATA COMPLETE - 100% ACCURATE")
                self.status_label.setStyleSheet(get_status_label_style('success'))
                
                report_lines.append("✅ PERFECT: All data types complete!")
                report_lines.append("   Building blocks have full data access")
                report_lines.append("   Trade Manager ready for deployment")
                
                self.details_text.setText("\n".join(report_lines))
                self.skip_button.setText("Continue")
        
        except Exception as e:
            self.status_label.setText("❌ Error checking data")
            self.status_label.setStyleSheet(get_status_label_style('error'))
            
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
            self.status_label.setStyleSheet(get_status_label_style('success'))
        else:
            self.status_label.setText("❌ Update Failed")
            self.status_label.setStyleSheet(get_status_label_style('error'))
        
        self.details_text.setText(message)
        
        # Show close button
        self.update_button.setVisible(False)
        self.skip_button.setVisible(False)
        self.close_button.setVisible(True)
