import test from "node:test";
import assert from "node:assert/strict";
import { insidePoint, orbitPoint, stableNumber } from "../lib/portraitLayout.js";

test("portrait layout is deterministic and keeps regions inside the canvas", () => {
  assert.equal(stableNumber("linear-algebra"), stableNumber("linear-algebra"));
  assert.deepEqual(orbitPoint("linear-algebra", 0, 3, 305), orbitPoint("linear-algebra", 0, 3, 305));

  const inside = insidePoint("linear-algebra", 0);
  const orbit = orbitPoint("linear-algebra", 0, 3, 305);
  assert.ok(inside.x >= 425 && inside.x <= 574);
  assert.ok(inside.y >= 350 && inside.y <= 619);
  assert.ok(orbit.x >= 100 && orbit.x <= 900);
  assert.ok(orbit.y >= 130 && orbit.y <= 610);
});

test("keeps a region anchored when sibling order or count changes", () => {
  assert.deepEqual(insidePoint("linear-algebra", 0), insidePoint("linear-algebra", 7));
  assert.deepEqual(
    orbitPoint("linear-algebra", 0, 3, 305),
    orbitPoint("linear-algebra", 4, 9, 305),
  );
});
