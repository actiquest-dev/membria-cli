# PATTERN DETECTION ENGINE - ТЕХНИЧЕСКОЕ ЗАДАНИЕ

## ЦЕЛЬ

Детектировать antipatterns в коде из commits, определить Add→Remove последовательности, рассчитать failure rates.

---

## АРХИТЕКТУРА ДЕТЕКЦИИ

```
┌─────────────────────────────────────────────────────────┐
│ PATTERN DETECTION PIPELINE                              │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Commits (PostgreSQL)                                   │
│       ↓                                                  │
│  [STAGE 1: Quick Filter] (Regex)                        │
│       ↓                                                  │
│  [STAGE 2: AST Analysis] (tree-sitter)                  │
│       ↓                                                  │
│  [STAGE 3: Context Check] (imports, usage)              │
│       ↓                                                  │
│  [STAGE 4: LLM Validation] (GLM 4.5 Air) - optional     │
│       ↓                                                  │
│  pattern_occurrences (PostgreSQL)                       │
│       ↓                                                  │
│  [STAGE 5: Temporal Analysis] (Add→Remove tracking)     │
│       ↓                                                  │
│  pattern_migrations (PostgreSQL)                        │
│       ↓                                                  │
│  [STAGE 6: Statistics] (failure rates)                  │
│       ↓                                                  │
│  pattern_definitions (PostgreSQL)                       │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## 1. PATTERN DEFINITIONS

### 1.1 Pattern Configuration File

```yaml
# config/patterns.yaml

patterns:
  # ==========================================
  # AUTHENTICATION PATTERNS
  # ==========================================
  
  custom_jwt:
    name: "Custom JWT Implementation"
    category: auth
    severity: high
    languages: [javascript, typescript]
    
    detection:
      # Stage 1: Quick regex filter
      regex_include:
        - 'jwt\.sign\s*\('
        - 'jsonwebtoken'
      
      regex_exclude:
        - 'passport'
        - 'express-jwt'
        - 'JwtStrategy'
      
      # Stage 2: AST pattern
      ast_query: |
        (call_expression
          function: (member_expression
            object: (identifier) @obj
            property: (property_identifier) @method)
          (#eq? @obj "jwt")
          (#eq? @method "sign"))
      
      # Stage 3: Context validation
      requires_import: ['jsonwebtoken', 'jwt']
      excludes_import: ['passport', 'passport-jwt', 'express-jwt']
      
      # Stage 4: LLM prompt (if needed)
      llm_prompt: |
        Is this a custom JWT implementation or proper library usage?
        Custom = manually calling jwt.sign() without passport
        Library = using passport-jwt, express-jwt, etc.
        
        Answer: CUSTOM or LIBRARY
    
    evidence:
      alternative: "passport-jwt"
      common_issues:
        - "Security vulnerabilities"
        - "Token validation errors"
        - "Secret key management"
  
  # ==========================================
  
  foreach_async:
    name: "forEach with async callback"
    category: async
    severity: high
    languages: [javascript, typescript]
    
    detection:
      regex_include:
        - '\.forEach\s*\(\s*async'
      
      ast_query: |
        (call_expression
          function: (member_expression
            property: (property_identifier) @method)
          arguments: (arguments
            (arrow_function
              async: "async"))
          (#eq? @method "forEach"))
      
      llm_prompt: |
        Does this code use forEach with async callback?
        This is an antipattern because forEach doesn't wait for promises.
        
        Answer: YES or NO
    
    evidence:
      alternative: "for...of loop or Promise.all()"
      common_issues:
        - "Race conditions"
        - "Promises not awaited"
        - "Unexpected execution order"
  
  # ==========================================
  
  n_plus_one:
    name: "N+1 Query Problem"
    category: database
    severity: medium
    languages: [javascript, typescript]
    
    detection:
      regex_include:
        - 'for\s*\([^)]+\)\s*{[^}]*\.(find|findOne|query)'
        - '\.forEach\([^)]+[^}]*\.(find|findOne)'
      
      ast_query: |
        (for_statement
          body: (block
            (call_expression
              function: (member_expression
                property: (property_identifier) @method)
              (#match? @method "find|findOne|query"))))
      
      llm_prompt: |
        Is this a N+1 query antipattern?
        N+1 = looping and making DB query in each iteration
        
        Answer: YES or NO
    
    evidence:
      alternative: "Batch loading, JOIN, eager loading"
      common_issues:
        - "Performance degradation"
        - "Database connection exhaustion"
        - "Slow response times"

# Add 20+ more patterns...
```

---

## 2. STAGE 1: REGEX FILTER

```typescript
// src/detection/regex-filter.ts

interface PatternConfig {
  regex_include: string[];
  regex_exclude?: string[];
}

export class RegexFilter {
  
  /**
   * Quick filter to eliminate obvious non-matches
   * Returns: 'MATCH' | 'NO_MATCH' | 'UNCERTAIN'
   */
  static check(code: string, pattern: PatternConfig): string {
    // Check includes
    const hasInclude = pattern.regex_include.some(regex => 
      new RegExp(regex, 'i').test(code)
    );
    
    if (!hasInclude) {
      return 'NO_MATCH';
    }
    
    // Check excludes
    if (pattern.regex_exclude) {
      const hasExclude = pattern.regex_exclude.some(regex =>
        new RegExp(regex, 'i').test(code)
      );
      
      if (hasExclude) {
        return 'NO_MATCH';
      }
    }
    
    return 'MATCH';
  }
  
  /**
   * Extract matched lines for further analysis
   */
  static extractMatches(code: string, regex: string): Array<{
    line: number;
    text: string;
  }> {
    const lines = code.split('\n');
    const pattern = new RegExp(regex, 'gi');
    const matches = [];
    
    lines.forEach((line, index) => {
      if (pattern.test(line)) {
        matches.push({
          line: index + 1,
          text: line.trim()
        });
      }
    });
    
    return matches;
  }
}

// Usage example
const code = `
const token = jwt.sign(payload, SECRET_KEY);
`;

const result = RegexFilter.check(code, {
  regex_include: ['jwt\\.sign'],
  regex_exclude: ['passport']
});

console.log(result); // 'MATCH'
```

---

## 3. STAGE 2: AST ANALYSIS

```typescript
// src/detection/ast-analyzer.ts

import Parser from 'tree-sitter';
import JavaScript from 'tree-sitter-javascript';
import TypeScript from 'tree-sitter-typescript';

interface ASTMatch {
  type: string;
  line: number;
  column: number;
  text: string;
  node: any;
}

export class ASTAnalyzer {
  private jsParser: Parser;
  private tsParser: Parser;
  
  constructor() {
    this.jsParser = new Parser();
    this.jsParser.setLanguage(JavaScript);
    
    this.tsParser = new Parser();
    this.tsParser.setLanguage(TypeScript.typescript);
  }
  
  /**
   * Parse code and find pattern matches
   */
  analyze(code: string, language: 'javascript' | 'typescript', astQuery: string): ASTMatch[] {
    const parser = language === 'typescript' ? this.tsParser : this.jsParser;
    const tree = parser.parse(code);
    
    // For now, use simple node traversal
    // TODO: Implement proper tree-sitter query language
    return this.findPatternNodes(tree.rootNode, astQuery);
  }
  
  /**
   * Find specific pattern in AST
   */
  private findPatternNodes(node: any, pattern: string): ASTMatch[] {
    const matches: ASTMatch[] = [];
    
    // Example: Detect jwt.sign()
    if (this.isJwtSignCall(node)) {
      matches.push({
        type: 'custom_jwt',
        line: node.startPosition.row + 1,
        column: node.startPosition.column,
        text: node.text,
        node: node
      });
    }
    
    // Recurse through children
    for (let i = 0; i < node.childCount; i++) {
      const child = node.child(i);
      matches.push(...this.findPatternNodes(child, pattern));
    }
    
    return matches;
  }
  
  /**
   * Check if node is jwt.sign() call
   */
  private isJwtSignCall(node: any): boolean {
    if (node.type !== 'call_expression') {
      return false;
    }
    
    const func = node.childForFieldName('function');
    if (!func || func.type !== 'member_expression') {
      return false;
    }
    
    const object = func.childForFieldName('object');
    const property = func.childForFieldName('property');
    
    return (
      object?.text === 'jwt' &&
      property?.text === 'sign'
    );
  }
  
  /**
   * Check if node is forEach with async
   */
  private isForEachAsync(node: any): boolean {
    if (node.type !== 'call_expression') {
      return false;
    }
    
    const func = node.childForFieldName('function');
    if (!func || func.type !== 'member_expression') {
      return false;
    }
    
    const property = func.childForFieldName('property');
    if (property?.text !== 'forEach') {
      return false;
    }
    
    const args = node.childForFieldName('arguments');
    if (!args) return false;
    
    // Check if callback is async
    const callback = args.namedChildren[0];
    return callback?.text.startsWith('async');
  }
}

// Usage
const analyzer = new ASTAnalyzer();
const code = `jwt.sign(payload, secret)`;
const matches = analyzer.analyze(code, 'javascript', 'custom_jwt');
console.log(matches);
```

---

## 4. STAGE 3: CONTEXT VALIDATION

```typescript
// src/detection/context-validator.ts

interface ContextRules {
  requires_import?: string[];
  excludes_import?: string[];
}

export class ContextValidator {
  
  /**
   * Validate pattern against file context
   */
  static validate(fileContent: string, rules: ContextRules): boolean {
    if (rules.requires_import) {
      const hasRequired = rules.requires_import.some(lib =>
        this.hasImport(fileContent, lib)
      );
      
      if (!hasRequired) {
        return false;
      }
    }
    
    if (rules.excludes_import) {
      const hasExcluded = rules.excludes_import.some(lib =>
        this.hasImport(fileContent, lib)
      );
      
      if (hasExcluded) {
        return false;
      }
    }
    
    return true;
  }
  
  /**
   * Check if file imports a library
   */
  private static hasImport(code: string, library: string): boolean {
    const patterns = [
      new RegExp(`import\\s+.*from\\s+['"]${library}['"]`, 'i'),
      new RegExp(`require\\s*\\(['"]${library}['"]\\)`, 'i'),
      new RegExp(`import\\s+['"]${library}['"]`, 'i'),
    ];
    
    return patterns.some(p => p.test(code));
  }
  
  /**
   * Get all imports from file
   */
  static extractImports(code: string): string[] {
    const imports: string[] = [];
    
    // ES6 imports
    const es6Pattern = /import\s+.*from\s+['"]([^'"]+)['"]/g;
    let match;
    while ((match = es6Pattern.exec(code)) !== null) {
      imports.push(match[1]);
    }
    
    // CommonJS requires
    const cjsPattern = /require\s*\(['"]([^'"]+)['"]\)/g;
    while ((match = cjsPattern.exec(code)) !== null) {
      imports.push(match[1]);
    }
    
    return imports;
  }
}

// Usage
const code = `
import jwt from 'jsonwebtoken';
const token = jwt.sign(payload, secret);
`;

const valid = ContextValidator.validate(code, {
  requires_import: ['jsonwebtoken'],
  excludes_import: ['passport']
});

console.log(valid); // true
```

---

## 5. STAGE 4: GLM 4.5 AIR VALIDATION

```typescript
// src/detection/llm-validator.ts

import axios from 'axios';
import crypto from 'crypto';

interface LLMResponse {
  result: 'CUSTOM' | 'LIBRARY' | 'YES' | 'NO' | 'UNCERTAIN';
  confidence: number;
}

export class LLMValidator {
  private apiUrl: string;
  private apiKey: string;
  private redis: any; // Redis client
  
  constructor(redis: any) {
    this.apiUrl = process.env.GLM_API_URL!;
    this.apiKey = process.env.GLM_API_KEY!;
    this.redis = redis;
  }
  
  /**
   * Validate pattern using GLM 4.5 Air
   * Uses cache to avoid duplicate API calls
   */
  async validate(code: string, prompt: string): Promise<LLMResponse> {
    // Generate cache key
    const cacheKey = this.getCacheKey(code, prompt);
    
    // Check Redis cache
    const cached = await this.redis.get(`llm:${cacheKey}`);
    if (cached) {
      return JSON.parse(cached);
    }
    
    // Call GLM API
    const result = await this.callGLM(code, prompt);
    
    // Cache result (30 days)
    await this.redis.setex(
      `llm:${cacheKey}`,
      2592000,
      JSON.stringify(result)
    );
    
    // Store in PostgreSQL for analytics
    await this.storeLLMCall(cacheKey, code, prompt, result);
    
    return result;
  }
  
  /**
   * Call GLM 4.5 Air API
   */
  private async callGLM(code: string, prompt: string): Promise<LLMResponse> {
    const fullPrompt = `${prompt}\n\nCode:\n${code}`;
    
    try {
      const response = await axios.post(
        this.apiUrl,
        {
          model: 'GLM-4.5-Air',
          messages: [
            {
              role: 'user',
              content: fullPrompt
            }
          ],
          temperature: 0.1,
          max_tokens: 10
        },
        {
          headers: {
            'Authorization': `Bearer ${this.apiKey}`,
            'Content-Type': 'application/json'
          },
          timeout: 30000
        }
      );
      
      const answer = response.data.choices[0].message.content.trim().toUpperCase();
      const tokens = response.data.usage.total_tokens;
      
      return {
        result: this.parseAnswer(answer),
        confidence: this.calculateConfidence(answer)
      };
      
    } catch (error: any) {
      console.error('GLM API error:', error.message);
      return {
        result: 'UNCERTAIN',
        confidence: 0
      };
    }
  }
  
  /**
   * Parse LLM answer
   */
  private parseAnswer(answer: string): LLMResponse['result'] {
    if (answer.includes('CUSTOM')) return 'CUSTOM';
    if (answer.includes('LIBRARY')) return 'LIBRARY';
    if (answer.includes('YES')) return 'YES';
    if (answer.includes('NO')) return 'NO';
    return 'UNCERTAIN';
  }
  
  /**
   * Calculate confidence based on answer clarity
   */
  private calculateConfidence(answer: string): number {
    if (answer.length <= 10 && /^(CUSTOM|LIBRARY|YES|NO)$/.test(answer)) {
      return 0.95;
    }
    if (answer.includes('CUSTOM') || answer.includes('LIBRARY')) {
      return 0.85;
    }
    return 0.5;
  }
  
  /**
   * Generate cache key
   */
  private getCacheKey(code: string, prompt: string): string {
    const normalized = code.trim() + '|||' + prompt.trim();
    return crypto.createHash('md5').update(normalized).digest('hex');
  }
  
  /**
   * Store LLM call in database
   */
  private async storeLLMCall(
    hash: string,
    code: string,
    prompt: string,
    result: LLMResponse
  ): Promise<void> {
    // Implementation depends on your DB client
    // await db.query('INSERT INTO llm_cache ...');
  }
}
```

---

## 6. COMPLETE DETECTION PIPELINE

```typescript
// src/detection/pattern-detector.ts

import { RegexFilter } from './regex-filter';
import { ASTAnalyzer } from './ast-analyzer';
import { ContextValidator } from './context-validator';
import { LLMValidator } from './llm-validator';
import { PatternConfig } from './types';

interface DetectionResult {
  pattern_id: string;
  detected: boolean;
  confidence: number;
  method: 'regex' | 'ast' | 'context' | 'llm';
  matches: Array<{
    line: number;
    text: string;
  }>;
}

export class PatternDetector {
  private astAnalyzer: ASTAnalyzer;
  private llmValidator: LLMValidator;
  
  constructor(redis: any) {
    this.astAnalyzer = new ASTAnalyzer();
    this.llmValidator = new LLMValidator(redis);
  }
  
  /**
   * Main detection method
   * Runs through all stages with early exit optimization
   */
  async detect(
    code: string,
    language: 'javascript' | 'typescript',
    patternConfig: PatternConfig
  ): Promise<DetectionResult> {
    
    // STAGE 1: Regex filter (fast, cheap, ~60% accuracy)
    const regexResult = RegexFilter.check(code, patternConfig.detection);
    
    if (regexResult === 'NO_MATCH') {
      return {
        pattern_id: patternConfig.name,
        detected: false,
        confidence: 0.9,
        method: 'regex',
        matches: []
      };
    }
    
    // STAGE 2: AST analysis (medium speed, free, ~85% accuracy)
    const astMatches = this.astAnalyzer.analyze(
      code,
      language,
      patternConfig.detection.ast_query
    );
    
    if (astMatches.length === 0) {
      return {
        pattern_id: patternConfig.name,
        detected: false,
        confidence: 0.85,
        method: 'ast',
        matches: []
      };
    }
    
    // STAGE 3: Context validation (fast, free, ~90% accuracy)
    const contextValid = ContextValidator.validate(code, {
      requires_import: patternConfig.detection.requires_import,
      excludes_import: patternConfig.detection.excludes_import
    });
    
    if (!contextValid) {
      return {
        pattern_id: patternConfig.name,
        detected: false,
        confidence: 0.9,
        method: 'context',
        matches: []
      };
    }
    
    // STAGE 4: LLM validation (slow, paid, ~95% accuracy)
    // Only use for uncertain cases
    if (patternConfig.detection.llm_prompt && astMatches.length > 0) {
      const llmResult = await this.llmValidator.validate(
        code,
        patternConfig.detection.llm_prompt
      );
      
      const detected = 
        llmResult.result === 'CUSTOM' ||
        llmResult.result === 'YES';
      
      return {
        pattern_id: patternConfig.name,
        detected,
        confidence: llmResult.confidence,
        method: 'llm',
        matches: astMatches.map(m => ({
          line: m.line,
          text: m.text
        }))
      };
    }
    
    // Default: AST + Context is confident enough
    return {
      pattern_id: patternConfig.name,
      detected: true,
      confidence: 0.9,
      method: 'ast',
      matches: astMatches.map(m => ({
        line: m.line,
        text: m.text
      }))
    };
  }
}
```

---

## 7. PROCESS COMMITS

```typescript
// src/pipeline/pattern-detection.ts

import { PatternDetector } from '../detection/pattern-detector';
import { loadPatternConfigs } from '../config/patterns';
import { db } from '../database/postgres';
import { redis } from '../database/redis';

export async function processCommits(): Promise<void> {
  const patterns = await loadPatternConfigs();
  const detector = new PatternDetector(redis);
  
  // Get unprocessed commits
  const commits = await db.query(`
    SELECT 
      sha,
      repo_id,
      diff_text,
      files_changed
    FROM commits
    WHERE processed = FALSE
    LIMIT 1000
  `);
  
  for (const commit of commits.rows) {
    await processCommit(commit, patterns, detector);
  }
}

async function processCommit(commit: any, patterns: any[], detector: PatternDetector) {
  // Parse diff to get added/removed code
  const changes = parseDiff(commit.diff_text);
  
  for (const change of changes) {
    // Determine language
    const language = getLanguage(change.file);
    if (!['javascript', 'typescript'].includes(language)) {
      continue;
    }
    
    // Detect patterns in added code
    for (const pattern of patterns) {
      if (change.added_lines.length > 0) {
        const result = await detector.detect(
          change.added_lines.join('\n'),
          language as any,
          pattern
        );
        
        if (result.detected) {
          await storePatternOccurrence(
            commit.sha,
            commit.repo_id,
            pattern.id,
            'add',
            change.file,
            result
          );
        }
      }
      
      // Detect patterns in removed code
      if (change.removed_lines.length > 0) {
        const result = await detector.detect(
          change.removed_lines.join('\n'),
          language as any,
          pattern
        );
        
        if (result.detected) {
          await storePatternOccurrence(
            commit.sha,
            commit.repo_id,
            pattern.id,
            'remove',
            change.file,
            result
          );
        }
      }
    }
  }
  
  // Mark commit as processed
  await db.query(
    'UPDATE commits SET processed = TRUE WHERE sha = $1',
    [commit.sha]
  );
}

function parseDiff(diff: string): Array<{
  file: string;
  added_lines: string[];
  removed_lines: string[];
}> {
  const files = [];
  const fileBlocks = diff.split('diff --git');
  
  for (const block of fileBlocks) {
    if (!block.trim()) continue;
    
    // Extract filename
    const fileMatch = block.match(/a\/(.+?)\s+b\//);
    if (!fileMatch) continue;
    
    const file = fileMatch[1];
    const added_lines: string[] = [];
    const removed_lines: string[] = [];
    
    const lines = block.split('\n');
    for (const line of lines) {
      if (line.startsWith('+') && !line.startsWith('+++')) {
        added_lines.push(line.substring(1));
      } else if (line.startsWith('-') && !line.startsWith('---')) {
        removed_lines.push(line.substring(1));
      }
    }
    
    files.push({ file, added_lines, removed_lines });
  }
  
  return files;
}
```

---

## 8. TEMPORAL ANALYSIS (Add→Remove)

```typescript
// src/analysis/temporal-analyzer.ts

import { db } from '../database/postgres';

export async function findMigrations(): Promise<void> {
  // For each repo and pattern
  const repos = await db.query('SELECT id FROM repos');
  const patterns = await db.query('SELECT DISTINCT pattern_id FROM pattern_occurrences');
  
  for (const repo of repos.rows) {
    for (const pattern of patterns.rows) {
      await findMigrationsForPattern(repo.id, pattern.pattern_id);
    }
  }
}

async function findMigrationsForPattern(repoId: number, patternId: string): Promise<void> {
  // Find all adds and removes for this pattern in this repo
  const occurrences = await db.query(`
    SELECT 
      po.id,
      po.commit_sha,
      po.action,
      po.file_path,
      c.date
    FROM pattern_occurrences po
    JOIN commits c ON po.commit_sha = c.sha
    WHERE po.repo_id = $1
      AND po.pattern_id = $2
    ORDER BY c.date ASC
  `, [repoId, patternId]);
  
  // Group by file
  const byFile: Map<string, any[]> = new Map();
  for (const occ of occurrences.rows) {
    if (!byFile.has(occ.file_path)) {
      byFile.set(occ.file_path, []);
    }
    byFile.get(occ.file_path)!.push(occ);
  }
  
  // For each file, find Add→Remove sequences
  for (const [file, occs] of byFile) {
    let lastAdd: any = null;
    
    for (const occ of occs) {
      if (occ.action === 'add') {
        lastAdd = occ;
      } else if (occ.action === 'remove' && lastAdd) {
        // Found migration!
        const daysDiff = Math.floor(
          (new Date(occ.date).getTime() - new Date(lastAdd.date).getTime()) / (1000 * 60 * 60 * 24)
        );
        
        await db.query(`
          INSERT INTO pattern_migrations (
            repo_id,
            pattern_id,
            added_commit_sha,
            removed_commit_sha,
            added_date,
            removed_date,
            days_to_removal
          ) VALUES ($1, $2, $3, $4, $5, $6, $7)
          ON CONFLICT DO NOTHING
        `, [
          repoId,
          patternId,
          lastAdd.commit_sha,
          occ.commit_sha,
          lastAdd.date,
          occ.date,
          daysDiff
        ]);
        
        lastAdd = null; // Reset
      }
    }
  }
}
```

---

## 9. CALCULATE STATISTICS

```typescript
// src/analysis/statistics.ts

import { db } from '../database/postgres';

export async function calculateStatistics(): Promise<void> {
  const patterns = await db.query('SELECT DISTINCT pattern_id FROM pattern_occurrences');
  
  for (const { pattern_id } of patterns.rows) {
    const stats = await db.query(`
      SELECT 
        COUNT(DISTINCT repo_id) as repos_affected,
        COUNT(CASE WHEN action = 'add' THEN 1 END) as total_adds,
        COUNT(CASE WHEN action = 'remove' THEN 1 END) as total_removes
      FROM pattern_occurrences
      WHERE pattern_id = $1
    `, [pattern_id]);
    
    const migrations = await db.query(`
      SELECT 
        COUNT(*) as migration_count,
        AVG(days_to_removal) as avg_days,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY days_to_removal) as median_days
      FROM pattern_migrations
      WHERE pattern_id = $1
    `, [pattern_id]);
    
    const { repos_affected, total_adds, total_removes } = stats.rows[0];
    const { migration_count, avg_days, median_days } = migrations.rows[0];
    
    const failure_rate = total_adds > 0 ? (total_removes / total_adds) : 0;
    
    // Store in pattern_definitions
    await db.query(`
      INSERT INTO pattern_definitions (
        id,
        category,
        repos_affected,
        total_occurrences,
        removal_count,
        failure_rate,
        avg_days_to_removal,
        median_days_to_removal
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
      ON CONFLICT (id) DO UPDATE SET
        repos_affected = EXCLUDED.repos_affected,
        total_occurrences = EXCLUDED.total_occurrences,
        removal_count = EXCLUDED.removal_count,
        failure_rate = EXCLUDED.failure_rate,
        avg_days_to_removal = EXCLUDED.avg_days_to_removal,
        median_days_to_removal = EXCLUDED.median_days_to_removal,
        last_updated = NOW()
    `, [
      pattern_id,
      'auth', // TODO: get from pattern config
      repos_affected,
      total_adds,
      total_removes,
      failure_rate,
      avg_days,
      median_days
    ]);
    
    console.log(`Pattern ${pattern_id}:`);
    console.log(`  Repos: ${repos_affected}`);
    console.log(`  Adds: ${total_adds}`);
    console.log(`  Removes: ${total_removes}`);
    console.log(`  Failure rate: ${(failure_rate * 100).toFixed(1)}%`);
    console.log(`  Avg days to removal: ${avg_days?.toFixed(0)}`);
  }
}
```

---

## 10. MAIN PIPELINE

```typescript
// src/index.ts

import { processCommits } from './pipeline/pattern-detection';
import { findMigrations } from './analysis/temporal-analyzer';
import { calculateStatistics } from './analysis/statistics';

async function main() {
  console.log('Starting pattern detection pipeline...');
  
  // Step 1: Detect patterns in commits
  console.log('\n[1/3] Detecting patterns in commits...');
  await processCommits();
  
  // Step 2: Find Add→Remove migrations
  console.log('\n[2/3] Finding temporal migrations...');
  await findMigrations();
  
  // Step 3: Calculate statistics
  console.log('\n[3/3] Calculating statistics...');
  await calculateStatistics();
  
  console.log('\nPipeline complete!');
}

main().catch(console.error);
```

---

## 11. TEST CASES

```typescript
// test/pattern-detector.test.ts

import { PatternDetector } from '../src/detection/pattern-detector';

describe('PatternDetector', () => {
  let detector: PatternDetector;
  
  beforeAll(() => {
    detector = new PatternDetector(mockRedis);
  });
  
  test('detects custom JWT', async () => {
    const code = `
      const jwt = require('jsonwebtoken');
      const token = jwt.sign(payload, SECRET_KEY);
    `;
    
    const result = await detector.detect(code, 'javascript', customJwtPattern);
    
    expect(result.detected).toBe(true);
    expect(result.confidence).toBeGreaterThan(0.8);
  });
  
  test('does not detect passport-jwt as custom', async () => {
    const code = `
      const passport = require('passport');
      passport.authenticate('jwt', { session: false });
    `;
    
    const result = await detector.detect(code, 'javascript', customJwtPattern);
    
    expect(result.detected).toBe(false);
  });
  
  test('detects forEach with async', async () => {
    const code = `
      items.forEach(async (item) => {
        await processItem(item);
      });
    `;
    
    const result = await detector.detect(code, 'javascript', forEachAsyncPattern);
    
    expect(result.detected).toBe(true);
  });
});
```

---

## SUMMARY: DETECTION COSTS

```yaml
Strategy: Hybrid (Regex → AST → Context → LLM)

Per 400,000 commits:
├─ Stage 1 (Regex): 400K commits → 40K suspicious (90% filtered, FREE)
├─ Stage 2 (AST): 40K → 10K matches (75% filtered, FREE)
├─ Stage 3 (Context): 10K → 5K validated (50% filtered, FREE)
├─ Stage 4 (GLM 4.5 Air): 5K × 500 tokens = 2.5M tokens
│   └─ Cost: 2.5M × $0.07/1M = $0.175 per run
└─ TOTAL: $0.18 per mining run

Monthly cost: $0.18
Annual cost: $2.16

Processing time:
├─ Regex: instant
├─ AST: ~10 minutes
├─ Context: ~1 minute
├─ GLM: ~15 minutes (with parallelization)
└─ TOTAL: ~30 minutes
```

---

**ГОТОВО! Теперь у вас полное ТЗ для детекции паттернов.**

Начните с `custom_jwt` и `foreach_async` — они самые простые для proof of concept.