require('dotenv').config();
const fs = require('fs');
const path = require('path');
const { pool } = require('../utils/database');

async function ensureMigrationsTable() {
  await pool.query(`
    CREATE TABLE IF NOT EXISTS _migrations (
      id SERIAL PRIMARY KEY,
      name VARCHAR(255) NOT NULL UNIQUE,
      applied_at TIMESTAMP DEFAULT NOW()
    );
  `);
}

async function getAppliedMigrations() {
  const result = await pool.query('SELECT name FROM _migrations ORDER BY id');
  return new Set(result.rows.map(r => r.name));
}

async function migrate() {
  try {
    await ensureMigrationsTable();
    const applied = await getAppliedMigrations();

    const migrationsDir = path.join(__dirname, 'migrations');
    const files = fs.readdirSync(migrationsDir)
      .filter(f => f.endsWith('.js'))
      .sort();

    for (const file of files) {
      const migration = require(path.join(migrationsDir, file));

      if (applied.has(migration.name)) {
        continue;
      }

      console.log(`Running migration: ${migration.name}`);
      await migration.up(pool);
      await pool.query('INSERT INTO _migrations (name) VALUES ($1)', [migration.name]);
      console.log(`  Applied: ${migration.name}`);
    }

    console.log('Database migrations complete');
    await pool.end();
  } catch (error) {
    console.error('Migration error:', error);
    process.exit(1);
  }
}

migrate();
