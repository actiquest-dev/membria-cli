module.exports = {
  name: '001_create_patterns',
  async up(pool) {
    await pool.query(`
      CREATE TABLE IF NOT EXISTS patterns (
        id SERIAL PRIMARY KEY,
        owner VARCHAR(255) NOT NULL,
        repo VARCHAR(255) NOT NULL,
        sha VARCHAR(255) NOT NULL UNIQUE,
        issues JSONB DEFAULT '[]',
        created_at TIMESTAMP DEFAULT NOW()
      );
    `);
  },
};
