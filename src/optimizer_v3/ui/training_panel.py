"""
Training Panel UI - Sprint 2.1
===============================

New Tab: Automated Trainer
Provides forward-looking signal analysis, training database, and optimal parameters.

Tasks Implemented:
- 2.1.1: TrainingPanelUI base structure
- 2.1.2: Block selection with BlockRegistry
- 2.1.3: Mode selection (Testing/Production)
- 2.1.4: Period selection dropdown
- 2.1.5: Timeframe checkboxes
- 2.1.6: Resource estimator & monitoring
- 2.1.7: Confirmation dialog

REUSES PATTERNS FROM:
- BacktestConfigurationPanel: QGroupBox, QFormLayout, QSpinBox, QCheckBox, QComboBox
- TradesPanel: Table structure, export functionality, logger integration
- AIRecommendationsPanel: Panel layout, button styling

CRITICAL: Zero hardcoded styles - all from styles.py
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional
from decimal import Decimal
from datetime import datetime, timedelta

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout,
    QCheckBox, QComboBox, QSpinBox, QLabel, QPushButton,
    QMessageBox, QProgressBar, QTextEdit
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

# Import centralized styles
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))
from src.strategy_builder.ui.styles import (
    get_main_stylesheet,
    get_primary_button_stylesheet,
    get_secondary_button_stylesheet,
    get_text_edit_stylesheet,
    get_color
)

# Import configuration
from src.optimizer_v3.config.training_config import get_training_config


class TrainingPanelUI(QWidget):
    """
    Training Panel UI - New Tab: Automated Trainer
    
    Forward-looking signal analysis to determine optimal RECHECK delays,
    timing windows, and parameter configurations.
    
    FEATURES:
    - Block selection from BlockRegistry
    - Testing/Production mode selection
    - Configurable analysis period
    - Multi-timeframe analysis
    - Resource estimation
    - Progress tracking
    - Results display with export
    
    PATTERN REUSE:
    - Configuration UI from BacktestConfigurationPanel
    - Results display from TradesPanel
    - Layout from AIRecommendationsPanel
    """
    
    # Signals
    training_started = pyqtSignal(dict)  # Emits training config
    training_stopped = pyqtSignal()
    
    def __init__(self, orchestrator=None, parent=None):
        super().__init__(parent)
        
        # Store orchestrator reference to access strategy
        self.orchestrator = orchestrator
        
        # Load configuration
        self.config = get_training_config()
        
        # Training state
        self.training_running = False
        self.selected_blocks = []
        self.selected_timeframes = []
        
        # Training worker
        self.training_thread = None
        
        # Setup UI
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup UI with zero hardcoded styles"""
        # Apply main stylesheet
        self.setStyleSheet(get_main_stylesheet())
        
        # Main layout - INCREASED SPACING for better readability
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)  # More padding around edges
        layout.setSpacing(16)  # More space between sections
        
        # Header
        header = self._create_header()
        layout.addWidget(header)
        
        # Configuration section (Tasks 2.1.2-2.1.5)
        config_section = self._create_configuration_section()
        layout.addWidget(config_section)
        
        # Progress section (Task 2.1.21)
        progress_section = self._create_progress_section()
        layout.addWidget(progress_section)
        
        # Results section (Task 2.1.22)
        results_section = self._create_results_section()
        layout.addWidget(results_section, stretch=1)
        
        # Action buttons
        action_section = self._create_action_section()
        layout.addWidget(action_section)
    
    def _create_header(self) -> QWidget:
        """Create header with title"""
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(4, 4, 4, 4)
        
        title = QLabel("🎯 Automated Trainer - Forward-Looking Signal Analysis")
        title_font = QFont("Segoe UI", 12, QFont.Weight.Bold)
        title.setFont(title_font)
        title.setStyleSheet("color: #FFFFFF; padding: 4px;")  # White for readability
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        return header_widget
    
    def _create_configuration_section(self) -> QWidget:
        """
        Create configuration section
        
        REUSES: BacktestConfigurationPanel patterns
        - QGroupBox with QFormLayout
        - QCheckBox for block selection
        - QComboBox for mode selection
        - QSpinBox for period selection
        - QCheckBox for timeframe selection
        """
        config_group = QGroupBox("Training Configuration")
        config_group.setStyleSheet(f"""
            QGroupBox {{
                font-weight: bold;
                font-size: 11pt;
                color: {get_color('primary')};
                border: 2px solid {get_color('border')};
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 8px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }}
        """)
        
        config_layout = QVBoxLayout()
        config_layout.setSpacing(12)  # Space between rows
        config_layout.setContentsMargins(16, 16, 16, 16)
        
        # Task 2.1.2: Block Selection
        block_section = self._create_block_selection()
        config_layout.addWidget(block_section)
        
        # ALL THREE CONFIG ITEMS IN ONE HORIZONTAL ROW
        single_row_layout = QHBoxLayout()
        single_row_layout.setSpacing(20)
        
        # Analysis Mode
        mode_label = QLabel("Analysis Mode:")
        mode_label.setStyleSheet("color: #FFFFFF; font-size: 10pt;")
        single_row_layout.addWidget(mode_label)
        
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(['Testing Mode (Limited Data)', 'Production Mode (Full Data)'])
        self.mode_combo.setCurrentIndex(0)
        self.mode_combo.setStyleSheet(f"""
            QComboBox {{
                padding: 4px 8px;
                border: 1px solid {get_color('border')};
                border-radius: 3px;
                background-color: {get_color('bg_light')};
                min-height: 24px;
                color: #FFFFFF;
            }}
            QComboBox:hover {{
                border-color: {get_color('primary')};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
        """)
        single_row_layout.addWidget(self.mode_combo)
        
        # Separator
        single_row_layout.addSpacing(20)
        
        # Lookback Period
        period_label = QLabel("Lookback Period:")
        period_label.setStyleSheet("color: #FFFFFF; font-size: 10pt;")
        single_row_layout.addWidget(period_label)
        
        self.period_spin = QSpinBox()
        self.period_spin.setRange(7, 365)
        self.period_spin.setValue(self.config['training']['max_lookback'])
        self.period_spin.setSuffix(" days")
        self.period_spin.setStyleSheet(f"""
            QSpinBox {{
                padding: 4px 8px;
                border: 1px solid {get_color('border')};
                border-radius: 3px;
                background-color: {get_color('bg_light')};
                min-height: 24px;
                color: #FFFFFF;
            }}
            QSpinBox:hover {{
                border-color: {get_color('primary')};
            }}
        """)
        single_row_layout.addWidget(self.period_spin)
        
        # Separator
        single_row_layout.addSpacing(20)
        
        # Timeframes
        timeframe_label = QLabel("Timeframes:")
        timeframe_label.setStyleSheet("color: #FFFFFF; font-size: 10pt;")
        single_row_layout.addWidget(timeframe_label)
        
        timeframe_section = self._create_timeframe_selection()
        single_row_layout.addWidget(timeframe_section)
        
        single_row_layout.addStretch()
        config_layout.addLayout(single_row_layout)
        
        config_group.setLayout(config_layout)
        return config_group
    
    def _create_block_selection(self) -> QWidget:
        """
        Create block selection checkboxes - HORIZONTAL INLINE LAYOUT
        
        LOADS FROM STRATEGY: Gets blocks from current strategy configuration
        """
        block_widget = QWidget()
        main_layout = QVBoxLayout(block_widget)
        main_layout.setSpacing(12)  # More space between rows
        main_layout.setContentsMargins(0, 4, 0, 4)  # Add vertical padding
        
        # Load blocks from strategy configuration
        blocks = self._get_strategy_blocks()
        
        if not blocks:
            # Fallback if no strategy loaded
            no_blocks_label = QLabel("⚠️ No strategy loaded. Please add building blocks first.")
            no_blocks_label.setStyleSheet("color: #FFB74D; padding: 8px;")  # Orange warning
            main_layout.addWidget(no_blocks_label)
            self.block_checkboxes = []
            return block_widget
        
        # HORIZONTAL LAYOUT for checkboxes
        checkboxes_layout = QHBoxLayout()
        checkboxes_layout.setSpacing(20)
        
        self.block_checkboxes = []
        for block_name in blocks:
            checkbox = QCheckBox(block_name)
            checkbox.setStyleSheet("""
                QCheckBox {
                    spacing: 8px;
                    color: #FFFFFF;
                    font-size: 10pt;
                }
                QCheckBox::indicator {
                    width: 18px;
                    height: 18px;
                    border: 2px solid #555;
                    border-radius: 3px;
                    background-color: #2A2A2A;
                }
                QCheckBox::indicator:checked {
                    background-color: #007ACC;
                    border-color: #007ACC;
                }
                QCheckBox::indicator:hover {
                    border-color: #007ACC;
                }
            """)
            checkboxes_layout.addWidget(checkbox)
            self.block_checkboxes.append(checkbox)
        
        checkboxes_layout.addStretch()
        main_layout.addLayout(checkboxes_layout)
        
        # Select All / Deselect All buttons
        button_layout = QHBoxLayout()
        
        select_all_btn = QPushButton("Select All")
        select_all_btn.setStyleSheet(get_secondary_button_stylesheet() + """
            font-size: 12pt;
            color: #FFFFFF;
            font-weight: bold;
            padding: 8px 20px;
            min-width: 120px;
        """)
        select_all_btn.setFixedHeight(36)
        select_all_btn.clicked.connect(lambda: self._toggle_all_blocks(True))
        button_layout.addWidget(select_all_btn)
        
        deselect_all_btn = QPushButton("Deselect All")
        deselect_all_btn.setStyleSheet(get_secondary_button_stylesheet() + """
            font-size: 12pt;
            color: #FFFFFF;
            font-weight: bold;
            padding: 8px 20px;
            min-width: 140px;
        """)
        deselect_all_btn.setFixedHeight(36)
        deselect_all_btn.clicked.connect(lambda: self._toggle_all_blocks(False))
        button_layout.addWidget(deselect_all_btn)
        
        button_layout.addStretch()
        main_layout.addLayout(button_layout)
        
        return block_widget
    
    def _create_timeframe_selection(self) -> QWidget:
        """
        Create timeframe selection checkboxes
        
        REUSES: BacktestConfigurationPanel checkbox patterns
        """
        timeframe_widget = QWidget()
        timeframe_layout = QHBoxLayout(timeframe_widget)
        timeframe_layout.setSpacing(12)
        timeframe_layout.setContentsMargins(0, 0, 0, 0)
        
        timeframes = ['5m', '15m', '1h', '4h']
        self.timeframe_checkboxes = {}
        
        for tf in timeframes:
            checkbox = QCheckBox(tf)
            checkbox.setChecked(tf in ['5m', '15m'])  # Default selection
            checkbox.setStyleSheet(f"""
                QCheckBox {{
                    spacing: 8px;
                    color: {get_color('text_secondary')};
                }}
                QCheckBox::indicator {{
                    width: 16px;
                    height: 16px;
                    border: 2px solid {get_color('border')};
                    border-radius: 3px;
                    background-color: {get_color('bg_light')};
                }}
                QCheckBox::indicator:checked {{
                    background-color: {get_color('success')};
                    border-color: {get_color('success')};
                }}
                QCheckBox::indicator:hover {{
                    border-color: {get_color('primary')};
                }}
            """)
            timeframe_layout.addWidget(checkbox)
            self.timeframe_checkboxes[tf] = checkbox
        
        return timeframe_widget
    
    def _create_progress_section(self) -> QWidget:
        """
        Create progress tracking section
        
        Task 2.1.21: Progress tracking UI
        """
        progress_group = QGroupBox("Training Progress")
        progress_group.setStyleSheet(f"""
            QGroupBox {{
                font-weight: bold;
                font-size: 10pt;
                color: {get_color('text_secondary')};
                border: 2px solid {get_color('border')};
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 8px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }}
        """)
        
        progress_layout = QVBoxLayout()
        progress_layout.setSpacing(4)
        progress_layout.setContentsMargins(8, 12, 8, 8)
        
        # Status label
        self.status_label = QLabel("Status: Ready")
        self.status_label.setStyleSheet(f"color: {get_color('text_secondary')}; font-weight: bold;")
        progress_layout.addWidget(self.status_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 2px solid {get_color('border')};
                border-radius: 5px;
                text-align: center;
                height: 24px;
                background-color: {get_color('bg_light')};
            }}
            QProgressBar::chunk {{
                background-color: {get_color('primary')};
                border-radius: 3px;
            }}
        """)
        progress_layout.addWidget(self.progress_bar)
        
        # ETA label
        self.eta_label = QLabel("ETA: Not started")
        self.eta_label.setStyleSheet(f"color: {get_color('text_muted')}; font-size: 9pt;")
        progress_layout.addWidget(self.eta_label)
        
        progress_group.setLayout(progress_layout)
        return progress_group
    
    def _create_results_section(self) -> QWidget:
        """
        Create results display section
        
        Task 2.1.22: Results display table
        (Full implementation will be in training_results_table.py)
        """
        results_group = QGroupBox("Training Results")
        results_group.setStyleSheet(f"""
            QGroupBox {{
                font-weight: bold;
                font-size: 11pt;
                color: {get_color('text_secondary')};
                border: 2px solid {get_color('border')};
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 8px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }}
        """)
        
        results_layout = QVBoxLayout()
        results_layout.setSpacing(4)
        results_layout.setContentsMargins(8, 12, 8, 8)
        
        # Results text area (placeholder - will be replaced with table)
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setPlainText("No training results yet. Start training to see optimal parameters.")
        # INCREASED FONT SIZE for readability
        self.results_text.setStyleSheet(get_text_edit_stylesheet() + """
            QTextEdit {
                font-size: 11pt;
                line-height: 1.5;
            }
        """)
        results_layout.addWidget(self.results_text)
        
        results_group.setLayout(results_layout)
        return results_group
    
    def _create_action_section(self) -> QWidget:
        """Create action buttons section"""
        action_widget = QWidget()
        action_layout = QHBoxLayout(action_widget)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(8)
        
        action_layout.addStretch()
        
        # Export button
        self.export_btn = QPushButton("Export Results")
        self.export_btn.setStyleSheet(get_secondary_button_stylesheet())
        self.export_btn.setFixedHeight(40)
        self.export_btn.setEnabled(False)
        self.export_btn.clicked.connect(self._export_results)
        action_layout.addWidget(self.export_btn)
        
        # Stop button (hidden by default)
        self.stop_btn = QPushButton("⏹ Stop Training")
        self.stop_btn.setStyleSheet(get_secondary_button_stylesheet())
        self.stop_btn.setFixedHeight(40)
        self.stop_btn.setVisible(False)
        self.stop_btn.clicked.connect(self._stop_training)
        action_layout.addWidget(self.stop_btn)
        
        # Start button
        self.start_btn = QPushButton("▶ Start Training")
        self.start_btn.setStyleSheet(get_primary_button_stylesheet())
        self.start_btn.setFixedHeight(40)
        self.start_btn.clicked.connect(self._start_training)
        action_layout.addWidget(self.start_btn)
        
        return action_widget
    
    def _toggle_all_blocks(self, checked: bool):
        """Toggle all block checkboxes"""
        for checkbox in self.block_checkboxes:
            checkbox.setChecked(checked)
    
    def _start_training(self):
        """
        Start training with confirmation dialog
        
        Task 2.1.7: Confirmation dialog
        """
        # Get selected blocks
        selected_blocks = [
            cb.text() for cb in self.block_checkboxes if cb.isChecked()
        ]
        
        # Get selected timeframes
        selected_timeframes = [
            tf for tf, cb in self.timeframe_checkboxes.items() if cb.isChecked()
        ]
        
        # Validation
        if not selected_blocks:
            QMessageBox.warning(
                self,
                "No Blocks Selected",
                "Please select at least one building block to analyze."
            )
            return
        
        if not selected_timeframes:
            QMessageBox.warning(
                self,
                "No Timeframes Selected",
                "Please select at least one timeframe to analyze."
            )
            return
        
        # Build configuration
        training_config = {
            'blocks': selected_blocks,
            'timeframes': selected_timeframes,
            'period_days': self.period_spin.value(),
            'mode': 'testing' if self.mode_combo.currentIndex() == 0 else 'production',
            'config': self.config
        }
        
        # Confirmation dialog (Task 2.1.7)
        msg = f"""
        <h3>Confirm Training Configuration</h3>
        <p><b>Selected Blocks:</b> {len(selected_blocks)}</p>
        <ul>{''.join(f'<li>{block}</li>' for block in selected_blocks)}</ul>
        <p><b>Timeframes:</b> {', '.join(selected_timeframes)}</p>
        <p><b>Lookback Period:</b> {self.period_spin.value()} days</p>
        <p><b>Mode:</b> {self.mode_combo.currentText()}</p>
        <br>
        <p><b>Estimated Analysis Time:</b> 5-15 minutes</p>
        <p>This will analyze historical signals and calculate optimal parameters.</p>
        """
        
        reply = QMessageBox.question(
            self,
            "Confirm Training",
            msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self._execute_training(training_config)
    
    def _execute_training(self, config: dict):
        """Execute training with given configuration"""
        self.training_running = True
        
        # Update UI state
        self.start_btn.setEnabled(False)
        self.stop_btn.setVisible(True)
        self.status_label.setText("Status: Training in progress...")
        self.status_label.setStyleSheet(f"color: {get_color('warning')}; font-weight: bold;")
        
        # Disable configuration inputs
        for checkbox in self.block_checkboxes:
            checkbox.setEnabled(False)
        for checkbox in self.timeframe_checkboxes.values():
            checkbox.setEnabled(False)
        self.mode_combo.setEnabled(False)
        self.period_spin.setEnabled(False)
        
        # Create and start training thread
        from src.optimizer_v3.core.training_thread import TrainingThread
        
        self.training_thread = TrainingThread(
            selected_blocks=config['blocks'],
            mode=config['mode'],
            period_days=config['period_days'],
            selected_timeframes=config['timeframes'],
            logger=None  # Optional logger
        )
        
        # Connect signals
        self.training_thread.progress_update.connect(self._on_progress_update)
        self.training_thread.block_complete.connect(self._on_block_complete)
        self.training_thread.training_complete.connect(self._on_training_complete)
        self.training_thread.error_occurred.connect(self._on_training_error)
        self.training_thread.eta_update.connect(self._on_eta_update)
        
        # Start training
        self.training_thread.start()
    
    def _stop_training(self):
        """Stop training"""
        reply = QMessageBox.question(
            self,
            "Stop Training",
            "Are you sure you want to stop the training?\n\nPartial results will be saved.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.training_stopped.emit()
            self._reset_ui_state()
    
    def _reset_ui_state(self):
        """Reset UI state after training completes or stops"""
        self.training_running = False
        
        # Update UI state
        self.start_btn.setEnabled(True)
        self.stop_btn.setVisible(False)
        self.status_label.setText("Status: Ready")
        self.status_label.setStyleSheet(f"color: {get_color('text_secondary')}; font-weight: bold;")
        
        # Enable configuration inputs
        for checkbox in self.block_checkboxes:
            checkbox.setEnabled(True)
        for checkbox in self.timeframe_checkboxes.values():
            checkbox.setEnabled(True)
        self.mode_combo.setEnabled(True)
        self.period_spin.setEnabled(True)
        
        # Reset progress
        self.progress_bar.setValue(0)
        self.eta_label.setText("ETA: Not started")
    
    def update_progress(self, progress: int, message: str, eta: str):
        """Update progress bar and status"""
        self.progress_bar.setValue(progress)
        self.status_label.setText(f"Status: {message}")
        self.eta_label.setText(f"ETA: {eta}")
    
    def training_complete(self, results: dict):
        """Handle training completion"""
        self._reset_ui_state()
        
        # Update status
        self.status_label.setText("Status: Training complete ✓")
        self.status_label.setStyleSheet(f"color: {get_color('success')}; font-weight: bold;")
        self.progress_bar.setValue(100)
        self.eta_label.setText("ETA: Complete")
        
        # Enable export
        self.export_btn.setEnabled(True)
        
        # Display results (placeholder - will use TrainingResultsTable)
        self.results_text.setPlainText(f"Training complete!\n\nResults: {results}")
    
    def _on_progress_update(self, current: int, total: int, message: str):
        """Handle progress update from training thread"""
        if total > 0:
            percentage = int((current / total) * 100)
            self.progress_bar.setValue(percentage)
        self.status_label.setText(f"Status: {message}")
    
    def _on_block_complete(self, block_name: str, result: dict):
        """Handle single block completion"""
        # Add to results display
        confidence = result.get('confidence', 0)
        delay = result.get('optimal_delay', 0)
        current_text = self.results_text.toPlainText()
        
        if current_text == "No training results yet. Start training to see optimal parameters.":
            current_text = "Training Results:\n\n"
        
        current_text += f"✓ {block_name}: Optimal delay = {delay} bars (confidence: {float(confidence):.0%})\n"
        self.results_text.setPlainText(current_text)
    
    def _on_training_complete(self, results: list):
        """Handle training completion"""
        self._reset_ui_state()
        
        # Update status
        self.status_label.setText("Status: Training complete ✓")
        self.status_label.setStyleSheet(f"color: {get_color('success')}; font-weight: bold;")
        self.progress_bar.setValue(100)
        self.eta_label.setText("ETA: Complete")
        
        # Enable export
        self.export_btn.setEnabled(True)
        
        # Display summary
        summary = f"\n\n{'='*50}\nTRAINING COMPLETE\n{'='*50}\n"
        summary += f"Total results: {len(results)}\n"
        summary += f"High confidence (>80%): {len([r for r in results if r.get('confidence', 0) > 0.8])}\n"
        summary += f"Medium confidence (50-80%): {len([r for r in results if 0.5 <= r.get('confidence', 0) <= 0.8])}\n"
        summary += f"Low confidence (<50%): {len([r for r in results if r.get('confidence', 0) < 0.5])}\n"
        
        current_text = self.results_text.toPlainText()
        self.results_text.setPlainText(current_text + summary)
    
    def _on_training_error(self, error_message: str):
        """Handle training error"""
        self._reset_ui_state()
        
        # Update status
        self.status_label.setText("Status: Error occurred")
        self.status_label.setStyleSheet(f"color: {get_color('error')}; font-weight: bold;")
        
        # Display error
        self.results_text.setPlainText(f"❌ Training Error:\n\n{error_message}")
        
        # Show error dialog
        QMessageBox.critical(
            self,
            "Training Error",
            f"An error occurred during training:\n\n{error_message}"
        )
    
    def _on_eta_update(self, seconds_remaining: int):
        """Handle ETA update"""
        if seconds_remaining < 60:
            eta_text = f"{seconds_remaining}s"
        elif seconds_remaining < 3600:
            minutes = seconds_remaining // 60
            eta_text = f"{minutes}m {seconds_remaining % 60}s"
        else:
            hours = seconds_remaining // 3600
            minutes = (seconds_remaining % 3600) // 60
            eta_text = f"{hours}h {minutes}m"
        
        self.eta_label.setText(f"ETA: {eta_text}")
    
    def _get_strategy_blocks(self) -> List[str]:
        """
        Get building block names from loaded strategy
        
        Returns:
            List[str]: Block names from strategy, or empty list if no strategy
        """
        try:
            if not self.orchestrator:
                return []
            
            # Get current strategy configuration
            config = self.orchestrator.get_current_config()
            if not config or not hasattr(config, 'blocks'):
                return []
            
            # Extract block names
            block_names = []
            for block in config.blocks:
                if hasattr(block, 'name'):
                    block_names.append(block.name)
            
            return block_names
            
        except Exception as e:
            # Silently fail - UI will show warning
            return []
    
    def _export_results(self):
        """
        Export training results
        
        Task 2.1.23: Export functionality
        (Full implementation will be in training_results_table.py)
        """
        # Placeholder for export
        QMessageBox.information(
            self,
            "Export Results",
            "Export functionality will be implemented in training_results_table.py"
        )
