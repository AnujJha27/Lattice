import type { BrainEdge } from "../types/brain";

type GraphLike = {
  hasNode: (id: string) => boolean;
  hasEdge: (source: string, target: string) => boolean;
  addEdge: (source: string, target: string) => unknown;
};

/** Add only drawable edges; community detection must see these first. */
export function addBrainEdges(graph: GraphLike, edges: BrainEdge[]): void {
  for (const { source, target } of edges) {
    if (source !== target && graph.hasNode(source) && graph.hasNode(target) && !graph.hasEdge(source, target)) {
      graph.addEdge(source, target);
    }
  }
}
