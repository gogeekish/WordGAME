// Flexible date parser: finds a date almost anywhere in a line of text,
// in many common written formats, and returns {monthIdx (0-11), year}.
(function(global){
  const MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];

  const MONTH_NAMES = {
    jan:0, january:0, feb:1, february:1, mar:2, march:2, apr:3, april:3,
    may:4, jun:5, june:5, jul:6, july:6, aug:7, august:7,
    sep:8, sept:8, september:8, oct:9, october:9, nov:10, november:10, dec:11, december:11
  };

  function monthNameToIndex(s){
    const key = String(s || '').toLowerCase();
    return MONTH_NAMES.hasOwnProperty(key) ? MONTH_NAMES[key] : -1;
  }

  function normalizeYear(yStr){
    if (yStr.length >= 4) return parseInt(yStr, 10);
    const y = parseInt(yStr, 10);
    return y <= 79 ? 2000 + y : 1900 + y;
  }

  function valid(day, monthIdx, year){
    return monthIdx >= 0 && monthIdx <= 11 && day >= 1 && day <= 31 && year >= 1900 && year <= 2100;
  }

  const SEP = '[\\-\\/\\. ]';
  // (?<!\d) / (?!\d) stop these numeric groups from matching a substring
  // inside a longer run of digits (like an ID number, or the middle of a
  // different date format already handled by an earlier pattern).
  const DAY = '(?<!\\d)(\\d{1,2})(?:st|nd|rd|th)?(?!\\d)';
  const MONTH_WORD = '([A-Za-z]{3,9})';
  const YEAR2_4 = '(?<!\\d)(\\d{2,4})(?!\\d)';
  const YEAR4 = '(?<!\\d)(\\d{4})(?!\\d)';
  const MONTHNUM = '(?<!\\d)(\\d{1,2})(?!\\d)';

  // Each pattern is tried (with the 'g' flag) across the whole line; the
  // first match that validates as a real date wins. Patterns that rely on a
  // written month name are tried before purely-numeric ones, since numeric
  // day/month order is ambiguous and more likely to false-positive on
  // unrelated numbers (like ID codes).
  const PATTERNS = [
    // 03-Aug-2026 / 3 August 2026 / 03/Aug/26 / 3rd Aug 2026
    {
      re: DAY + SEP + MONTH_WORD + SEP + YEAR2_4,
      fn: m => {
        const mi = monthNameToIndex(m[2]);
        if (mi < 0) return null;
        return { day: +m[1], monthIdx: mi, year: normalizeYear(m[3]) };
      }
    },
    // Aug 3, 2026 / August 3rd 2026 / Aug-03-2026
    {
      re: MONTH_WORD + SEP + DAY + ',?' + SEP + YEAR2_4,
      fn: m => {
        const mi = monthNameToIndex(m[1]);
        if (mi < 0) return null;
        return { day: +m[2], monthIdx: mi, year: normalizeYear(m[3]) };
      }
    },
    // 2026-Aug-03
    {
      re: YEAR4 + SEP + MONTH_WORD + SEP + DAY,
      fn: m => {
        const mi = monthNameToIndex(m[2]);
        if (mi < 0) return null;
        return { day: +m[3], monthIdx: mi, year: +m[1] };
      }
    },
    // 2026-08-03 (ISO, numeric month)
    {
      re: YEAR4 + SEP + MONTHNUM + SEP + DAY,
      fn: m => {
        const mo = +m[2];
        if (mo < 1 || mo > 12) return null;
        return { day: +m[3], monthIdx: mo - 1, year: +m[1] };
      }
    },
    // 03/08/2026 or 08/03/2026 (ambiguous numeric; day-first wins ties,
    // since that matches this project's original DD-Mon-YYYY convention)
    {
      re: MONTHNUM + SEP + MONTHNUM + SEP + YEAR2_4,
      fn: m => {
        const a = +m[1], b = +m[2];
        const year = normalizeYear(m[3]);
        let day, month;
        if (a > 12 && b <= 12) { day = a; month = b; }
        else if (b > 12 && a <= 12) { day = b; month = a; }
        else if (a <= 12 && b <= 12) { day = a; month = b; }
        else return null;
        return { day, monthIdx: month - 1, year };
      }
    }
  ];

  const COMPILED = PATTERNS.map(p => ({ re: new RegExp(p.re, 'gi'), fn: p.fn }));

  function parseAnyDate(line){
    for (const p of COMPILED){
      p.re.lastIndex = 0;
      let m;
      while ((m = p.re.exec(line)) !== null){
        const result = p.fn(m);
        if (result && valid(result.day, result.monthIdx, result.year)){
          return result;
        }
        if (m.index === p.re.lastIndex) p.re.lastIndex++; // avoid infinite loop on zero-length match
      }
    }
    return null;
  }

  global.NextGenDateParser = { parseAnyDate, MONTHS };
})(typeof window !== 'undefined' ? window : (typeof global !== 'undefined' ? global : this));

if (typeof module !== 'undefined' && module.exports) {
  module.exports = global.NextGenDateParser || (typeof window !== 'undefined' ? window.NextGenDateParser : undefined);
}
