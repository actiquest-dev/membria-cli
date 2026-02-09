module.exports = {
  name: '005_create_pattern_occurrences',
  async up(pool) {
    await pool.query(`
      CREATE TABLE IF NOT EXISTS pattern_occurrences (
        id SERIAL PRIMARY KEY,
        commit_sha VARCHAR(40) NOT NULL,
        repo_id INTEGER NOT NULL REFERENCES repos(id),
        pattern_id VARCHAR(100) NOT NULL,
        action VARCHAR(10) NOT NULL CHECK (action IN ('add', 'remove')),
        file_path TEXT,
        line_number INTEGER,
        confidence NUMERIC(3,2),
        detection_method VARCHAR(20),
        match_text TEXT,
        created_at TIMESTAMP DEFAULT NOW()
      );
      CREATE INDEX IF NOT EXISTS idx_occurrences_repo_pattern ON pattern_occurrences(repo_id, pattern_id);
      CREATE INDEX IF NOT EXISTS idx_occurrences_commit ON pattern_occurrences(commit_sha);
    `);
  },
};
