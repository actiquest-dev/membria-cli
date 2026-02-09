module.exports = {
  name: '002_create_repos',
  async up(pool) {
    await pool.query(`
      CREATE TABLE IF NOT EXISTS repos (
        id SERIAL PRIMARY KEY,
        owner VARCHAR(255) NOT NULL,
        name VARCHAR(255) NOT NULL,
        full_name VARCHAR(511) NOT NULL UNIQUE,
        stars INTEGER DEFAULT 0,
        forks INTEGER DEFAULT 0,
        language VARCHAR(50),
        priority_score NUMERIC(10,2) DEFAULT 0,
        last_fetched_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT NOW()
      );
      CREATE INDEX IF NOT EXISTS idx_repos_full_name ON repos(full_name);
    `);
  },
};
