import test from "node:test";
import assert from "node:assert/strict";
import Graph from "graphology";
import { activeBrainNode, addBrainEdges } from "../lib/brainGraph.js";

test("adds graph edges before community detection", () => {
  const graph = new Graph({ multi: false, type: "undirected" });
  graph.addNode("formal-verification");
  graph.addNode("category-theory");

  addBrainEdges(graph, [{ source: "formal-verification", target: "category-theory", type: "RELATED_TO" }]);

  assert.equal(graph.size, 1);
  assert.deepEqual(graph.extremities(graph.edges()[0]!), ["formal-verification", "category-theory"]);
});

test("ignores stale hover ids after drilling into an island", () => {
  const graph = new Graph({ multi: false, type: "undirected" });
  graph.addNode("concept-1");

  assert.equal(activeBrainNode(graph, "island:math", null), null);
  assert.equal(activeBrainNode(graph, "island:math", "concept-1"), "concept-1");
});

test("does not let a stored selection hide labels in a focused island", () => {
  const graph = new Graph({ multi: false, type: "undirected" });
  graph.addNode("concept-1");

  assert.equal(activeBrainNode(graph, null, "concept-1", true), null);
  assert.equal(activeBrainNode(graph, "concept-1", "concept-2", true), "concept-1");
});
