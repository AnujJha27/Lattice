import test from "node:test";
import assert from "node:assert/strict";
import { selectedSnapshot } from "../lib/portraitHistory.js";

const history = [
  { snapshot_id: "new", summary: {}, changes_since_previous: [] },
  { snapshot_id: "old", summary: {}, changes_since_previous: [] },
];

test("snapshot selection prefers the requested snapshot and falls back to the latest", () => {
  assert.equal(selectedSnapshot(history, "old").snapshot_id, "old");
  assert.equal(selectedSnapshot(history, "missing").snapshot_id, "new");
  assert.equal(selectedSnapshot([], "missing"), null);
});
