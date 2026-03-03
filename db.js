const Database = require('better-sqlite3');
const db = new Database('llm_dispatcher.db');

// Initialize Database Schema
db.exec(`
    CREATE TABLE IF NOT EXISTS providers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        base_url TEXT,
        api_key TEXT,
        is_active INTEGER DEFAULT 1,
        models TEXT, -- JSON string
        max_requests_per_day INTEGER DEFAULT 1000,
        current_requests_today INTEGER DEFAULT 0,
        last_reset_date TEXT, -- YYYY-MM-DD
        weight INTEGER DEFAULT 1,
        priority INTEGER DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS model_groups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        alias TEXT,
        target_models TEXT -- JSON string
    );

    CREATE TABLE IF NOT EXISTS usage_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        provider_id INTEGER,
        model TEXT,
        prompt_tokens INTEGER DEFAULT 0,
        completion_tokens INTEGER DEFAULT 0,
        total_tokens INTEGER DEFAULT 0,
        timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
        status_code INTEGER
    );
`);

module.exports = db;
