const axios = require('axios');
const pool = require('./utils/database').pool;

const PAGEINDEX_URL = 'http://127.0.0.1:5000';

module.exports = function(app) {
  app.post('/api/chat', async (req, res) => {
    try {
      const { message } = req.body;
      if (!message) return res.status(400).json({ error: 'Message required' });

      console.log('[Chat]', message.substring(0, 80));

      // Run DB context + PageIndex keyword search in parallel (both instant)
      const [dbContext, ragContext] = await Promise.allSettled([
        getDBContext(),
        queryPageIndex(message),
      ]);

      const db = dbContext.status === 'fulfilled' ? dbContext.value : '';
      const rag = ragContext.status === 'fulfilled' ? ragContext.value : null;

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
        systemPrompt += '\n\n## Research Documents Context\n' + rag.context;
      }

      // Single GLM call with both contexts
      const apiKey = process.env.GLM4_API_KEY;
      const apiUrl = (process.env.GLM4_API_URL || 'https://api.z.ai/api/coding/paas/v4') + '/chat/completions';
      if (!apiKey) return res.status(500).json({ error: 'GLM API not configured' });

      const glmResponse = await axios.post(apiUrl, {
        model: 'glm-4-plus',
        messages: [
          { role: 'system', content: systemPrompt },
          { role: 'user', content: message },
        ],
        temperature: 0.7,
        max_tokens: 8000,
      }, {
        headers: {
          'Authorization': 'Bearer ' + apiKey,
          'Content-Type': 'application/json',
        },
        timeout: 120000,
      });

      const msg = glmResponse.data?.choices?.[0]?.message;
      let reply = msg?.content || msg?.reasoning_content || 'No response';

      // Append RAG sources
      if (rag && rag.sources && rag.sources.length > 0) {
        reply += '\n\n---\n\n**Sources:**\n';
        rag.sources.forEach((s, i) => {
          reply += '\n' + (i + 1) + '. **' + s.document + '** — ' + s.title;
        });
      }

      const tokens = glmResponse.data?.usage?.total_tokens || 0;
      res.json({ response: { reply, tokens } });

    } catch (error) {
      console.error('[Chat Error]', error.message);
      res.status(500).json({ error: error.message });
    }
  });
};

async function getDBContext() {
  try {
    const [stats, byPattern, byEra, recent] = await Promise.all([
      pool.query('SELECT (SELECT COUNT(*) FROM repos) as repos, (SELECT COUNT(*) FROM commits) as commits, (SELECT COUNT(*) FROM pattern_occurrences) as occurrences'),
      pool.query('SELECT pattern_id, action, COUNT(*) as cnt FROM pattern_occurrences GROUP BY pattern_id, action ORDER BY cnt DESC LIMIT 20'),
      pool.query("SELECT COALESCE(metadata->>'era', 'unknown') as era, COUNT(*) as repos, COALESCE(SUM(stars), 0) as stars FROM repos GROUP BY metadata->>'era'"),
      pool.query('SELECT po.pattern_id, po.action, po.confidence, r.full_name, r.language FROM pattern_occurrences po JOIN repos r ON r.id = po.repo_id ORDER BY po.created_at DESC LIMIT 5'),
    ]);
    const s = stats.rows[0];
    return [
      'Repos: ' + s.repos + ', Commits: ' + s.commits + ', Antipatterns: ' + s.occurrences,
      'Eras: ' + byEra.rows.map(r => r.era + ': ' + r.repos + ' repos (' + r.stars + ' stars)').join(', '),
      'Patterns: ' + byPattern.rows.map(r => r.pattern_id + '(' + r.action + '): ' + r.cnt).join(', '),
      'Recent: ' + recent.rows.map(r => r.pattern_id + ' in ' + r.full_name + '[' + r.language + ']').join('; '),
    ].join('\n');
  } catch (e) {
    console.error('[DB Error]', e.message);
    return 'Database unavailable';
  }
}

async function queryPageIndex(question) {
  try {
    // Use /search (keyword TF-IDF, no LLM) — instant response
    const response = await axios.post(PAGEINDEX_URL + '/search', {
      question: question,
      top_k: 3,
    }, { timeout: 5000 });

    const results = response.data.results || [];
    if (results.length === 0) return null;

    const context = results.map(function(r) {
      return r.document + ' - ' + r.title + ':\n' + (r.content || '').slice(0, 1500);
    }).join('\n\n').slice(0, 3000);

    const sources = results.map(function(r) {
      return { document: r.document, title: r.title };
    });

    return { context: context, sources: sources };
  } catch (e) {
    console.log('[PageIndex]', e.message);
    return null;
  }
}
