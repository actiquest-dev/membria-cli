const fs = require('fs');
const path = require('path');
const yaml = require('js-yaml');

let compiledPatterns = null;

function loadPatternConfigs() {
  if (compiledPatterns) return compiledPatterns;

  const configPath = path.join(__dirname, '../../config/patterns.yaml');
  const raw = fs.readFileSync(configPath, 'utf8');
  const config = yaml.load(raw);

  compiledPatterns = Object.entries(config.patterns).map(([id, pattern]) => {
    const detection = pattern.detection;

    return {
      id,
      name: pattern.name,
      category: pattern.category,
      severity: pattern.severity,
      languages: pattern.languages,
      detection: {
        regex_include: (detection.regex_include || []).map(r => new RegExp(r, 'i')),
        regex_exclude: (detection.regex_exclude || []).map(r => new RegExp(r, 'i')),
        ast_query: detection.ast_query || null,
        requires_import: detection.requires_import || [],
        excludes_import: detection.excludes_import || [],
        llm_prompt: detection.llm_prompt || null,
      },
      evidence: pattern.evidence,
    };
  });

  return compiledPatterns;
}

module.exports = { loadPatternConfigs };
