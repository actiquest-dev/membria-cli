const pool = require('./connection');

class Repository {
  static async create(data) {
    const query = `
      INSERT INTO repos (full_name, owner, name, description, stars, forks, language, size, last_pushed_at, archived, forked, topics, priority_score, last_fetched_at)
      VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
      ON CONFLICT (full_name) DO UPDATE SET
        stars = EXCLUDED.stars,
        forks = EXCLUDED.forks,
        language = EXCLUDED.language,
        last_pushed_at = EXCLUDED.last_pushed_at,
        priority_score = EXCLUDED.priority_score,
        updated_at = NOW()
      RETURNING *
    `;

    const values = [
      data.full_name,
      data.owner,
      data.name,
      data.description || null,
      data.stars || 0,
      data.forks || 0,
      data.language || null,
      data.size || null,
      data.pushed_at || null,
      data.archived || false,
      data.fork || false,
      data.topics ? JSON.stringify(data.topics) : null,
      data.priority_score || 0,
      null
    ];

    const result = await pool.query(query, values);
    return result.rows[0];
  }

  static async getRepoByName(owner, name) {
    const result = await pool.query(
      'SELECT * FROM repos WHERE owner = $1 AND name = $2',
      [owner, name]
    );
    return result.rows[0] || null;
  }

  static async getById(id) {
    const result = await pool.query(
      'SELECT * FROM repos WHERE id = $1',
      [id]
    );
    return result.rows[0] || null;
  }

  static async getUnprocessed(limit = 100) {
    const query = `
      SELECT * FROM repos
      WHERE last_fetched_at IS NULL
      ORDER BY priority_score DESC NULLS LAST
      LIMIT $1
    `;
    const result = await pool.query(query, [limit]);
    return result.rows;
  }

  static async getNeedsUpdate(days = 30, limit = 100) {
    const query = `
      SELECT * FROM repos
      WHERE (last_fetched_at IS NULL OR last_fetched_at < NOW() - INTERVAL '${days} days')
      ORDER BY priority_score DESC NULLS LAST
      LIMIT $1
    `;
    const result = await pool.query(query, [limit]);
    return result.rows;
  }

  static async updateLastFetched(repoId) {
    const query = 'UPDATE repos SET last_fetched_at = NOW() WHERE id = $1';
    await pool.query(query, [repoId]);
  }

  static async count() {
    const result = await pool.query('SELECT COUNT(*) FROM repos');
    return parseInt(result.rows[0].count);
  }

  static async getAll() {
    const result = await pool.query('SELECT * FROM repos ORDER BY priority_score DESC NULLS LAST');
    return result.rows;
  }

  static async getStats() {
    const result = await pool.query(`
      SELECT
        COUNT(*) as total_repos,
        COUNT(last_fetched_at) as processed_repos,
        COUNT(*) - COUNT(last_fetched_at) as unprocessed_repos,
        SUM(stars) as total_stars
      FROM repos
    `);
    return result.rows[0];
  }
}

module.exports = Repository;
