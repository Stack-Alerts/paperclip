-- Delete the orphaned strategy from failed save
DELETE FROM strategies WHERE strategy_id = 'strategy_967a7319';

-- Verify it's gone
SELECT strategy_id, name FROM strategies ORDER BY updated_at DESC;
