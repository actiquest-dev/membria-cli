module.exports = {
  name: '003_create_commits',
  async up(pool) {
    await pool.query(`
      CREATE TABLE IF NOT EXISTS commits (
        id SERIAL PRIMARY KEY,
        sha VARCHAR(40) NOT NULL,
        repo_id INTEGER NOT NULL REFERENCES repos(id),
        message TEXT,
        author VARCHAR(255),
        date TIMESTAMP,
        diff_text TEXT,
        files_changed JSONB DEFAULT '[]',
        processed BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT NOW(),
        UNIQUE(sha, repo_id)
      );
      CREATE INDEX IF NOT EXISTS idx_commits_processed ON commits(processed) WHERE processed = FALSE;
      CREATE INDEX IF NOT EXISTS idx_commits_repo_id ON commits(repo_id);
    `);
  },
};
