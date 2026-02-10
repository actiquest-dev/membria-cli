const pool = require('./connection');

class Commit {
  static async create(data) {
    const query = `
      INSERT INTO commits (sha, repo_id, message, author, date, diff_text, files_changed, processed)
      VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
      ON CONFLICT (sha, repo_id) DO NOTHING
      RETURNING id
    `;

    const values = [
      data.sha,
      data.repoId,
      data.message,
      data.author || 'unknown',
      data.date || null,
      data.diffText || null,
      data.filesChanged ? JSON.stringify(data.filesChanged) : null,
      false
    ];

    const result = await pool.query(query, values);
    return result.rows[0]?.id || null;
  }

  static async getByRepo(repoId, limit = 100) {
    const query = `
      SELECT * FROM commits
      WHERE repo_id = $1
      ORDER BY date DESC
      LIMIT $2
    `;
    const result = await pool.query(query, [repoId, limit]);
    return result.rows;
  }

  static async countByRepo(repoId) {
    const result = await pool.query(
      'SELECT COUNT(*) FROM commits WHERE repo_id = $1',
      [repoId]
    );
    return parseInt(result.rows[0].count);
  }

  static async countTotal() {
    const result = await pool.query('SELECT COUNT(*) FROM commits');
    return parseInt(result.rows[0].count);
  }

  static async getUnprocessed(limit = 1000) {
    const query = `
      SELECT c.* FROM commits c
      JOIN repos r ON c.repo_id = r.id
      WHERE c.processed = FALSE
      ORDER BY r.priority_score DESC NULLS LAST, c.date DESC
      LIMIT $1
    `;
    const result = await pool.query(query, [limit]);
    return result.rows;
  }

  static async markProcessed(sha, repoId) {
    await pool.query(
      'UPDATE commits SET processed = TRUE WHERE sha = $1 AND repo_id = $2',
      [sha, repoId]
    );
  }
}

module.exports = Commit;
