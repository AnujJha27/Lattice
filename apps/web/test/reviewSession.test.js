import test from "node:test";
import assert from "node:assert/strict";
import { nextReviewIndex } from "../lib/reviewSession.js";

test("advances through due reviews and marks the final item complete", () => {
  assert.equal(nextReviewIndex(0, 3), 1);
  assert.equal(nextReviewIndex(1, 3), 2);
  assert.equal(nextReviewIndex(2, 3), null);
});
