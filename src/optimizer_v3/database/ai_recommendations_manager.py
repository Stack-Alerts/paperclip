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
from datetime import datetime
import json
import logging
from sqlalchemy.orm import Session

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
        Create new AI recommendation
        
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
            recommendation_id: UUID of created recommendation
            
        Raises:
            ValueError: If required fields missing
        """
        # Validate required fields
        required = ['strategy_id', 'recommendation_type', 'title', 'description', 'rationale', 'suggested_changes']
        missing = [f for f in required if f not in recommendation_data]
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(missing)}")
        
        # Validate recommendation type
        valid_types = ['performance', 'risk', 'signal', 'parameter', 'entry', 'exit', 'general']
        if recommendation_data['recommendation_type'] not in valid_types:
            raise ValueError(f"Invalid type. Must be one of: {', '.join(valid_types)}")
        
        # Generate recommendation ID
        rec_id = str(uuid4())
        
        # Prepare data
        data = {
            'recommendation_id': rec_id,
            'strategy_id': recommendation_data['strategy_id'],
            'strategy_version_id': recommendation_data.get('strategy_version_id'),
            'recommendation_type': recommendation_data['recommendation_type'],
            'title': recommendation_data['title'],
            'description': recommendation_data['description'],
            'rationale': recommendation_data['rationale'],
            'suggested_changes': json.dumps(recommendation_data['suggested_changes']),
            'expected_impact': json.dumps(recommendation_data.get('expected_impact', {})),
            'confidence_score': recommendation_data.get('confidence_score', 0.5),
            'priority': recommendation_data.get('priority', 'medium'),
            'model_version': recommendation_data.get('model_version'),
            'analysis_data': json.dumps(recommendation_data.get('analysis_data')) if recommendation_data.get('analysis_data') else None
        }
        
        # Insert recommendation
        query = """
            INSERT INTO ai_recommendations (
                recommendation_id, strategy_id, strategy_version_id, recommendation_type,
                title, description, rationale, suggested_changes, expected_impact,
                confidence_score, priority, model_version, analysis_data
            ) VALUES (
                :recommendation_id, :strategy_id, :strategy_version_id, :recommendation_type,
                :title, :description, :rationale, :suggested_changes, :expected_impact,
                :confidence_score, :priority, :model_version, :analysis_data
            )
        """
        
        self.session.execute(query, data)
        self.session.commit()
        
        self.logger.info(
            f"Created AI recommendation: {rec_id} "
            f"(strategy: {recommendation_data['strategy_id']}, type: {recommendation_data['recommendation_type']})"
        )
        
        return rec_id
    
    def get_recommendation(self, recommendation_id: str) -> Optional[Dict[str, Any]]:
        """
        Get recommendation by ID
        
        Args:
            recommendation_id: Recommendation UUID
            
        Returns:
            Recommendation dict or None if not found
        """
        query = "SELECT * FROM ai_recommendations WHERE recommendation_id = :rec_id"
        result = self.session.execute(query, {'rec_id': recommendation_id}).fetchone()
        
        if not result:
            return None
        
        rec = dict(result._mapping)
        
        # Parse JSON fields
        json_fields = ['suggested_changes', 'expected_impact', 'analysis_data', 'actual_impact']
        for field in json_fields:
            if rec.get(field):
                rec[field] = json.loads(rec[field])
        
        return rec
    
    def get_strategy_recommendations(
        self,
        strategy_id: str,
        applied_only: bool = False,
        pending_only: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get all recommendations for a strategy
        
        Args:
            strategy_id: Strategy ID
            applied_only: Only return applied recommendations
            pending_only: Only return pending recommendations
            
        Returns:
            List of recommendation dicts
        """
        query = "SELECT * FROM ai_recommendations WHERE strategy_id = :strategy_id"
        
        if applied_only:
            query += " AND applied = TRUE"
        elif pending_only:
            query += " AND applied = FALSE"
        
        query += " ORDER BY created_at DESC"
        
        results = self.session.execute(query, {'strategy_id': strategy_id}).fetchall()
        
        recommendations = []
        for row in results:
            rec = dict(row._mapping)
            json_fields = ['suggested_changes', 'expected_impact', 'analysis_data', 'actual_impact']
            for field in json_fields:
                if rec.get(field):
                    rec[field] = json.loads(rec[field])
            recommendations.append(rec)
        
        return recommendations
    
    def mark_applied(
        self,
        recommendation_id: str,
        applied_version_id: str,
        applied_by: Optional[str] = None
    ) -> bool:
        """
        Mark recommendation as applied to a version
        
        Args:
            recommendation_id: Recommendation UUID
            applied_version_id: Version where recommendation was applied
            applied_by: User who applied it
            
        Returns:
            True if updated, False if not found
        """
        query = """
            UPDATE ai_recommendations 
            SET applied = TRUE,
                applied_version_id = :version_id,
                applied_at = NOW(),
                applied_by = :applied_by
            WHERE recommendation_id = :rec_id
        """
        
        result = self.session.execute(
            query,
            {
                'rec_id': recommendation_id,
                'version_id': applied_version_id,
                'applied_by': applied_by
            }
        )
        
        self.session.commit()
        
        updated = result.rowcount > 0
        if updated:
            self.logger.info(f"Marked recommendation {recommendation_id} as applied to {applied_version_id}")
        
        return updated
    
    def record_impact(
        self,
        recommendation_id: str,
        actual_impact: Dict[str, Any]
    ) -> bool:
        """
        Record actual impact after recommendation application
        
        Args:
            recommendation_id: Recommendation UUID
            actual_impact: Actual measured impact data
            
        Returns:
            True if updated, False if not found
        """
        query = """
            UPDATE ai_recommendations 
            SET actual_impact = :impact
            WHERE recommendation_id = :rec_id
        """
        
        result = self.session.execute(
            query,
            {
                'rec_id': recommendation_id,
                'impact': json.dumps(actual_impact)
            }
        )
        
        self.session.commit()
        
        updated = result.rowcount > 0
        if updated:
            self.logger.info(f"Recorded impact for recommendation {recommendation_id}")
        
        return updated
    
    def get_recommendations_by_type(
        self,
        recommendation_type: str
    ) -> List[Dict[str, Any]]:
        """
        Get all recommendations of specific type
        
        Args:
            recommendation_type: Type to filter by
            
        Returns:
            List of recommendation dicts
        """
        query = """
            SELECT * FROM ai_recommendations 
            WHERE recommendation_type = :type 
            ORDER BY created_at DESC
        """
        
        results = self.session.execute(query, {'type': recommendation_type}).fetchall()
        
        recommendations = []
        for row in results:
            rec = dict(row._mapping)
            json_fields = ['suggested_changes', 'expected_impact', 'analysis_data', 'actual_impact']
            for field in json_fields:
                if rec.get(field):
                    rec[field] = json.loads(rec[field])
            recommendations.append(rec)
        
        return recommendations
    
    def get_high_confidence_pending(
        self,
        min_confidence: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Get pending recommendations with high confidence scores
        
        Args:
            min_confidence: Minimum confidence threshold (0.0-1.0)
            
        Returns:
            List of high-confidence pending recommendations
        """
        query = """
            SELECT * FROM ai_recommendations 
            WHERE applied = FALSE 
            AND confidence_score >= :min_conf
            ORDER BY confidence_score DESC, created_at DESC
        """
        
        results = self.session.execute(query, {'min_conf': min_confidence}).fetchall()
        
        recommendations = []
        for row in results:
            rec = dict(row._mapping)
            json_fields = ['suggested_changes', 'expected_impact', 'analysis_data', 'actual_impact']
            for field in json_fields:
                if rec.get(field):
                    rec[field] = json.loads(rec[field])
            recommendations.append(rec)
        
        return recommendations
    
    def get_effectiveness_stats(self) -> Dict[str, Any]:
        """
        Get statistics on recommendation effectiveness
        
        Returns:
            Dict with effectiveness metrics
        """
        query = """
            SELECT 
                COUNT(*) as total_recommendations,
                COUNT(CASE WHEN applied = TRUE THEN 1 END) as total_applied,
                COUNT(CASE WHEN actual_impact IS NOT NULL THEN 1 END) as total_measured,
                AVG(confidence_score) as avg_confidence,
                AVG(CASE WHEN applied = TRUE THEN confidence_score END) as avg_applied_confidence
            FROM ai_recommendations
        """
        
        result = self.session.execute(query).fetchone()
        
        if result:
            stats = dict(result._mapping)
            stats['application_rate'] = (
                stats['total_applied'] / stats['total_recommendations'] 
                if stats['total_recommendations'] > 0 else 0.0
            )
            return stats
        
        return {
            'total_recommendations': 0,
            'total_applied': 0,
            'total_measured': 0,
            'avg_confidence': 0.0,
            'avg_applied_confidence': 0.0,
            'application_rate': 0.0
        }
