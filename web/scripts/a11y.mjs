// Accessibility audit: axe-core (WCAG 2 A/AA + best-practice) on all three tabs, light and dark.
// Usage (from web/): npm run build && npx vite preview --port 4173 &
//   npm i --no-save playwright axe-core && node scripts/a11y.mjs .
import { chromium } from 'playwright';
import fs from 'fs';
const axe = fs.readFileSync(process.argv[2] + '/node_modules/axe-core/axe.min.js', 'utf8');
const b = await chromium.launch(process.env.CHROMIUM ? { executablePath: process.env.CHROMIUM } : {});
for (const theme of ['light', 'dark']) for (const t of ['replay', 'evaluation', 'method']) {
  const p = await b.newPage({ viewport: { width: 1280, height: 900 }, colorScheme: theme });
  await p.goto('http://localhost:4173/?d=2025-06-20#' + t); await p.waitForTimeout(700);
  await p.addScriptTag({ content: axe });
  const r = await p.evaluate(async () => (await axe.run(document, { runOnly: ['wcag2a', 'wcag2aa', 'best-practice'] })).violations.map(v => ({ id: v.id, impact: v.impact, n: v.nodes.length, ex: v.nodes[0].target.join(' ') + ' :: ' + (v.nodes[0].failureSummary || '').slice(0, 160) })));
  console.log(theme, t, JSON.stringify(r));
  await p.close();
}
await b.close();
