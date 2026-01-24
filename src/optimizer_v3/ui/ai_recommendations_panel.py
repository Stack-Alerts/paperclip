"""
AI Recommendations Panel - Optimizer v3 UI Component

Displays AI-generated recommendations in an easy-to-read format with apply/dismiss actions.

Receives recommendations from the AI recommendation system and presents them
in a structured, actionable format for user review and application.

Author: Optimizer v3 Team
Date: 2026-01-24
Sprint: 1.6 (AI Recommendations Integration)
"""

from typing import List, Dict, Optional
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QTextEdit, QGroupBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

# Import centralized styles
from src.strategy_builder.ui.styles import (
    get_label_style,
    get_primary_button_stylesheet,
    get_panel_title_stylesheet,
    get_groupbox_header_stylesheet,
    get_color,
    create_font
)


class RecommendationCard(QFrame):
    """
    Single recommendation card widget
    
    Displays one AI recommendation with:
    - Action summary
    - Full reasoning
    - Expected impact
    - Confidence level
    - Apply/Dismiss buttons
    """
    
    # Signals
    apply_clicked = pyqtSignal(dict)  # Emits recommendation data
    dismiss_clicked = pyqtSignal(str)  # Emits recommendation ID
    
    def __init__(self, recommendation: Dict, parent=None):
        super().__init__(parent)
        self.recommendation = recommendation
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the card UI"""
        self.setFrameStyle(QFrame.Box | QFrame.Raised)
        self.setLineWidth(1)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {get_color('background_secondary')};
                border: 1px solid {get_color('border')};
                border-radius: 8px;
                padding: 15px;
                margin: 5px;
            }}
            QFrame:hover {{
                border: 1px solid {get_color('primary')};
                background-color: {get_color('hover')};
            }}
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        # Header: Action Type Icon + Summary
        header_layout = QHBoxLayout()
        
        # Icon based on recommendation type
        rec_type = self.recommendation.get('type', 'ADD_BLOCK')
        ai_enhanced = self.recommendation.get('ai_enhanced', False)
        
        if ai_enhanced:
            icon = "🤖"
            type_label = "AI-ENHANCED"
            color = get_color('success')
        else:
            icon = "📊"
            type_label = "DATA-DRIVEN"
            color = get_color('info')
        
        icon_label = QLabel(f"{icon} {type_label}")
        icon_label.setFont(create_font(14, bold=True))
        icon_label.setStyleSheet(f"color: {color};")
        header_layout.addWidget(icon_label)
        
        header_layout.addStretch()
        
        # Confidence badge
        confidence = self.recommendation.get('combined_confidence', 0.0)
        conf_pct = int(confidence * 100)
        conf_badge = QLabel(f"Confidence: {conf_pct}%")
        conf_badge.setFont(create_font(12))
        conf_badge.setStyleSheet(f"color: {get_color('text_secondary')}; background-color: {get_color('background_tertiary')}; padding: 4px 8px; border-radius: 4px;")
        header_layout.addWidget(conf_badge)
        
        layout.addLayout(header_layout)
        
        # Action Summary
        action_text = self._format_action_summary()
        action_label = QLabel(action_text)
        action_label.setFont(create_font(13, bold=True))
        action_label.setWordWrap(True)
        action_label.setStyleSheet(f"color: {get_color('text_primary')};")
        layout.addWidget(action_label)
        
        # Reasoning
        reasoning = self.recommendation.get('reasoning', '')
        if reasoning:
            reasoning_label = QLabel(f"<b>Reason:</b> {reasoning}")
            reasoning_label.setWordWrap(True)
            reasoning_label.setFont(create_font(12))
            reasoning_label.setStyleSheet(f"color: {get_color('text_secondary')}; padding: 5px 0;")
            layout.addWidget(reasoning_label)
        
        # Expected Impact
        expected_impact = self.recommendation.get('expected_impact', {})
        if expected_impact:
            impact_text = ", ".join([f"{k.replace('_', ' ').title()}: {v}" for k, v in expected_impact.items()])
            impact_label = QLabel(f"<b>Expected Impact:</b> {impact_text}")
            impact_label.setWordWrap(True)
            impact_label.setFont(create_font(12))
            impact_label.setStyleSheet(f"color: {get_color('success')};")
            layout.addWidget(impact_label)
        
        # Root Cause (if available)
        root_cause = self.recommendation.get('root_cause', '')
        if root_cause:
            root_label = QLabel(f"<b>Root Cause:</b> {root_cause}")
            root_label.setWordWrap(True)
            root_label.setFont(create_font(11))
            root_label.setStyleSheet(f"color: {get_color('text_muted')};")
            layout.addWidget(root_label)
        
        # Warnings (if any)
        warnings = self.recommendation.get('warnings', [])
        if warnings:
            for warning in warnings[:2]:  # Show max 2 warnings
                warn_label = QLabel(f"⚠️ {warning}")
                warn_label.setWordWrap(True)
                warn_label.setFont(create_font(11))
                warn_label.setStyleSheet(f"color: {get_color('warning')};")
                layout.addWidget(warn_label)
        
        # Action Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        # Dismiss Button
        dismiss_btn = QPushButton("Dismiss")
        dismiss_btn.setFixedWidth(100)
        dismiss_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {get_color('background_tertiary')};
                color: {get_color('text_secondary')};
                border: 1px solid {get_color('border')};
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {get_color('hover')};
                border-color: {get_color('text_secondary')};
            }}
        """)
        dismiss_btn.clicked.connect(lambda: self.dismiss_clicked.emit(
            str(self.recommendation.get('id', ''))
        ))
        button_layout.addWidget(dismiss_btn)
        
        # Apply Button
        apply_btn = QPushButton("✓ Apply")
        apply_btn.setFixedWidth(100)
        apply_btn.setStyleSheet(get_primary_button_stylesheet())
        apply_btn.clicked.connect(lambda: self.apply_clicked.emit(self.recommendation))
        button_layout.addWidget(apply_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def _format_action_summary(self) -> str:
        """Format the action summary text"""
        rec_type = self.recommendation.get('type', 'ADD_BLOCK')
        block_name = self.recommendation.get('block_name', '')
        signal_name = self.recommendation.get('signal_name', '')
        param_name = self.recommendation.get('parameter_name', '')
        config = self.recommendation.get('configuration', {})
        
        if rec_type == 'ADD_BLOCK':
            return f"Add '{block_name}' building block"
        elif rec_type == 'ADD_RECHECK':
            bar_delay = config.get('bar_delay', 25)
            return f"Add recheck validation to '{block_name}::{signal_name}' (delay: {bar_delay} bars)"
        elif rec_type == 'ADD_TIMING':
            max_candles = config.get('max_candles', 20)
            return f"Add timing constraint (within {max_candles} candles)"
        elif rec_type == 'ADJUST_PARAM':
            new_value = config.get('new_value', '?')
            return f"Adjust {param_name} to {new_value}"
        else:
            return f"{rec_type}"


class AIRecommendationsPanel(QWidget):
    """
    AI Recommendations Display Panel
    
    Shows AI-generated recommendations in a scrollable, card-based layout.
    Each recommendation can be applied or dismissed.
    
    Connected to the metrics panel which triggers recommendation generation.
    """
    
    # Signals
    recommendation_applied = pyqtSignal(dict)  # Emits when user applies a recommendation
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.recommendations: List[Dict] = []
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the panel UI"""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Title
        title_label = QLabel("🤖 AI-Powered Recommendations")
        title_label.setStyleSheet(get_panel_title_stylesheet())
        main_layout.addWidget(title_label)
        
        # Description
        desc_label = QLabel(
            "AI-analyzed recommendations based on backtest results, strategy configuration, "
            "and performance metrics. Review each recommendation and apply those that improve your strategy."
        )
        desc_label.setWordWrap(True)
        desc_label.setFont(create_font(12))
        desc_label.setStyleSheet(f"color: {get_color('text_secondary')}; padding: 5px 0 10px 0;")
        main_layout.addWidget(desc_label)
        
        # Scroll Area for recommendations
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background-color: {get_color('background_primary')};
            }}
        """)
        
        # Container widget for cards
        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout()
        self.cards_layout.setSpacing(10)
        self.cards_layout.setAlignment(Qt.AlignTop)
        
        # Placeholder message
        self.placeholder_label = QLabel(
            "No recommendations available.\n\n"
            "Run a backtest first, then AI recommendations will appear here automatically.\n\n"
            "Or click 'Get AI Recommendations' button in the Metrics tab."
        )
        self.placeholder_label.setAlignment(Qt.AlignCenter)
        self.placeholder_label.setFont(create_font(13))
        self.placeholder_label.setStyleSheet(f"color: {get_color('text_muted')}; padding: 50px;")
        self.cards_layout.addWidget(self.placeholder_label)
        
        self.cards_container.setLayout(self.cards_layout)
        self.scroll_area.setWidget(self.cards_container)
        
        main_layout.addWidget(self.scroll_area)
        
        self.setLayout(main_layout)
    
    def display_recommendations(self, recommendations: List[Dict]):
        """
        Display a list of recommendations
        
        Args:
            recommendations: List of recommendation dicts from AI system
        """
        # Clear existing cards
        self._clear_cards()
        
        # Store recommendations
        self.recommendations = recommendations
        
        if not recommendations:
            # Show placeholder
            self.placeholder_label.show()
            return
        
        # Hide placeholder
        self.placeholder_label.hide()
        
        # Create card for each recommendation
        for i, rec in enumerate(recommendations):
            # Add recommendation ID if not present
            if 'id' not in rec:
                rec['id'] = str(i)
            
            card = RecommendationCard(rec)
            card.apply_clicked.connect(self._on_apply_recommendation)
            card.dismiss_clicked.connect(self._on_dismiss_recommendation)
            self.cards_layout.addWidget(card)
        
        # Add stretch at the end
        self.cards_layout.addStretch()
        
        print(f"[AIRecommendationsPanel] Displayed {len(recommendations)} recommendations")
    
    def _clear_cards(self):
        """Clear all recommendation cards"""
        # Remove all widgets except placeholder
        while self.cards_layout.count() > 0:
            item = self.cards_layout.takeAt(0)
            if item.widget() and item.widget() != self.placeholder_label:
                item.widget().deleteLater()
    
    def _on_apply_recommendation(self, recommendation: Dict):
        """Handle apply button click"""
        print(f"[AIRecommendationsPanel] Apply clicked for: {recommendation.get('type')}")
        
        # Emit signal for parent to handle
        self.recommendation_applied.emit(recommendation)
        
        # TODO: Implement actual application logic
        # This would modify the strategy configuration based on the recommendation
        
        # For now, show a message
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.information(
            self,
            "Apply Recommendation",
            f"Recommendation application not yet implemented.\n\n"
            f"Would apply: {recommendation.get('type')}\n"
            f"Block: {recommendation.get('block_name', 'N/A')}"
        )
    
    def _on_dismiss_recommendation(self, rec_id: str):
        """Handle dismiss button click"""
        print(f"[AIRecommendationsPanel] Dismiss clicked for: {rec_id}")
        
        # Find and remove the card
        for i in range(self.cards_layout.count()):
            item = self.cards_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if isinstance(widget, RecommendationCard):
                    if str(widget.recommendation.get('id', '')) == rec_id:
                        # Remove from layout
                        self.cards_layout.removeWidget(widget)
                        widget.deleteLater()
                        
                        # Remove from recommendations list
                        self.recommendations = [
                            r for r in self.recommendations 
                            if str(r.get('id', '')) != rec_id
                        ]
                        
                        # Show placeholder if no more recommendations
                        if not self.recommendations:
                            self.placeholder_label.show()
                        
                        break
    
    def clear_recommendations(self):
        """Clear all recommendations"""
        self._clear_cards()
        self.recommendations = []
        self.placeholder_label.show()


# Test function
if __name__ == '__main__':
    import sys
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # Create test panel
    panel = AIRecommendationsPanel()
    panel.setWindowTitle("AI Recommendations Panel Test")
    panel.resize(800, 600)
    
    # Add test recommendations
    test_recs = [
        {
            'id': '1',
            'type': 'ADD_BLOCK',
            'block_name': 'hod:HOD_REJECTION_RECHECK',
            'ai_enhanced': True,
            'reasoning': 'Current setup has 0 signal occurrences. Recheck pattern validates at bar 18 instead of bar 1, providing 0.0234% more signal opportunities',
            'expected_impact': {
                'trades': '+15-20 over 180 days',
                'sharpe_ratio': '0.33 → 0.75-1.2'
            },
            'combined_confidence': 0.87,
            'root_cause': 'Too restrictive entry conditions (92% confidence)',
            'warnings': []
        },
        {
            'id': '2',
            'type': 'ADJUST_PARAM',
            'parameter_name': 'min_confluence',
            'configuration': {'new_value': 35},
            'ai_enhanced': False,
            'reasoning': 'Current threshold of 40 pts is too restrictive, reducing to 35 pts increases trade frequency',
            'expected_impact': {
                'trade_frequency': '+25%'
            },
            'combined_confidence': 0.72,
            'warnings': ['May slightly reduce win rate']
        }
    ]
    
    panel.display_recommendations(test_recs)
    panel.show()
    
    sys.exit(app.exec_())
