"""
AI Recommendations Manager
SPRINT 1.6.1 - Phase 1 Day 2

Manages AI-generated recommendations for strategy improvements.
Tracks recommendations, application status, and effectiveness.

Institutional-grade implementation with:
- Recommendation tracking and history
- Application status monitoring
- Effectiveness measurement
- Feedback loop for AI improvement
"""

from typing import Optional, List, Dict, Any
from uuid import uuid4
from datetime import datetime, timezone
import json
import logging
from sqlalchemy.orm import Session
from sqlalchemy import text

import logging
logger = logging.getLogger(__name__)


logger = logging.getLogger(__name__)


class AIRecommendationsManager:
    """
    Database manager for AI recommendation tracking and analysis
    
    Provides:
    - Create recommendations with detailed rationale
    - Track application status
    - Measure effectiveness post-application
    - Query by strategy, type, status
    - Feedback loop for AI model improvement
    """
    
    def __init__(self, db_session: Session):
        """
        Initialize AI recommendations manager
        
        Args:
            db_session: SQLAlchemy session for database operations
        """
        self.session = db_session
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def create_recommendation(self, recommendation_data: Dict[str, Any]) -> str:
        """
        Create new AI recommendation using ORM
        
        Args:
            recommendation_data: Recommendation details including:
                - strategy_id (str): Target strategy
                - strategy_version_id (str, optional): Specific version
                - recommendation_type (str): Type (performance, risk, signal, parameter)
                - title (str): Brief title
                - description (str): Detailed description
                - rationale (str): AI reasoning
                - suggested_changes (dict): Proposed modifications
                - expected_impact (dict): Projected improvements
                - confidence_score (float): AI confidence (0.0-1.0)
                - priority (str, optional): high, medium, low
                - model_version (str, optional): AI model version
                - analysis_data (dict, optional): Supporting analysis
                
        Returns:
            recommendation_id: UUID string of created recommendation
            
        Raises:
            ValueError: If required fields missing or invalid
            
        Real Money Impact: HIGH - Creates AI recommendations for trading strategies
        
        """
        # Validate required fields
        required = ['strategy_id', 'recommendation_type', 'reasoning']
        missing = [f for f in required if f not in recommendation_data]
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(missing)}")
        
        # Validate recommendation type
        valid_types = ['performance', 'risk', 'signal', 'parameter', 'entry', 'exit', 'general']
        if recommendation_data['recommendation_type'] not in valid_types:
            raise ValueError(f"Invalid type. Must be one of: {', '.join(valid_types)}")
        
        # Use raw SQL insert for columns that exist in the current DB schema.
        # The AIRecommendation ORM model defines columns (title, description,
        # rationale, suggested_changes, priority, applied_version_id,
        # applied_by) that have not been migrated to the PostgreSQL table yet.
        # Raw SQL avoids the ORM including unmigrated columns in the INSERT.
        import uuid as _uuid_mod
        _rec_id = _uuid_mod.uuid4()
        _now = datetime.now(timezone.utc)
        _reasoning = recommendation_data.get('reasoning', recommendation_data.get('rationale', ''))
        _confidence = recommendation_data.get('combined_confidence', recommendation_data.get('confidence_score', 0.5))
        _expected_impact = recommendation_data.get('expected_impact', {})
        _configuration = recommendation_data.get('configuration')
        _version_id = recommendation_data.get('strategy_version_id')
        
        _strategy_version = recommendation_data.get('strategy_version')
        if _strategy_version is None and _version_id is not None:
            _vr = self.session.execute(
                text("SELECT version_number FROM strategy_versions WHERE version_id = :vid"),
                {"vid": _version_id}
            ).scalar()
            if _vr is not None:
                _strategy_version = str(_vr)

        try:
            self.session.execute(
                text("""
                    INSERT INTO ai_recommendations
                        (recommendation_id, strategy_id, version_id,
                         strategy_version, timestamp, recommendation_type,
                         reasoning, expected_impact, combined_confidence,
                         configuration, created_at)
                    VALUES
                        (:rec_id, :strategy_id, :version_id,
                         :strategy_version, :ts, :rec_type,
                         :reasoning, :expected_impact, :combined_confidence,
                         :configuration, :created_at)
                """),
                {
                    "rec_id": _rec_id,
                    "strategy_id": recommendation_data['strategy_id'],
                    "version_id": _version_id,
                    "strategy_version": _strategy_version,
                    "ts": _now,
                    "rec_type": recommendation_data['recommendation_type'],
                    "reasoning": _reasoning,
                    "expected_impact": json.dumps(_expected_impact) if isinstance(_expected_impact, dict) else _expected_impact,
                    "combined_confidence": _confidence,
                    "configuration": json.dumps(_configuration) if isinstance(_configuration, dict) else _configuration,
                    "created_at": _now,
                }
            )
            self.session.commit()
            
            rec_id = str(_rec_id)
            self.logger.info(
                f"Created AI recommendation: {rec_id} "
                f"(strategy: {recommendation_data['strategy_id']}, type: {recommendation_data['recommendation_type']})"
            )
            return rec_id
            
        except Exception as e:
            self.session.rollback()
            self.logger.error(f"Failed to create recommendation: {e}")
            raise
    
    def get_recommendation(self, recommendation_id: str) -> Optional[Dict[str, Any]]:
        """
        Get recommendation by ID

        Uses raw SQL to avoid ORM columns that have not been migrated
        to the current PostgreSQL schema yet.
        """
        try:
            row = self.session.execute(
                text("SELECT * FROM ai_recommendations WHERE recommendation_id = :rid"),
                {"rid": recommendation_id}
            ).mappings().first()

            if not row:
                return None

            return {
                'recommendation_id': str(row['recommendation_id']),
                'strategy_id': row['strategy_id'],
                'strategy_version_id': str(row['version_id']) if row['version_id'] else None,
                'recommendation_type': row['recommendation_type'],
                'reasoning': row['reasoning'],
                'configuration': row['configuration'],
                'expected_impact': row['expected_impact'],
                'combined_confidence': row['combined_confidence'],
                'applied': row['applied'],
                'applied_at': row['applied_at'],
                'created_at': row['created_at'],
            }

        except Exception as e:
            self.session.rollback()
            self.logger.error(f"Failed to get recommendation {recommendation_id}: {e}")
            return None

    def get_strategy_recommendations(
        self,
        strategy_id: str,
        applied_only: bool = False,
        pending_only: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get all recommendations for a strategy

        Uses raw SQL to avoid ORM columns that have not been migrated.
        """
        try:
            where = "WHERE strategy_id = :sid"
            params: dict = {"sid": strategy_id}
            if applied_only:
                where += " AND applied = TRUE"
            elif pending_only:
                where += " AND (applied IS NULL OR applied = FALSE)"

            rows = self.session.execute(
                text(
                    f"SELECT recommendation_id, strategy_id, version_id, "
                    f"recommendation_type, reasoning, expected_impact, "
                    f"configuration, combined_confidence, applied, applied_at, "
                    f"created_at "
                    f"FROM ai_recommendations {where} "
                    f"ORDER BY created_at DESC"
                ),
                params
            ).mappings().all()

            result_list = []
            for row in rows:
                result_list.append({
                    'recommendation_id': str(row['recommendation_id']),
                    'strategy_id': row['strategy_id'],
                    'strategy_version_id': str(row['version_id']) if row['version_id'] else None,
                    'recommendation_type': row['recommendation_type'],
                    'reasoning': row['reasoning'],
                    'configuration': row['configuration'],
                    'expected_impact': row['expected_impact'],
                    'combined_confidence': row['combined_confidence'],
                    'applied': row['applied'],
                    'applied_at': row['applied_at'],
                    'created_at': row['created_at'],
                })

            return result_list

        except Exception as e:
            self.session.rollback()
            self.logger.error(f"Failed to get recommendations for strategy {strategy_id}: {e}")
            return []
    
    def mark_applied(
        self,
        recommendation_id: str,
        applied_version_id: str,
        applied_by: Optional[str] = None
    ) -> bool:
        """
        Mark recommendation as applied to a version

        Uses raw SQL to avoid ORM columns that have not been migrated.
        """
        try:
            result = self.session.execute(
                text("""
                    UPDATE ai_recommendations
                    SET applied = TRUE,
                        applied_at = :now
                    WHERE recommendation_id = :rid
                """),
                {"rid": recommendation_id, "now": datetime.now(timezone.utc)}
            )
            self.session.commit()

            updated = result.rowcount > 0
            if updated:
                self.logger.info(f"Marked recommendation {recommendation_id} as applied")
            return updated

        except Exception as e:
            self.session.rollback()
            self.logger.error(f"Failed to mark recommendation {recommendation_id} as applied: {e}")
            return False
    def record_impact(
        self,
        recommendation_id: str,
        actual_impact: Dict[str, Any]
    ) -> bool:
        """
        Record actual impact after recommendation application.

        Uses raw SQL/text() to stay consistent with the rest of the
        manager — the ORM model declares columns (title, description,
        rationale, suggested_changes, priority, applied_version_id,
        applied_by) that have not been migrated to the live
        PostgreSQL table, so going through the ORM can include
        unmigrated columns in UPDATE statements.

        Args:
            recommendation_id: Recommendation UUID
            actual_impact: Actual measured impact data (Python dict)

        Returns:
            True if updated, False if not found
        """
        try:
            result = self.session.execute(
                text("""
                    UPDATE ai_recommendations
                    SET metrics_after = :impact
                    WHERE recommendation_id = :rid
                """),
                {"rid": recommendation_id, "impact": json.dumps(actual_impact)}
            )
            self.session.commit()

            updated = result.rowcount > 0
            if updated:
                self.logger.info(f"Recorded impact for recommendation {recommendation_id}")
            return updated

        except Exception as e:
            self.session.rollback()
            self.logger.error(f"Failed to record impact for {recommendation_id}: {e}")
            return False
    
    def get_recommendations_by_type(
        self,
        recommendation_type: str
    ) -> List[Dict[str, Any]]:
        """
        Get all recommendations of specific type.

        Uses raw SQL/text() to avoid ORM columns that have not been
        migrated to the live PostgreSQL schema.
        """
        try:
            rows = self.session.execute(
                text("""
                    SELECT *
                    FROM ai_recommendations
                    WHERE recommendation_type = :rtype
                    ORDER BY created_at DESC
                """),
                {"rtype": recommendation_type}
            ).mappings().all()

            return [self._row_to_dict(row) for row in rows]

        except Exception as e:
            self.session.rollback()
            self.logger.error(f"Failed to get recommendations by type {recommendation_type}: {e}")
            return []

    def _row_to_dict(self, row) -> Dict[str, Any]:
        """Convert a raw SQL row mapping to the public dict shape.

        Mirrors the column list that the live PostgreSQL schema actually
        has (see also the raw SELECTs above). The previous helper
        `_recommendation_to_dict` referenced ORM attributes that have
        not been migrated to the live DB, so it was retired in P2.2
        along with all ORM query paths.
        """
        return {
            'recommendation_id': str(row['recommendation_id']) if row['recommendation_id'] else None,
            'strategy_id': row['strategy_id'],
            'strategy_version_id': str(row['version_id']) if row['version_id'] else None,
            'strategy_version': row['strategy_version'],
            'timestamp': row['timestamp'],
            'recommendation_type': row['recommendation_type'],
            'block_name': row['block_name'],
            'signal_name': row['signal_name'],
            'parameter_name': row['parameter_name'],
            'configuration': row['configuration'],
            'reasoning': row['reasoning'],
            'expected_impact': row['expected_impact'],
            'combined_confidence': row['combined_confidence'],
            'root_cause': row['root_cause'],
            'warnings': row['warnings'],
            'ai_enhanced': row['ai_enhanced'],
            'applied': row['applied'],
            'applied_at': row['applied_at'],
            'metrics_before': row['metrics_before'],
            'metrics_after': row['metrics_after'],
            'created_at': row['created_at'],
        }

    def get_high_confidence_pending(
        self,
        min_confidence: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Get pending recommendations with high confidence scores.

        Uses raw SQL/text() to avoid ORM columns that have not been
        migrated to the live PostgreSQL schema.
        """
        try:
            rows = self.session.execute(
                text("""
                    SELECT *
                    FROM ai_recommendations
                    WHERE (applied IS NULL OR applied = FALSE)
                      AND combined_confidence >= :min_conf
                    ORDER BY combined_confidence DESC, created_at DESC
                """),
                {"min_conf": min_confidence}
            ).mappings().all()

            return [self._row_to_dict(row) for row in rows]

        except Exception as e:
            self.session.rollback()
            self.logger.error(f"Failed to get high confidence recommendations: {e}")
            return []
    
    def get_effectiveness_stats(self) -> Dict[str, Any]:
        """
        Get statistics on recommendation effectiveness.

        Uses raw SQL/text() with a single aggregation query to avoid
        ORM columns that have not been migrated to the live
        PostgreSQL schema.

        Returns:
            Dict with effectiveness metrics including:
            - total_recommendations
            - total_applied
            - total_measured
            - avg_confidence
            - avg_applied_confidence
            - application_rate
        """
        try:
            row = self.session.execute(
                text("""
                    SELECT
                        COUNT(*) AS total_recommendations,
                        COUNT(*) FILTER (WHERE applied = TRUE) AS total_applied,
                        COUNT(*) FILTER (WHERE metrics_after IS NOT NULL) AS total_measured,
                        AVG(combined_confidence) AS avg_confidence,
                        AVG(combined_confidence) FILTER (WHERE applied = TRUE) AS avg_applied_confidence
                    FROM ai_recommendations
                """)
            ).mappings().one()

            total = row['total_recommendations'] or 0
            stats = {
                'total_recommendations': total,
                'total_applied': row['total_applied'] or 0,
                'total_measured': row['total_measured'] or 0,
                'avg_confidence': float(row['avg_confidence']) if row['avg_confidence'] else 0.0,
                'avg_applied_confidence': float(row['avg_applied_confidence']) if row['avg_applied_confidence'] else 0.0
            }
            stats['application_rate'] = (
                stats['total_applied'] / total if total > 0 else 0.0
            )
            return stats

        except Exception as e:
            self.session.rollback()
            self.logger.error(f"Failed to get effectiveness stats: {e}")
            return {
                'total_recommendations': 0,
                'total_applied': 0,
                'total_measured': 0,
                'avg_confidence': 0.0,
                'avg_applied_confidence': 0.0,
                'application_rate': 0.0
            }
