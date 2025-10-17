-- SQL Script to Update Learning Tables Schema
-- Run this in your Supabase SQL Editor to fix the decimal precision issue

-- =====================================================
-- Step 1: Drop views that depend on these columns
-- =====================================================

DROP VIEW IF EXISTS learning_cycle_summary CASCADE;
DROP VIEW IF EXISTS system_performance_trends CASCADE;
DROP VIEW IF EXISTS pending_failure_reviews CASCADE;

-- =====================================================
-- Step 2: Update decimal precision for learning_cycles
-- =====================================================

-- Current: DECIMAL(5, 4) allows max 9.9999 (too small for percentages)
-- New: DECIMAL(6, 2) allows max 9999.99 (enough for percentage scores)

ALTER TABLE learning_cycles 
  ALTER COLUMN accuracy_rate TYPE DECIMAL(5, 2),
  ALTER COLUMN optimization_score TYPE DECIMAL(6, 2);

-- =====================================================
-- Step 3: Update decimal precision for system_improvements
-- =====================================================

ALTER TABLE system_improvements
  ALTER COLUMN before_metric TYPE DECIMAL(6, 2),
  ALTER COLUMN after_metric TYPE DECIMAL(6, 2),
  ALTER COLUMN impact_score TYPE DECIMAL(6, 2);

-- =====================================================
-- Step 4: Recreate the views with updated column types
-- =====================================================

-- View: Learning Cycle Summary
CREATE OR REPLACE VIEW learning_cycle_summary AS
SELECT 
    lc.id,
    lc.trigger_type,
    lc.completed_at,
    lc.feedback_count,
    lc.average_rating,
    lc.accuracy_rate,
    lc.optimization_success,
    COUNT(si.id) as improvements_count,
    AVG(si.impact_score) as avg_impact
FROM learning_cycles lc
LEFT JOIN system_improvements si ON lc.id = si.learning_cycle_id
GROUP BY lc.id, lc.trigger_type, lc.completed_at, lc.feedback_count, 
         lc.average_rating, lc.accuracy_rate, lc.optimization_success
ORDER BY lc.completed_at DESC;

-- View: System Performance Trends
CREATE OR REPLACE VIEW system_performance_trends AS
SELECT 
    DATE(completed_at) as date,
    AVG(average_rating) as avg_rating,
    AVG(accuracy_rate) as avg_accuracy,
    COUNT(*) as cycles_count,
    SUM(CASE WHEN optimization_success THEN 1 ELSE 0 END) as successful_optimizations
FROM learning_cycles
GROUP BY DATE(completed_at)
ORDER BY date DESC;

-- View: Pending Reviews
CREATE OR REPLACE VIEW pending_failure_reviews AS
SELECT 
    fa.id,
    fa.user_question,
    fa.failure_reason,
    fa.improvements_needed,
    fa.should_add_to_kb,
    fa.suggested_correction,
    fa.created_at,
    f.rating as original_rating,
    f.user_feedback
FROM failure_analysis fa
LEFT JOIN feedback f ON fa.feedback_id = f.id
WHERE fa.status = 'pending_review'
ORDER BY fa.created_at DESC;

-- =====================================================
-- Step 5: Verify Changes
-- =====================================================

SELECT 
  table_name, 
  column_name, 
  data_type, 
  numeric_precision, 
  numeric_scale
FROM information_schema.columns
WHERE table_name IN ('learning_cycles', 'system_improvements')
  AND column_name IN ('accuracy_rate', 'optimization_score', 'before_metric', 'after_metric', 'impact_score')
ORDER BY table_name, column_name;

-- Expected output:
-- learning_cycles | accuracy_rate | numeric | 5 | 2
-- learning_cycles | optimization_score | numeric | 6 | 2
-- system_improvements | before_metric | numeric | 6 | 2
-- system_improvements | after_metric | numeric | 6 | 2
-- system_improvements | impact_score | numeric | 6 | 2

COMMENT ON COLUMN learning_cycles.optimization_score IS 'DSPy optimization score as percentage (0-100), DECIMAL(6,2) allows up to 9999.99%';
COMMENT ON COLUMN learning_cycles.accuracy_rate IS 'Answer accuracy rate as percentage (0-100), DECIMAL(5,2) allows up to 999.99%';
