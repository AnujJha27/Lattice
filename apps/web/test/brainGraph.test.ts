import test from "node:test";
import assert from "node:assert/strict";
import Graph from "graphology";
import { addBrainEdges } from "../lib/brainGraph.js";

test("adds graph edges before community detection", () => {
  const graph = new Graph({ multi: false, type: "undirected" });
  graph.addNode("formal-verification");
  graph.addNode("category-theory");

  addBrainEdges(graph, [{ source: "formal-verification", target: "category-theory", type: "RELATED_TO" }]);

  assert.equal(graph.size, 1);
  assert.deepEqual(graph.extremities(graph.edges()[0]!), ["formal-verification", "category-theory"]);
});
