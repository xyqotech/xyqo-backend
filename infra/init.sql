-- AUTOPILOT Database Initialization
-- Tables et index pour PostgreSQL

-- Extension pour UUID si nécessaire
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Table des sessions de démonstration
CREATE TABLE IF NOT EXISTS demo_sessions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(16) UNIQUE NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_size INTEGER NOT NULL,
    file_hash VARCHAR(64),
    extraction_success BOOLEAN DEFAULT FALSE,
    jira_ticket_created BOOLEAN DEFAULT FALSE,
    jira_ticket_key VARCHAR(50),
    quality_score FLOAT,
    latency_ms INTEGER,
    error_message TEXT,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index pour performances
CREATE INDEX IF NOT EXISTS idx_demo_sessions_session_id ON demo_sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_demo_sessions_file_hash ON demo_sessions(file_hash);
CREATE INDEX IF NOT EXISTS idx_demo_sessions_created_at ON demo_sessions(created_at);
CREATE INDEX IF NOT EXISTS idx_demo_sessions_success ON demo_sessions(extraction_success);

-- Table pour cache des extractions (optionnel, Redis prioritaire)
CREATE TABLE IF NOT EXISTS extraction_cache (
    id SERIAL PRIMARY KEY,
    file_hash VARCHAR(64) UNIQUE NOT NULL,
    extraction_result JSONB NOT NULL,
    confidence_score FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    access_count INTEGER DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_extraction_cache_hash ON extraction_cache(file_hash);
CREATE INDEX IF NOT EXISTS idx_extraction_cache_accessed ON extraction_cache(accessed_at);

-- Table pour métriques qualité (historique)
CREATE TABLE IF NOT EXISTS quality_metrics (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    total_extractions INTEGER DEFAULT 0,
    successful_extractions INTEGER DEFAULT 0,
    avg_confidence_score FLOAT,
    avg_latency_ms INTEGER,
    jira_tickets_created INTEGER DEFAULT 0,
    total_cost_eur FLOAT DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_quality_metrics_date ON quality_metrics(date);

-- Vues pour analytics rapides
CREATE OR REPLACE VIEW daily_stats AS
SELECT 
    DATE(created_at) as date,
    COUNT(*) as total_sessions,
    COUNT(*) FILTER (WHERE extraction_success = true) as successful_extractions,
    COUNT(*) FILTER (WHERE jira_ticket_created = true) as jira_tickets,
    AVG(quality_score) FILTER (WHERE quality_score IS NOT NULL) as avg_quality,
    AVG(latency_ms) as avg_latency_ms
FROM demo_sessions 
GROUP BY DATE(created_at)
ORDER BY date DESC;

-- Fonction pour nettoyer les anciennes données
CREATE OR REPLACE FUNCTION cleanup_old_data() RETURNS void AS $$
BEGIN
    -- Supprimer sessions > 30 jours
    DELETE FROM demo_sessions 
    WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '30 days';
    
    -- Supprimer cache > 7 jours non utilisé
    DELETE FROM extraction_cache 
    WHERE accessed_at < CURRENT_TIMESTAMP - INTERVAL '7 days';
    
    -- Garder métriques qualité 1 an
    DELETE FROM quality_metrics 
    WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '1 year';
END;
$$ LANGUAGE plpgsql;

-- Données de test pour la démo
INSERT INTO demo_sessions (
    session_id, file_name, file_size, file_hash,
    extraction_success, jira_ticket_created, jira_ticket_key,
    quality_score, latency_ms, created_at
) VALUES 
    ('demo001', 'contrat_service.pdf', 245760, 'hash001', true, true, 'DEMO-1', 0.92, 6200, CURRENT_TIMESTAMP - INTERVAL '2 hours'),
    ('demo002', 'bon_commande.docx', 156432, 'hash002', true, true, 'DEMO-2', 0.88, 5800, CURRENT_TIMESTAMP - INTERVAL '1 hour'),
    ('demo003', 'contrat_bail.txt', 12456, 'hash003', true, false, null, 0.75, 7200, CURRENT_TIMESTAMP - INTERVAL '30 minutes')
ON CONFLICT (session_id) DO NOTHING;

-- Privilèges utilisateur
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO autopilot;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO autopilot;
