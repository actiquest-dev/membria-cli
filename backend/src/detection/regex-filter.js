class RegexFilter {
  static check(code, detection) {
    const hasInclude = detection.regex_include.some(regex => regex.test(code));
    if (!hasInclude) return 'NO_MATCH';

    if (detection.regex_exclude && detection.regex_exclude.length > 0) {
      const hasExclude = detection.regex_exclude.some(regex => regex.test(code));
      if (hasExclude) return 'NO_MATCH';
    }

    return 'MATCH';
  }

  static extractMatches(code, regexList) {
    const lines = code.split('\n');
    const matches = [];

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      for (const regex of regexList) {
        regex.lastIndex = 0;
        if (regex.test(line)) {
          matches.push({ line: i + 1, text: line.trim() });
          break;
        }
      }
    }

    return matches;
  }
}

module.exports = { RegexFilter };
