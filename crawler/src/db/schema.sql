-- PostgreSQL schema for Membria Crawler

-- Repositories table
CREATE TABLE IF NOT EXISTS repositories (
  id SERIAL PRIMARY KEY,
  full_name VARCHAR(255) UNIQUE NOT NULL,
  owner VARCHAR(255) NOT NULL,
  name VARCHAR(255) NOT NULL,
  description TEXT,
  stars INTEGER DEFAULT 0,
  forks INTEGER DEFAULT 0,
  language VARCHAR(100),
  size INTEGER,
  last_pushed TIMESTAMP,
  archived BOOLEAN DEFAULT FALSE,
  forked BOOLEAN DEFAULT FALSE,
  topics TEXT[],
  priority_score DECIMAL(10,2),
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  last_fetched_at TIMESTAMP
);

CREATE INDEX idx_repos_full_name ON repositories(full_name);
CREATE INDEX idx_repos_stars ON repositories(stars DESC);
CREATE INDEX idx_repos_priority ON repositories(priority_score DESC);

-- Commits table
CREATE TABLE IF NOT EXISTS commits (
  id SERIAL PRIMARY KEY,
  repo_id INTEGER REFERENCES repositories(id) ON DELETE CASCADE,
  sha VARCHAR(255) UNIQUE NOT NULL,
  author VARCHAR(255),
  date TIMESTAMP,
  message TEXT,
  additions INTEGER DEFAULT 0,
  deletions INTEGER DEFAULT 0,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_commits_repo_id ON commits(repo_id);
CREATE INDEX idx_commits_date ON commits(date DESC);
CREATE INDEX idx_commits_sha ON commits(sha);

-- Patterns/Antipatterns table
CREATE TABLE IF NOT EXISTS patterns (
  id SERIAL PRIMARY KEY,
  repo_id INTEGER REFERENCES repositories(id) ON DELETE CASCADE,
  commit_sha VARCHAR(255),
  issue_type VARCHAR(50),
  message TEXT,
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_patterns_repo_id ON patterns(repo_id);
CREATE INDEX idx_patterns_type ON patterns(issue_type);
CREATE INDEX idx_patterns_date ON patterns(created_at DESC);

-- Rate limiter tracking
CREATE TABLE IF NOT EXISTS rate_limit_tracking (
  id SERIAL PRIMARY KEY,
  resource VARCHAR(50) UNIQUE NOT NULL,
  remaining INTEGER NOT NULL,
  limit INTEGER NOT NULL,
  reset_at TIMESTAMP NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_rate_limit_reset ON rate_limit_tracking(reset_at);
