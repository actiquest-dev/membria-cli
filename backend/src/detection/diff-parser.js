function parseDiff(diff) {
  if (!diff) return [];

  const files = [];
  const fileBlocks = diff.split('diff --git');

  for (const block of fileBlocks) {
    if (!block.trim()) continue;

    const fileMatch = block.match(/a\/(.+?)\s+b\//);
    if (!fileMatch) continue;

    const file = fileMatch[1];
    const addedLines = [];
    const removedLines = [];

    const lines = block.split('\n');
    for (const line of lines) {
      if (line.startsWith('+') && !line.startsWith('+++')) {
        addedLines.push(line.substring(1));
      } else if (line.startsWith('-') && !line.startsWith('---')) {
        removedLines.push(line.substring(1));
      }
    }

    if (addedLines.length > 0 || removedLines.length > 0) {
      files.push({ file, addedLines, removedLines });
    }
  }

  return files;
}

function getLanguage(filePath) {
  const ext = filePath.split('.').pop().toLowerCase();
  const map = {
    js: 'javascript',
    mjs: 'javascript',
    cjs: 'javascript',
    jsx: 'javascript',
    ts: 'typescript',
    tsx: 'typescript',
    mts: 'typescript',
    py: 'python',
  };
  return map[ext] || null;
}

module.exports = { parseDiff, getLanguage };
