module.exports = {
  name: '006_create_pattern_migrations',
  async up(pool) {
    await pool.query(`
      CREATE TABLE IF NOT EXISTS pattern_migrations (
        id SERIAL PRIMARY KEY,
        repo_id INTEGER NOT NULL REFERENCES repos(id),
        pattern_id VARCHAR(100) NOT NULL,
        added_commit_sha VARCHAR(40) NOT NULL,
        removed_commit_sha VARCHAR(40) NOT NULL,
        added_date TIMESTAMP,
        removed_date TIMESTAMP,
        days_to_removal INTEGER,
        file_path TEXT,
        created_at TIMESTAMP DEFAULT NOW(),
        UNIQUE(repo_id, pattern_id, added_commit_sha, removed_commit_sha)
      );
    `);
  },
};
