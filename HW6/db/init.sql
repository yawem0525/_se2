CREATE TABLE IF NOT EXISTS system_logs (
    id SERIAL PRIMARY KEY,
    message VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO system_logs (message) VALUES 
('System initialization verified'),
('PostgreSQL connected with Docker volume mount');
