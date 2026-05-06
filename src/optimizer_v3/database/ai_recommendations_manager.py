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
        
        ORM Refactored: Sprint 1.6.1 Task 2.1.7
        """
        from src.optimizer_v3.database.models import AIRecommendation
        
        # Validate required fields
        required = ['strategy_id', 'recommendation_type', 'title', 'description', 'rationale', 'suggested_changes']
        missing = [f for f in required if f not in recommendation_data]
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(missing)}")
        
        # Validate recommendation type
        valid_types = ['performance', 'risk', 'signal', 'parameter', 'entry', 'exit', 'general']
        if recommendation_data['recommendation_type'] not in valid_types:
            raise ValueError(f"Invalid type. Must be one of: {', '.join(valid_types)}")
        
        # Create ORM object - SQLAlchemy handles JSONB automatically
        recommendation = AIRecommendation(
            strategy_id=recommendation_data['strategy_id'],
            strategy_version_id=recommendation_data.get('strategy_version_id'),
            recommendation_type=recommendation_data['recommendation_type'],
            title=recommendation_data['title'],
            description=recommendation_data['description'],
            rationale=recommendation_data['rationale'],
            # JSONB fields - pass Python dicts directly
            suggested_changes=recommendation_data['suggested_changes'],
            expected_impact=recommendation_data.get('expected_impact', {}),
            analysis_data=recommendation_data.get('analysis_data'),
            # Other fields
            confidence_score=recommendation_data.get('confidence_score', 0.5),
            priority=recommendation_data.get('priority', 'medium'),
            model_version=recommendation_data.get('model_version')
            # recommendation_id, created_at handled by defaults
        )
        
        try:
            self.session.add(recommendation)
            self.session.commit()
            
            # Get UUID as string
            rec_id = str(recommendation.recommendation_id)
            
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
        Get recommendation by ID using ORM
        
        Args:
            recommendation_id: Recommendation UUID string
            
        Returns:
            Recommendation dict or None if not found
            JSONB fields automatically deserialized to Python objects
            
        Real Money Impact: MEDIUM - Retrieves AI recommendation data
        
        ORM Refactored: Sprint 1.6.1 Task 2.1.1
        """
        # Import AIRecommendation ORM model
        from src.optimizer_v3.database.models import AIRecommendation
        
        try:
            # Query using ORM
            recommendation = self.session.query(AIRecommendation).filter_by(
                recommendation_id=recommendation_id
            ).first()
            
            if not recommendation:
                return None
            
            # Convert ORM object to dict
            # JSONB fields are automatically deserialized by SQLAlchemy
            rec_dict = {
                'recommendation_id': str(recommendation.recommendation_id),
                'strategy_id': recommendation.strategy_id,
                'strategy_version_id': str(recommendation.strategy_version_id) if recommendation.strategy_version_id else None,
                'recommendation_type': recommendation.recommendation_type,
                'title': recommendation.title,
                'description': recommendation.description,
                'rationale': recommendation.rationale,
                # JSONB fields - already Python objects
                'suggested_changes': recommendation.suggested_changes,
                'expected_impact': recommendation.expected_impact,
                'analysis_data': recommendation.analysis_data,
                'actual_impact': recommendation.actual_impact,
                # Other fields
                'confidence_score': recommendation.confidence_score,
                'priority': recommendation.priority,
                'model_version': recommendation.model_version,
                'applied': recommendation.applied,
                'applied_version_id': str(recommendation.applied_version_id) if recommendation.applied_version_id else None,
                'applied_at': recommendation.applied_at,
                'applied_by': recommendation.applied_by,
                'created_at': recommendation.created_at
            }
            
            return rec_dict
            
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
        Get all recommendations for a strategy using ORM
        
        Args:
            strategy_id: Strategy ID
            applied_only: Only return applied recommendations
            pending_only: Only return pending recommendations
            
        Returns:
            List of recommendation dicts with JSONB auto-deserialized
            
        Real Money Impact: MEDIUM - Lists AI recommendations for strategy
        
        ORM Refactored: Sprint 1.6.1 Task 2.1.2
        """
        from src.optimizer_v3.database.models import AIRecommendation
        
        try:
            # Build ORM query with filters
            query = self.session.query(AIRecommendation).filter_by(
                strategy_id=strategy_id
            )
            
            if applied_only:
                query = query.filter(AIRecommendation.applied == True)
            elif pending_only:
                query = query.filter(AIRecommendation.applied == False)
            
            query = query.order_by(AIRecommendation.created_at.desc())
            
            recommendations = query.all()
            
            # Convert to list of dicts
            result_list = []
            for rec in recommendations:
                rec_dict = {
                    'recommendation_id': str(rec.recommendation_id),
                    'strategy_id': rec.strategy_id,
                    'strategy_version_id': str(rec.strategy_version_id) if rec.strategy_version_id else None,
                    'recommendation_type': rec.recommendation_type,
                    'title': rec.title,
                    'description': rec.description,
                    'rationale': rec.rationale,
                    'suggested_changes': rec.suggested_changes,
                    'expected_impact': rec.expected_impact,
                    'analysis_data': rec.analysis_data,
                    'actual_impact': rec.actual_impact,
                    'confidence_score': rec.confidence_score,
                    'priority': rec.priority,
                    'model_version': rec.model_version,
                    'applied': rec.applied,
                    'applied_version_id': str(rec.applied_version_id) if rec.applied_version_id else None,
                    'applied_at': rec.applied_at,
                    'applied_by': rec.applied_by,
                    'created_at': rec.created_at
                }
                result_list.append(rec_dict)
            
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
        Mark recommendation as applied to a version using ORM
        
        Args:
            recommendation_id: Recommendation UUID
            applied_version_id: Version where recommendation was applied
            applied_by: User who applied it
            
        Returns:
            True if updated, False if not found
            
        ORM Refactored: Sprint 1.6.1 Task 2.1.5
        """
        from src.optimizer_v3.database.models import AIRecommendation
        
        try:
            recommendation = self.session.query(AIRecommendation).filter_by(
                recommendation_id=recommendation_id
            ).first()
            
            if not recommendation:
                return False
            
            # Update using ORM
            recommendation.applied = True
            recommendation.applied_version_id = applied_version_id
            recommendation.applied_at = datetime.now(timezone.utc)
            recommendation.applied_by = applied_by
            
            self.session.commit()
            
            self.logger.info(f"Marked recommendation {recommendation_id} as applied to {applied_version_id}")
            return True
            
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
        Record actual impact after recommendation application using ORM
        
        Args:
            recommendation_id: Recommendation UUID
            actual_impact: Actual measured impact data (Python dict)
            
        Returns:
            True if updated, False if not found
            
        ORM Refactored: Sprint 1.6.1 Task 2.1.6
        """
        from src.optimizer_v3.database.models import AIRecommendation
        
        try:
            recommendation = self.session.query(AIRecommendation).filter_by(
                recommendation_id=recommendation_id
            ).first()
            
            if not recommendation:
                return False
            
            # Update JSONB field - SQLAlchemy handles serialization
            recommendation.actual_impact = actual_impact
            
            self.session.commit()
            
            self.logger.info(f"Recorded impact for recommendation {recommendation_id}")
            return True
            
        except Exception as e:
            self.session.rollback()
            self.logger.error(f"Failed to record impact for {recommendation_id}: {e}")
            return False
    
    def get_recommendations_by_type(
        self,
        recommendation_type: str
    ) -> List[Dict[str, Any]]:
        """
        Get all recommendations of specific type using ORM
        
        Args:
            recommendation_type: Type to filter by
            
        Returns:
            List of recommendation dicts with JSONB auto-deserialized
            
        ORM Refactored: Sprint 1.6.1 Task 2.1.3
        """
        from src.optimizer_v3.database.models import AIRecommendation
        
        try:
            recommendations = self.session.query(AIRecommendation).filter_by(
                recommendation_type=recommendation_type
            ).order_by(AIRecommendation.created_at.desc()).all()
            
            return [self._recommendation_to_dict(rec) for rec in recommendations]
            
        except Exception as e:
            self.session.rollback()
            self.logger.error(f"Failed to get recommendations by type {recommendation_type}: {e}")
            return []
    
    def _recommendation_to_dict(self, rec) -> Dict[str, Any]:
        """Helper to convert ORM object to dict"""
        return {
            'recommendation_id': str(rec.recommendation_id),
            'strategy_id': rec.strategy_id,
            'strategy_version_id': str(rec.strategy_version_id) if rec.strategy_version_id else None,
            'recommendation_type': rec.recommendation_type,
            'title': rec.title,
            'description': rec.description,
            'rationale': rec.rationale,
            'suggested_changes': rec.suggested_changes,
            'expected_impact': rec.expected_impact,
            'analysis_data': rec.analysis_data,
            'actual_impact': rec.actual_impact,
            'confidence_score': rec.confidence_score,
            'priority': rec.priority,
            'model_version': rec.model_version,
            'applied': rec.applied,
            'applied_version_id': str(rec.applied_version_id) if rec.applied_version_id else None,
            'applied_at': rec.applied_at,
            'applied_by': rec.applied_by,
            'created_at': rec.created_at
        }
    
    def get_high_confidence_pending(
        self,
        min_confidence: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Get pending recommendations with high confidence scores using ORM
        
        Args:
            min_confidence: Minimum confidence threshold (0.0-1.0)
            
        Returns:
            List of high-confidence pending recommendations
            
        ORM Refactored: Sprint 1.6.1 Task 2.1.4
        """
        from src.optimizer_v3.database.models import AIRecommendation
        
        try:
            recommendations = self.session.query(AIRecommendation).filter(
                AIRecommendation.applied == False,
                AIRecommendation.confidence_score >= min_confidence
            ).order_by(
                AIRecommendation.confidence_score.desc(),
                AIRecommendation.created_at.desc()
            ).all()
            
            return [self._recommendation_to_dict(rec) for rec in recommendations]
            
        except Exception as e:
            self.session.rollback()
            self.logger.error(f"Failed to get high confidence recommendations: {e}")
            return []
    
    def get_effectiveness_stats(self) -> Dict[str, Any]:
        """
        Get statistics on recommendation effectiveness using ORM
        
        Returns:
            Dict with effectiveness metrics including:
            - total_recommendations
            - total_applied
            - total_measured
            - avg_confidence
            - avg_applied_confidence
            - application_rate
            
        ORM Refactored: Sprint 1.6.1 Task 2.1.8
        """
        from src.optimizer_v3.database.models import AIRecommendation
        from sqlalchemy import func, case
        
        try:
            # Build ORM aggregation query
            result = self.session.query(
                func.count(AIRecommendation.recommendation_id).label('total_recommendations'),
                func.count(case((AIRecommendation.applied == True, 1))).label('total_applied'),
                func.count(case((AIRecommendation.actual_impact != None, 1))).label('total_measured'),
                func.avg(AIRecommendation.confidence_score).label('avg_confidence'),
                func.avg(case((AIRecommendation.applied == True, AIRecommendation.confidence_score))).label('avg_applied_confidence')
            ).one()
            
            stats = {
                'total_recommendations': result.total_recommendations or 0,
                'total_applied': result.total_applied or 0,
                'total_measured': result.total_measured or 0,
                'avg_confidence': float(result.avg_confidence) if result.avg_confidence else 0.0,
                'avg_applied_confidence': float(result.avg_applied_confidence) if result.avg_applied_confidence else 0.0
            }
            
            # Calculate application rate
            stats['application_rate'] = (
                stats['total_applied'] / stats['total_recommendations'] 
                if stats['total_recommendations'] > 0 else 0.0
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
