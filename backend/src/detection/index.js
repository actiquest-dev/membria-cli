const { RegexFilter } = require('./regex-filter');
const { ASTAnalyzer } = require('./ast-analyzer');
const { ContextValidator } = require('./context-validator');
const { LLMValidator } = require('./llm-validator');

class PatternDetector {
  constructor(redis) {
    this.astAnalyzer = new ASTAnalyzer();
    this.llmValidator = new LLMValidator(redis);
  }

  async detect(code, language, patternConfig) {
    // Stage 1: Regex filter
    const regexResult = RegexFilter.check(code, patternConfig.detection);

    if (regexResult === 'NO_MATCH') {
      return {
        pattern_id: patternConfig.id,
        detected: false,
        confidence: 0.9,
        method: 'regex',
        matches: [],
      };
    }

    const matches = RegexFilter.extractMatches(code, patternConfig.detection.regex_include);

    // Stage 2: AST analysis (stub — returns [] in Phase 1)
    const astMatches = this.astAnalyzer.analyze(code, language, patternConfig.detection.ast_query);

    if (astMatches.length > 0) {
      // Stage 3: Context validation (stub — returns true in Phase 1)
      const contextValid = ContextValidator.validate(code, {
        requires_import: patternConfig.detection.requires_import,
        excludes_import: patternConfig.detection.excludes_import,
      });

      if (!contextValid) {
        return {
          pattern_id: patternConfig.id,
          detected: false,
          confidence: 0.9,
          method: 'context',
          matches: [],
        };
      }
    }

    // Phase 1: regex match is enough to detect
    return {
      pattern_id: patternConfig.id,
      detected: true,
      confidence: 0.6,
      method: 'regex',
      matches,
    };
  }
}

module.exports = { PatternDetector };
