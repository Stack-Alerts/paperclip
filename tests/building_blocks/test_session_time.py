"""
Unit tests for Session Time Building Block
"""

import pytest
import pandas as pd
from datetime import datetime
from src.detectors.building_blocks.sessions.session_time import SessionTime


@pytest.fixture
def sample_data_asia():
    return pd.DataFrame({'timestamp': [datetime(2024, 1, 1, 4, 0)]})  # 04:00 UTC = Asia

@pytest.fixture
def sample_data_london():
    return pd.DataFrame({'timestamp': [datetime(2024, 1, 1, 10, 0)]})  # 10:00 UTC = London

@pytest.fixture
def sample_data_overlap():
    return pd.DataFrame({'timestamp': [datetime(2024, 1, 1, 14, 0)]})  # 14:00 UTC = Overlap


class TestInitialization:
    def test_default(self):
        session = SessionTime()
        assert session.timeframe == '15min'


class TestSessionIdentification:
    def test_asia_session(self, sample_data_asia):
        session = SessionTime()
        result = session.analyze(sample_data_asia)
        assert result['metadata']['session'] == 'ASIA'
    
    def test_london_session(self, sample_data_london):
        session = SessionTime()
        result = session.analyze(sample_data_london)
        assert result['metadata']['session'] == 'LONDON'
    
    def test_overlap_session(self, sample_data_overlap):
        session = SessionTime()
        result = session.analyze(sample_data_overlap)
        assert result['metadata']['session'] == 'LONDON_NY_OVERLAP'


class TestAnalysis:
    def test_standardized_format(self, sample_data_asia):
        session = SessionTime()
        result = session.analyze(sample_data_asia)
        assert all(k in result for k in ['signal', 'confidence', 'metadata'])
    
    def test_quiet_session(self, sample_data_asia):
        session = SessionTime()
        result = session.analyze(sample_data_asia)
        assert result['signal'] == 'QUIET'
    
    def test_active_session(self, sample_data_london):
        session = SessionTime()
        result = session.analyze(sample_data_london)
        assert result['signal'] == 'ACTIVE'


class TestValidation:
    def test_missing_timestamp(self):
        session = SessionTime()
        assert session.analyze(pd.DataFrame({'wrong': [1]}))['signal'] == 'ERROR'


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
