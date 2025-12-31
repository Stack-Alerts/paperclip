"""
Unit tests for Kill Zones Building Block
"""

import pytest
import pandas as pd
from datetime import datetime
from src.detectors.building_blocks.sessions.kill_zones import KillZones


@pytest.fixture
def sample_data_ny_am():
    return pd.DataFrame({'timestamp': [datetime(2024, 1, 1, 13, 0)]})  # 13:00 UTC = NY AM KZ

@pytest.fixture
def sample_data_london():
    return pd.DataFrame({'timestamp': [datetime(2024, 1, 1, 8, 0)]})  # 08:00 UTC = London KZ

@pytest.fixture
def sample_data_no_kz():
    return pd.DataFrame({'timestamp': [datetime(2024, 1, 1, 11, 0)]})  # 11:00 UTC = No KZ


class TestInitialization:
    def test_default(self):
        kz = KillZones()
        assert kz.timeframe == '15min'


class TestKillZoneIdentification:
    def test_ny_am_kz(self, sample_data_ny_am):
        kz = KillZones()
        result = kz.analyze(sample_data_ny_am)
        assert result['metadata']['kill_zone'] == 'NY_AM_KZ'
        assert result['metadata']['priority'] == 'VERY_HIGH'
    
    def test_london_kz(self, sample_data_london):
        kz = KillZones()
        result = kz.analyze(sample_data_london)
        assert result['metadata']['kill_zone'] == 'LONDON_KZ'
        assert result['metadata']['priority'] == 'HIGH'
    
    def test_no_kz(self, sample_data_no_kz):
        kz = KillZones()
        result = kz.analyze(sample_data_no_kz)
        assert result['metadata']['kill_zone'] == 'NO_KZ'


class TestAnalysis:
    def test_standardized_format(self, sample_data_ny_am):
        kz = KillZones()
        result = kz.analyze(sample_data_ny_am)
        assert all(k in result for k in ['signal', 'confidence', 'metadata'])
    
    def test_prime_time_signal(self, sample_data_ny_am):
        kz = KillZones()
        result = kz.analyze(sample_data_ny_am)
        assert result['signal'] == 'PRIME_TIME'
    
    def test_wait_signal(self, sample_data_no_kz):
        kz = KillZones()
        result = kz.analyze(sample_data_no_kz)
        assert result['signal'] == 'WAIT'


class TestValidation:
    def test_missing_timestamp(self):
        kz = KillZones()
        assert kz.analyze(pd.DataFrame({'wrong': [1]}))['signal'] == 'ERROR'


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
