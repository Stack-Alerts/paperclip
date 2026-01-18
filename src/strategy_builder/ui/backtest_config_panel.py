"""
Backtest Configuration Panel - Strategy Builder UI Component

Comprehensive backtest configuration with:
- Lookback days and training window control
- Mode 1 (historical) / Mode 2 (live replay) selection
- TP/SL configuration integration
- Live progress tracking with candle/trade counters
- TP/SL adjustment tracking (per type)
- Pause/Resume/Stop controls

NAUTILUS EXPERT: Institutional-grade backtest execution with real-time monitoring

Author: Strategy Builder Team
Date: 2026-01-17
"""

from typing import Optional
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox,
    QRadioButton, QButtonGroup, QComboBox, QProgressBar,
    QPushButton, QGroupBox, QTextEdit, QTabWidget
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont


class BacktestWorker(QThread):
    """Worker thread for running backtests without blocking UI"""
    
    # Signals
    progress_updated = pyqtSignal(int, int, str)  # current, total, message
    backtest_finished = pyqtSignal(bool, dict)  # success, results
    
    def __init__(self, orchestrator, config: dict):
        super().__init__()
        self.orchestrator = orchestrator
        self.config = config
        self.is_paused = False
        self.should_stop = False
    
    def run(self):
        """Run backtest in background thread"""
        try:
            # TODO: Implement actual backtest execution
            # This is a placeholder that simulates backtest progress
            
            total_candles = 14040  # Example from spec
            
            for i in range(0, total_candles, 100):
                if self.should_stop:
                    self.backtest_finished.emit(False, {'error': 'Stopped by user'})
                    return
                
                # Wait while paused
                while self.is_paused and not self.should_stop:
                    self.msleep(100)
                
                # Emit progress
                progress_msg = f"Processing candles {i}/{total_candles}"
                self.progress_updated.emit(i, total_candles, progress_msg)
                
                # Simulate work
                self.msleep(50)
            
            # Emit completion
            results = {
                'total_candles': total_candles,
                'trades': 24,
                'tp_adjustments': {'TP1': 12, 'TP2': 18, 'TP3': 9, 'SL': 8}
            }
            self.backtest_finished.emit(True, results)
            
        except Exception as e:
            self.backtest_finished.emit(False, {'error': str(e)})
    
    def pause(self):
        """Pause the backtest"""
        self.is_paused = True
    
    def resume(self):
        """Resume the backtest"""
        self.is_paused = False
    
    def stop(self):
        """Stop the backtest"""
        self.should_stop = True


class BacktestConfigPanel(QWidget):
    """
    Backtest Configuration Panel
    
    Provides comprehensive backtest configuration and live execution monitoring.
    """
    
    def __init__(self, orchestrator, parent=None):
        super().__init__(parent)
        self.orchestrator = orchestrator
        self.worker: Optional[BacktestWorker] = None
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the user interface"""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create tab widget with stepper-like styling
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #3C4149;
                background: #15191E;
                margin-top: 10px;
            }
            QTabBar::tab {
                background: #374151;
                color: #9CA3AF;
                padding: 15px 30px;
                margin-right: 4px;
                margin-top: 8px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-size: 14px;
                font-weight: bold;
                min-width: 120px;
            }
            QTabBar::tab:selected {
                background: #2070FF;
                color: #FFFFFF;
            }
            QTabBar::tab:hover:!selected {
                background: #4B5563;
                color: #D1D5DB;
            }
        """)
        
        # Tab 1: Configuration (existing content)
        config_tab = self._create_config_tab()
        self.tab_widget.addTab(config_tab, "⚙️ Config")
        
        # Tab 2: Live Output (placeholder)
        output_tab = self._create_placeholder_tab("📊 Live Output", "Real-time backtest output will appear here")
        self.tab_widget.addTab(output_tab, "📊 Live Output")
        
        # Tab 3: Trades (placeholder)
        trades_tab = self._create_placeholder_tab("📋 Trades", "Trade history table will appear here")
        self.tab_widget.addTab(trades_tab, "📋 Trades")
        
        # Tab 4: Metrics (placeholder)
        metrics_tab = self._create_placeholder_tab("📈 Metrics", "Key metrics comparison will appear here")
        self.tab_widget.addTab(metrics_tab, "📈 Metrics")
        
        # Tab 5: Compare (placeholder)
        compare_tab = self._create_placeholder_tab("🔄 Compare", "Configuration comparison will appear here")
        self.tab_widget.addTab(compare_tab, "🔄 Compare")
        
        main_layout.addWidget(self.tab_widget)
        self.setLayout(main_layout)
    
    def _create_config_tab(self) -> QWidget:
        """Create configuration tab (original content)"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Title
        title = QLabel("⚙️ Backtest Configuration")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)
        
        # Configuration Group
        config_group = self._create_config_group()
        layout.addWidget(config_group)
        
        # Progress Group
        progress_group = self._create_progress_group()
        layout.addWidget(progress_group)
        
        # Control Buttons
        control_layout = self._create_control_buttons()
        layout.addLayout(control_layout)
        
        # Results Display
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setMaximumHeight(150)
        self.results_text.setPlaceholderText("Backtest results will appear here...")
        layout.addWidget(QLabel("📊 Results:"))
        layout.addWidget(self.results_text)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def _create_placeholder_tab(self, title: str, message: str) -> QWidget:
        """Create a placeholder tab for future implementation"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title_label = QLabel(title)
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # Coming soon message
        msg_label = QLabel(f"{message}\n\n🚧 Coming Soon 🚧")
        msg_label.setAlignment(Qt.AlignCenter)
        msg_label.setStyleSheet("color: #9AA0A6; font-size: 14px; padding: 20px;")
        layout.addWidget(msg_label)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def _create_config_group(self) -> QGroupBox:
        """Create configuration controls group"""
        group = QGroupBox("Configuration")
        
        # Style group and radio buttons
        group.setStyleSheet("""
            QRadioButton {
                background: transparent;
                color: #9CA3AF;
                padding: 5px;
                font-size: 13px;
            }
            QRadioButton:checked {
                color: #2070FF;
                font-weight: bold;
            }
            QRadioButton::indicator {
                width: 18px;
                height: 18px;
                border-radius: 9px;
                border: 2px solid #6B7280;
                background: transparent;
            }
            QRadioButton::indicator:checked {
                border-color: #2070FF;
                background: #2070FF;
            }
            QRadioButton::indicator:checked:after {
                content: '';
                width: 8px;
                height: 8px;
                border-radius: 4px;
                background: white;
            }
        """)
        
        layout = QVBoxLayout()
        
        # Lookback Days
        lookback_layout = QHBoxLayout()
        lookback_layout.addWidget(QLabel("Lookback Days:"))
        self.lookback_spin = QSpinBox()
        self.lookback_spin.setRange(1, 365)
        self.lookback_spin.setValue(180)
        self.lookback_spin.setSuffix(" days")
        self.lookback_spin.setToolTip("Number of days of historical data to analyze")
        lookback_layout.addWidget(self.lookback_spin)
        lookback_layout.addStretch()
        layout.addLayout(lookback_layout)
        
        # Training Window
        training_layout = QHBoxLayout()
        training_layout.addWidget(QLabel("Training Window:"))
        self.training_spin = QSpinBox()
        self.training_spin.setRange(1, 90)
        self.training_spin.setValue(30)
        self.training_spin.setSuffix(" days")
        self.training_spin.setToolTip("Size of rolling training window")
        training_layout.addWidget(self.training_spin)
        training_layout.addStretch()
        layout.addLayout(training_layout)
        
        # Test Mode
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Test Mode:"))
        self.mode_group = QButtonGroup()
        self.mode1_radio = QRadioButton("Mode 1 (Historical)")
        self.mode2_radio = QRadioButton("Mode 2 (Live Replay)")
        self.mode1_radio.setChecked(True)
        self.mode1_radio.setToolTip("Standard historical backtest")
        self.mode2_radio.setToolTip("Real-time replay simulation")
        self.mode_group.addButton(self.mode1_radio, 1)
        self.mode_group.addButton(self.mode2_radio, 2)
        mode_layout.addWidget(self.mode1_radio)
        mode_layout.addWidget(self.mode2_radio)
        mode_layout.addStretch()
        layout.addLayout(mode_layout)
        
        # TP/SL Configuration
        tpsl_layout = QHBoxLayout()
        tpsl_layout.addWidget(QLabel("TP/SL Config:"))
        self.tpsl_combo = QComboBox()
        self.tpsl_combo.addItems(["Fibonacci", "Hybrid", "Fixed"])
        self.tpsl_combo.setToolTip("Take profit / stop loss calculation method")
        tpsl_layout.addWidget(self.tpsl_combo)
        tpsl_layout.addStretch()
        layout.addLayout(tpsl_layout)
        
        # Stop Loss Mode
        sl_layout = QHBoxLayout()
        sl_layout.addWidget(QLabel("Stop Loss:"))
        self.sl_combo = QComboBox()
        self.sl_combo.addItems(["Adaptive v2.0", "Fixed"])
        self.sl_combo.setToolTip("Stop loss adjustment method")
        sl_layout.addWidget(self.sl_combo)
        sl_layout.addStretch()
        layout.addLayout(sl_layout)
        
        group.setLayout(layout)
        return group
    
    def _create_progress_group(self) -> QGroupBox:
        """Create progress monitoring group"""
        group = QGroupBox("Progress")
        layout = QVBoxLayout()
        
        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # Stats Grid
        stats_layout = QHBoxLayout()
        
        # Candles
        candles_layout = QVBoxLayout()
        candles_layout.addWidget(QLabel("Candles:"))
        self.candles_label = QLabel("0 / 0")
        self.candles_label.setAlignment(Qt.AlignCenter)
        self.candles_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        candles_layout.addWidget(self.candles_label)
        stats_layout.addLayout(candles_layout)
        
        # Trades
        trades_layout = QVBoxLayout()
        trades_layout.addWidget(QLabel("Trades:"))
        self.trades_label = QLabel("0")
        self.trades_label.setAlignment(Qt.AlignCenter)
        self.trades_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        trades_layout.addWidget(self.trades_label)
        stats_layout.addLayout(trades_layout)
        
        # TP/SL Adjustments
        adj_layout = QVBoxLayout()
        adj_layout.addWidget(QLabel("TP/SL Adjustments:"))
        self.adjustments_label = QLabel("0")
        self.adjustments_label.setAlignment(Qt.AlignCenter)
        self.adjustments_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        adj_layout.addWidget(self.adjustments_label)
        stats_layout.addLayout(adj_layout)
        
        layout.addLayout(stats_layout)
        
        # Adjustment Breakdown
        self.breakdown_label = QLabel("(TP1: 0, TP2: 0, TP3: 0, SL: 0)")
        self.breakdown_label.setAlignment(Qt.AlignCenter)
        self.breakdown_label.setStyleSheet("color: #9AA0A6;")
        layout.addWidget(self.breakdown_label)
        
        group.setLayout(layout)
        return group
    
    def _create_control_buttons(self) -> QHBoxLayout:
        """Create control button layout"""
        layout = QHBoxLayout()
        
        # Run Button
        self.run_btn = QPushButton("▶️ Run Test")
        self.run_btn.clicked.connect(self._on_run_clicked)
        self.run_btn.setStyleSheet("""
            QPushButton {
                background-color: #2070FF;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #1557CC;
            }
            QPushButton:disabled {
                background-color: #3C4149;
                color: #6B7280;
            }
        """)
        layout.addWidget(self.run_btn)
        
        # Pause Button
        self.pause_btn = QPushButton("⏸️ Pause")
        self.pause_btn.clicked.connect(self._on_pause_clicked)
        self.pause_btn.setEnabled(False)
        layout.addWidget(self.pause_btn)
        
        # Stop Button
        self.stop_btn = QPushButton("⏹️ Stop")
        self.stop_btn.clicked.connect(self._on_stop_clicked)
        self.stop_btn.setEnabled(False)
        layout.addWidget(self.stop_btn)
        
        layout.addStretch()
        
        # View Results Button
        self.results_btn = QPushButton("📈 View Live Results")
        self.results_btn.setEnabled(False)
        layout.addWidget(self.results_btn)
        
        return layout
    
    def _on_run_clicked(self):
        """Handle run button click"""
        # Validate strategy
        validation = self.orchestrator.validate_strategy()
        if not validation.success:
            self.results_text.setText(f"❌ Strategy validation failed:\n{validation.message}")
            return
        
        # Get configuration
        config = {
            'lookback_days': self.lookback_spin.value(),
            'training_window': self.training_spin.value(),
            'mode': self.mode_group.checkedId(),
            'tpsl_mode': self.tpsl_combo.currentText(),
            'sl_mode': self.sl_combo.currentText()
        }
        
        # Create and start worker
        self.worker = BacktestWorker(self.orchestrator, config)
        self.worker.progress_updated.connect(self._on_progress_updated)
        self.worker.backtest_finished.connect(self._on_backtest_finished)
        self.worker.start()
        
        # Update UI state
        self.run_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)
        self.results_btn.setEnabled(True)
        
        self.results_text.setText("🔄 Backtest started...\n")
    
    def _on_pause_clicked(self):
        """Handle pause button click"""
        if self.worker and self.worker.isRunning():
            if self.worker.is_paused:
                self.worker.resume()
                self.pause_btn.setText("⏸️ Pause")
                self.results_text.append("▶️ Resumed")
            else:
                self.worker.pause()
                self.pause_btn.setText("▶️ Resume")
                self.results_text.append("⏸️ Paused")
    
    def _on_stop_clicked(self):
        """Handle stop button click"""
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.results_text.append("⏹️ Stopping...")
    
    def _on_progress_updated(self, current: int, total: int, message: str):
        """Handle progress update from worker"""
        progress_pct = int((current / total) * 100) if total > 0 else 0
        self.progress_bar.setValue(progress_pct)
        self.candles_label.setText(f"{current:,} / {total:,}")
    
    def _on_backtest_finished(self, success: bool, results: dict):
        """Handle backtest completion"""
        # Update UI state
        self.run_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.pause_btn.setText("⏸️ Pause")
        
        if success:
            # Update displays
            self.trades_label.setText(str(results.get('trades', 0)))
            
            tp_adj = results.get('tp_adjustments', {})
            total_adj = sum(tp_adj.values())
            self.adjustments_label.setText(str(total_adj))
            
            breakdown = f"(TP1: {tp_adj.get('TP1', 0)}, TP2: {tp_adj.get('TP2', 0)}, " \
                       f"TP3: {tp_adj.get('TP3', 0)}, SL: {tp_adj.get('SL', 0)})"
            self.breakdown_label.setText(breakdown)
            
            # Show results
            self.results_text.append(f"\n✅ Backtest completed successfully!")
            self.results_text.append(f"Total Candles: {results.get('total_candles', 0):,}")
            self.results_text.append(f"Trades: {results.get('trades', 0)}")
            self.results_text.append(f"TP/SL Adjustments: {total_adj}")
        else:
            error = results.get('error', 'Unknown error')
            self.results_text.append(f"\n❌ Backtest failed: {error}")
        
        self.worker = None
    
    def get_config(self) -> dict:
        """Get current backtest configuration"""
        return {
            'lookback_days': self.lookback_spin.value(),
            'training_window': self.training_spin.value(),
            'mode': self.mode_group.checkedId(),
            'tpsl_mode': self.tpsl_combo.currentText(),
            'sl_mode': self.sl_combo.currentText()
        }
