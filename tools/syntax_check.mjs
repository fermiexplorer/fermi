// Extract inline <script> blocks from index.html and syntax-check each.
// Exits non-zero on any syntax error (used by tools/verify.py).
import { readFileSync } from "fs";
const html = readFileSync("index.html", "utf8");
const re = /<script(?![^>]*src)[^>]*>([\s\S]*?)<\/script>/g;
let m, i = 0, bad = 0;
while ((m = re.exec(html))) {
  i++;
  try {
    new Function(m[1]);
    console.log(`script block ${i}: OK (${m[1].length} chars)`);
  } catch (e) {
    bad++;
    console.log(`script block ${i}: SYNTAX ERROR: ${e.message}`);
  }
}
process.exit(bad ? 1 : 0);
