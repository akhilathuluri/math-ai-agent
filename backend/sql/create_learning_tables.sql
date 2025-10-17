-- SQL Script to Create Tables for Human-in-the-Loop Learning System
-- Run this in your Supabase SQL Editor

-- =====================================================
-- Table: failure_analysis
-- Purpose: Store immediate analysis of low-rated responses
-- =====================================================
CREATE TABLE IF NOT EXISTS failure_analysis (
    id SERIAL PRIMARY KEY,
    feedback_id INTEGER REFERENCES feedback(id) ON DELETE CASCADE,
    user_question TEXT NOT NULL,
    failure_reason TEXT,
    improvements_needed TEXT,
    should_add_to_kb BOOLEAN DEFAULT FALSE,
    suggested_correction TEXT,
    status VARCHAR(50) DEFAULT 'pending_review',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    reviewed_at TIMESTAMP WITH TIME ZONE,
    reviewed_by VARCHAR(255)
);

-- Index for faster queries
CREATE INDEX IF NOT EXISTS idx_failure_analysis_status ON failure_analysis(status);
CREATE INDEX IF NOT EXISTS idx_failure_analysis_created_at ON failure_analysis(created_at DESC);

-- =====================================================
-- Table: learning_cycles
-- Purpose: Track learning cycle executions and metrics
-- =====================================================
CREATE TABLE IF NOT EXISTS learning_cycles (
    id SERIAL PRIMARY KEY,
    trigger_type VARCHAR(50) NOT NULL, -- 'daily_scheduled', 'feedback_count_100', 'manual'
    completed_at TIMESTAMP WITH TIME ZONE NOT NULL,
    feedback_count INTEGER DEFAULT 0,
    average_rating DECIMAL(3, 2) DEFAULT 0.0,
    accuracy_rate DECIMAL(5, 2) DEFAULT 0.0,
    suggestions_count INTEGER DEFAULT 0,
    optimization_success BOOLEAN DEFAULT FALSE,
    optimization_score DECIMAL(6, 2) DEFAULT 0.0,
    training_examples INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for faster queries
CREATE INDEX IF NOT EXISTS idx_learning_cycles_completed_at ON learning_cycles(completed_at DESC);
CREATE INDEX IF NOT EXISTS idx_learning_cycles_trigger_type ON learning_cycles(trigger_type);

-- =====================================================
-- Table: system_improvements
-- Purpose: Track specific improvements made by the system
-- =====================================================
CREATE TABLE IF NOT EXISTS system_improvements (
    id SERIAL PRIMARY KEY,
    learning_cycle_id INTEGER REFERENCES learning_cycles(id) ON DELETE CASCADE,
    improvement_type VARCHAR(100) NOT NULL, -- 'prompt_optimization', 'kb_addition', 'routing_improvement', etc.
    description TEXT NOT NULL,
    before_metric DECIMAL(6, 2),
    after_metric DECIMAL(6, 2),
    impact_score DECIMAL(6, 2),
    details JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for faster queries
CREATE INDEX IF NOT EXISTS idx_system_improvements_cycle_id ON system_improvements(learning_cycle_id);
CREATE INDEX IF NOT EXISTS idx_system_improvements_type ON system_improvements(improvement_type);

-- =====================================================
-- Views for Analytics
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
-- Comments
-- =====================================================

COMMENT ON TABLE failure_analysis IS 'Stores immediate AI analysis of failed responses (rating <= 2)';
COMMENT ON TABLE learning_cycles IS 'Tracks each learning cycle execution with metrics and results';
COMMENT ON TABLE system_improvements IS 'Records specific improvements made during learning cycles';

COMMENT ON COLUMN learning_cycles.trigger_type IS 'What triggered this cycle: daily_scheduled, feedback_count_100, or manual';
COMMENT ON COLUMN learning_cycles.optimization_success IS 'Whether DSPy optimization completed successfully';
COMMENT ON COLUMN failure_analysis.status IS 'Review status: pending_review, reviewed, resolved, dismissed';

-- =====================================================
-- Grant Permissions (adjust as needed for your setup)
-- =====================================================

-- If using Row Level Security (RLS), you may need to enable it:
-- ALTER TABLE failure_analysis ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE learning_cycles ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE system_improvements ENABLE ROW LEVEL SECURITY;

-- Example policy (adjust for your auth setup):
-- CREATE POLICY "Enable read access for authenticated users" ON learning_cycles
--   FOR SELECT USING (auth.role() = 'authenticated');

COMMENT ON DATABASE postgres IS 'Math Agent - Human-in-the-Loop Learning System';
