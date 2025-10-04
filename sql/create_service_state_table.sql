-- Service State Table for Render.com Deployment
-- Replaces ephemeral file-based state storage
-- Run this in Supabase SQL Editor before deploying to Render.com

CREATE TABLE IF NOT EXISTS service_state (
    service_name TEXT PRIMARY KEY,
    state_data JSONB NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add index for performance
CREATE INDEX IF NOT EXISTS idx_service_state_updated ON service_state(updated_at);

-- Grant permissions
GRANT ALL ON service_state TO authenticated;
GRANT ALL ON service_state TO service_role;

-- Insert example state structure (optional - for documentation)
INSERT INTO service_state (service_name, state_data)
VALUES (
    'example_service',
    '{
        "last_run": "2025-10-02T00:00:00Z",
        "status": "running",
        "progress": {
            "total": 100,
            "completed": 50
        }
    }'::jsonb
) ON CONFLICT (service_name) DO NOTHING;

-- Verify table creation
SELECT
    'service_state table created successfully' AS status,
    COUNT(*) as example_records
FROM service_state;
