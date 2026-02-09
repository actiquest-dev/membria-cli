module.exports = {
  name: '004_create_pattern_definitions',
  async up(pool) {
    await pool.query(`
      CREATE TABLE IF NOT EXISTS pattern_definitions (
        id VARCHAR(100) PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        category VARCHAR(50),
        severity VARCHAR(20),
        repos_affected INTEGER DEFAULT 0,
        total_occurrences INTEGER DEFAULT 0,
        removal_count INTEGER DEFAULT 0,
        failure_rate NUMERIC(5,4) DEFAULT 0,
        avg_days_to_removal NUMERIC(10,2),
        median_days_to_removal NUMERIC(10,2),
        last_updated TIMESTAMP DEFAULT NOW(),
        created_at TIMESTAMP DEFAULT NOW()
      );
    `);
  },
};
