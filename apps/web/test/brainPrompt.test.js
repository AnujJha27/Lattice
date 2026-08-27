import test from "node:test";
import assert from "node:assert/strict";
import { brainPromptItems } from "../lib/brainPrompt.js";

test("review due takes priority over recommendations in the Brain prompt", () => {
  const items = brainPromptItems(
    [{ concept_id: "due-1", name: "Graph theory", mastery_score: 42 }],
    [{ concept_id: "next-1", name: "Topology", score: 0.8, reason: "A strong next step" }],
  );

  assert.deepEqual(items, [{
    kind: "review",
    href: "/app/review",
    label: "1 due",
    name: "Graph theory",
    id: "due-1",
  }]);
});

test("Brain prompt exposes the first three recommendations when nothing is due", () => {
  const recommendations = [1, 2, 3, 4].map((number) => ({
    concept_id: `next-${number}`,
    name: `Concept ${number}`,
    score: number / 10,
    reason: "A strong next step",
  }));

  const items = brainPromptItems([], recommendations);

  assert.equal(items.length, 3);
  assert.deepEqual(items[0], {
    kind: "recommendation",
    href: "/app/concepts/next-1",
    label: "A strong next step",
    name: "Concept 1",
    id: "next-1",
  });
});
