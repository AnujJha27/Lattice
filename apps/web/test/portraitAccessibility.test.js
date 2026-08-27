import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const renderer = readFileSync(new URL("../components/portrait/PortraitRenderer.tsx", import.meta.url), "utf8");
const styles = readFileSync(new URL("../app/globals.css", import.meta.url), "utf8");
const profile = readFileSync(new URL("../app/app/profile/page.tsx", import.meta.url), "utf8");

test("interactive portrait regions remain exposed to assistive technology", () => {
  assert.match(renderer, /<svg[\s\S]*?role="group"/);
  assert.doesNotMatch(renderer, /<svg[\s\S]*?role="img"/);
  assert.match(renderer, /<g role="button" tabIndex=\{0\}/);
  assert.match(renderer, /group-focus-visible:opacity-100/);
  assert.match(renderer, /portrait-mobile-secondary/);
  assert.match(styles, /\.portrait-mobile-secondary\s*\{\s*display:\s*none;/);
  assert.match(renderer, /aria-label=\{`\$\{source\.represents\}: \$\{source\.asset\.title\} · \$\{source\.asset\.rights_class\}/);
  assert.match(renderer, /createClient\(\)\.auth\.getSession/);
  assert.match(profile, /useRefreshPortrait/);
  assert.match(profile, /Refresh portrait/);
  assert.match(renderer, /AnimatePresence/);
  assert.match(renderer, /motion\.g/);
  assert.match(renderer, /useReducedMotion/);
  assert.match(renderer, /exit=\{/);
  assert.match(renderer, /key=\{`anchor-\$\{item\.id\}`\}/);
  assert.match(renderer, /key=\{`frontier-\$\{item\.id\}`\}/);
  assert.match(renderer, /key=\{`emerging-\$\{item\.id\}`\}/);
  assert.match(renderer, /key=\{`visual-\$\{source\.asset_id\}`\}/);
});
