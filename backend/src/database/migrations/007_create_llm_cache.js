module.exports = {
  name: '007_create_llm_cache',
  async up(pool) {
    await pool.query(`
      CREATE TABLE IF NOT EXISTS llm_cache (
        id SERIAL PRIMARY KEY,
        hash VARCHAR(32) NOT NULL UNIQUE,
        code_snippet TEXT,
        prompt TEXT,
        result VARCHAR(20),
        confidence NUMERIC(3,2),
        tokens_used INTEGER,
        created_at TIMESTAMP DEFAULT NOW()
      );
    `);
  },
};
