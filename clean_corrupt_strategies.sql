-- INSTITUTIONAL-GRADE FIX: Remove corrupt strategies
-- These 3 strategies are causing InFailedSqlTransaction errors

DELETE FROM strategy_versions WHERE strategy_id = 'strategy_35a2c8a2';
DELETE FROM strategies WHERE strategy_id = 'strategy_35a2c8a2';

DELETE FROM strategy_versions WHERE strategy_id = 'strategy_aa2bb7c5';
DELETE FROM strategies WHERE strategy_id = 'strategy_aa2bb7c5';

DELETE FROM strategy_versions WHERE strategy_id = 'strategy_86206819';
DELETE FROM strategies WHERE strategy_id = 'strategy_86206819';

-- Verify clean state
SELECT strategy_id, name FROM strategies ORDER BY updated_at DESC;
