require('dotenv').config();
const { Pool } = require('pg');

const pool = new Pool({
  host: process.env.DB_HOST || 'localhost',
  port: process.env.DB_PORT || 5432,
  database: process.env.DB_NAME || 'membria',
  user: process.env.DB_USER || 'membria',
  password: process.env.DB_PASSWORD,
});

async function migrate() {
  try {
    await pool.query(`
      CREATE TABLE IF NOT EXISTS patterns (
        id SERIAL PRIMARY KEY,
        owner VARCHAR(255) NOT NULL,
        repo VARCHAR(255) NOT NULL,
        sha VARCHAR(255) NOT NULL,
        issues JSONB DEFAULT '[]',
        created_at TIMESTAMP DEFAULT NOW()
      );
    `);

    console.log('✅ Database migrated');
    await pool.end();
  } catch (error) {
    console.error('Migration error:', error);
    process.exit(1);
  }
}

migrate();
