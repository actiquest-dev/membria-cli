const axios = require('axios');
const pool = require('./utils/database').pool;

const PAGEINDEX_URL = 'http://127.0.0.1:5000';

module.exports = function(app) {
  app.post('/api/chat', async (req, res) => {
    try {
      const { message } = req.body;
      if (!message) return res.status(400).json({ error: 'Message required' });

      console.log('[Chat]', message.substring(0, 80));

      // Run DB context + PageIndex RAG in parallel
      const [dbContext, ragContext] = await Promise.allSettled([
        getDBContext(),
        queryPageIndex(message),
      ]);

      const db = dbContext.status === 'fulfilled' ? dbContext.value : '';
      const rag = ragContext.status === 'fulfilled' ? ragContext.value : null;

      // Build system prompt with both contexts
      let systemPrompt = `You are Membria AI — an expert assistant for code antipattern analysis and cognitive bias debiasing in software development.

You have two knowledge sources:
1. **Database** — antipatterns detected in GitHub repos (pre-AI vs AI-era comparison)
2. **Research documents** — cognitive biases, decision making, debiasing research papers

Always format your response using Markdown:
- Use **bold** for emphasis
- Use ### headers for sections
- Use bullet lists and numbered lists
- Use \`code\` for technical terms
- Use > blockquotes for citations from research

Answer in the same language as the user's question.

## Database Context
${db}`;

      if (rag && rag.context) {
        systemPrompt += `\n\n## Research Documents Context\n${rag.context}`;
      }

      // Call GLM-4.5-Air
      const apiKey = process.env.GLM4_API_KEY;
      const apiUrl = (process.env.GLM4_API_URL || 'https://api.z.ai/api/coding/paas/v4') + '/chat/completions';

      if (!apiKey) return res.status(500).json({ error: 'GLM API not configured' });

      const glmResponse = await axios.post(apiUrl, {
        model: 'GLM-4.5-Air',
        messages: [
          { role: 'system', content: systemPrompt },
          { role: 'user', content: message },
        ],
        temperature: 0.7,
        max_tokens: 8000,
      }, {
        headers: {
          'Authorization': `Bearer ${apiKey}`,
          'Content-Type': 'application/json',
        },
        timeout: 120000,
      });

      const msg = glmResponse.data?.choices?.[0]?.message;
      let reply = msg?.content || msg?.reasoning_content || 'No response';

      // Append RAG sources if available
      if (rag && rag.sources && rag.sources.length > 0) {
        reply += '\n\n---\n\n**📚 Sources:**\n';
        rag.sources.forEach((s, i) => {
          reply += `\n${i + 1}. **${s.document}** — ${s.title}`;
        });
      }

      const tokens = glmResponse.data?.usage?.total_tokens || 0;
      res.json({ response: { reply, tokens } });

    } catch (error) {
      console.error('[Chat Error]', error.message);
      if (error.response?.data) console.error('[GLM]', JSON.stringify(error.response.data).slice(0, 300));
      res.status(500).json({ error: error.message });
    }
  });
};

async function getDBContext() {
  try {
    const [stats, byPattern, byEra, recent] = await Promise.all([
      pool.query(`SELECT 
        (SELECT COUNT(*) FROM repos) as repos,
        (SELECT COUNT(*) FROM commits) as commits,
        (SELECT COUNT(*) FROM pattern_occurrences) as occurrences`),
      pool.query(`SELECT pattern_id, action, COUNT(*) as cnt 
        FROM pattern_occurrences GROUP BY pattern_id, action ORDER BY cnt DESC LIMIT 20`),
      pool.query(`SELECT COALESCE(metadata->>'era', 'unknown') as era, COUNT(*) as repos,
        COALESCE(SUM(stars), 0) as stars FROM repos GROUP BY metadata->>'era'`),
      pool.query(`SELECT po.pattern_id, po.action, po.confidence, r.full_name, r.language
        FROM pattern_occurrences po JOIN repos r ON r.id = po.repo_id
        ORDER BY po.created_at DESC LIMIT 5`),
    ]);

    const s = stats.rows[0];
    const lines = [
      `Repos: ${s.repos}, Commits: ${s.commits}, Antipatterns detected: ${s.occurrences}`,
      `Eras: ${byEra.rows.map(r => `${r.era}: ${r.repos} repos (${r.stars} stars)`).join(', ')}`,
      `Top patterns: ${byPattern.rows.map(r => `${r.pattern_id}(${r.action}): ${r.cnt}`).join(', ')}`,
      `Recent: ${recent.rows.map(r => `${r.pattern_id} in ${r.full_name}[${r.language}]`).join('; ')}`,
    ];
    return lines.join('\n');
  } catch (e) {
    console.error('[DB Context Error]', e.message);
    return 'Database context unavailable';
  }
}

async function queryPageIndex(question) {
  try {
    const response = await axios.post(`${PAGEINDEX_URL}/query`, {
      question: question,
      top_k: 3,
    }, { timeout: 120000 });

    const data = response.data;
    return {
      context: data.answer ? data.answer.slice(0, 3000) : '',
      sources: data.sources || [],
    };
  } catch (e) {
    console.log('[PageIndex]', e.message);
    return null;
  }
}
