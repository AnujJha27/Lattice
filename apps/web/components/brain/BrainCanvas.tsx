"use client";

import { useEffect, useRef, useState } from "react";
import Graph from "graphology";
import Sigma from "sigma";
import forceAtlas2 from "graphology-layout-forceatlas2";
import EdgeCurveProgram from "@sigma/edge-curve";
import louvain from "graphology-communities-louvain";
import type { Attributes } from "graphology-types";
import { useBrainGraph } from "@/hooks/useBrain";
import { AddInterest } from "@/components/brain/AddInterest";
import { brainUI, useBrainStore, visibleNodes } from "@/lib/store/brain";
import { addBrainEdges } from "@/lib/brainGraph";
import type { Settings } from "sigma/settings";
import { MASTERY_COLORS, nodeSize, domainColor, type BrainNode } from "@/types/brain";

type NodeAttrs = Attributes & {
  size: number;
  color: string;
  label: string;
  x: number;
  y: number;
  conceptId: string;
  baseColor: string;
  baseSize: number;
  domain: string | null;
};

export function BrainCanvas() {
  const containerRef = useRef<HTMLDivElement>(null);
  const sigmaRef = useRef<Sigma<NodeAttrs> | null>(null);
  const [focusedCluster, setFocusedCluster] = useState<string | null>(null);
  const { data: graphData, isPending, isError, refetch } = useBrainGraph();
  const viewMode = useBrainStore((s) => s.viewMode);
  const domainFilter = useBrainStore((s) => s.domainFilter);

  useEffect(() => {
    const container = containerRef.current;
    if (!container || !graphData || viewMode === "list") return;

    // Build (or rebuild) the graphology structure.
    const graph = new Graph<NodeAttrs>({ multi: false, type: "undirected" });

    // Neutral spiral seed first (community detection needs the full graph).
    let seedAngle = 0;
    for (const node of visibleNodes(graphData.nodes, domainFilter)) {
      seedAngle += 2.399963;
      const r = 2 + Math.sqrt(seedAngle) * 1.1;
      graph.addNode(node.id, {
        conceptId: node.id,
        label: node.name,
        size: nodeSize(node),
        color: MASTERY_COLORS[node.state],
        baseColor: MASTERY_COLORS[node.state],
        baseSize: nodeSize(node),
        domain: node.domain,
        x: Math.cos(seedAngle) * r,
        y: Math.sin(seedAngle) * r,
      });
    }

    // Islands are learning structure, not loose associations.
    addBrainEdges(graph, graphData.edges.filter((edge) => edge.type !== "RELATED_TO"));

    // Precompute adjacency so hover reducers stay O(1) per node.
    const adjacency = new Map<string, Set<string>>();
    for (const edge of graphData.edges) {
      if (!adjacency.has(edge.source)) adjacency.set(edge.source, new Set());
      if (!adjacency.has(edge.target)) adjacency.set(edge.target, new Set());
      adjacency.get(edge.source)!.add(edge.target);
      adjacency.get(edge.target)!.add(edge.source);
    }

    // Hub concepts (most connections) become the bright centers of clusters.
    const degree = new Map<string, number>();
    for (const edge of graphData.edges) {
      degree.set(edge.source, (degree.get(edge.source) ?? 0) + 1);
      degree.set(edge.target, (degree.get(edge.target) ?? 0) + 1);
    }
    graph.forEachNode((node, attrs) => {
      const d = Math.min(degree.get(node) ?? 0, 8);
      const hubBoost = 1 + d * 0.22;
      attrs.baseSize = (attrs.baseSize ?? 6) * hubBoost;
      attrs.size = attrs.baseSize;
    });

    // Community islands — Louvain with lower resolution produces
    // 4-6 meaningful clusters instead of a dozen micro ones.
    try {
      if (graph.size > 0) {
        louvain.assign(graph, { resolution: 0.65 });
        const communityCount = new Set(
          graph.nodes().map((n) => graph.getNodeAttribute(n, "__community__")),
        ).size;
        if (communityCount <= 1) {
          graph.forEachNode((n) => graph.removeNodeAttribute(n, "__community__"));
        }
      }
    } catch {
      // sparse graph — domain fallback below
    }

    // Position clusters on a ring by community (or domain when undetectable).
    const clusterOfNode = new Map<string, string>();
    graph.forEachNode((node, attrs) => {
      const community = graph.hasNodeAttribute(node, "__community__")
        ? String(graph.getNodeAttribute(node, "__community__"))
        : null;
      clusterOfNode.set(node, attrs.domain ?? community ?? "Uncategorized");
    });
    // Size-aware regions: big clusters get proportionally more sky
    // (area ∝ node count), small related clusters stay tight.
    const clusterSizes = new Map<string, number>();
    clusterOfNode.forEach((key) => {
      clusterSizes.set(key, (clusterSizes.get(key) ?? 0) + 1);
    });
    const clusterKeys = [...clusterSizes.keys()].sort(
      (a, b) => clusterSizes.get(b)! - clusterSizes.get(a)!,
    );
    const totalArea = clusterKeys.reduce((sum, k) => sum + (clusterSizes.get(k) ?? 1), 0);
    const clusterRadius = new Map<string, number>();
    clusterKeys.forEach((k) => {
      // radius ∝ sqrt(share of nodes), with a floor for singletons
      clusterRadius.set(k, 2.2 + Math.sqrt(((clusterSizes.get(k) ?? 1) / totalArea) * 60));
    });

    // Place cluster centers: biggest clusters on the inner ring, with center
    // separation = sum of neighboring radii + gap (no overlaps, ever).
    const clusterCenter = new Map<string, { x: number; y: number }>();
    let cursorAngle = 0;
    clusterKeys.forEach((key) => {
      const rOuter = 10 + clusterRadius.get(key)! * 1.4;
      const halfAngle = clusterRadius.get(key)! / rOuter + 0.35 / rOuter;
      const angle = cursorAngle + halfAngle;
      cursorAngle += 2 * halfAngle + 0.5 / rOuter;
      clusterCenter.set(key, { x: Math.cos(angle) * rOuter, y: Math.sin(angle) * rOuter });
    });

    const showingOverview = !focusedCluster || !clusterSizes.has(focusedCluster);
    const islandHubId = new Map<string, string>();
    if (showingOverview) {
      const islandEdges = new Map<string, number>();
      for (const { source, target } of graphData.edges) {
        const a = clusterOfNode.get(source);
        const b = clusterOfNode.get(target);
        if (a && b && a !== b) {
          const key = [a, b].sort().join("|");
          islandEdges.set(key, (islandEdges.get(key) ?? 0) + 1);
        }
      }

      graph.clear();
      clusterKeys.forEach((key) => {
        const members = graphData.nodes.filter((node) => clusterOfNode.get(node.id) === key);
        const hub = [...members].sort((a, b) => (degree.get(b.id) ?? 0) - (degree.get(a.id) ?? 0))[0]!;
        islandHubId.set(key, hub.id);
        const center = clusterCenter.get(key)!;
        const count = clusterSizes.get(key)!;
        graph.addNode(`island:${key}`, {
          conceptId: `island:${key}`,
          label: `${hub.name} · ${count} concept${count === 1 ? "" : "s"}`,
          size: 10 + Math.sqrt(count) * 4,
          baseSize: 10 + Math.sqrt(count) * 4,
          color: domainColor(hub.domain),
          baseColor: domainColor(hub.domain),
          domain: hub.domain,
          x: center.x,
          y: center.y,
        });
      });
      islandEdges.forEach((count, pair) => {
        const [a, b] = pair.split("|");
        if (!a || !b) return;
        graph.addEdge(`island:${a}`, `island:${b}`, {
          size: Math.min(0.8 + count * 0.25, 2.6),
          color: "rgba(139, 147, 167, 0.22)",
        });
      });
    } else if (focusedCluster) {
      clusterCenter.set(focusedCluster, { x: 0, y: 0 });
      graph.nodes().forEach((node) => {
        if (clusterOfNode.get(node) !== focusedCluster) graph.dropNode(node);
      });
    }

    // Drill-down stays organic: a seeded local force layout, never the global
    // force pass that used to smear every island into one hairball.
    if (!showingOverview) {
      graph.nodes().forEach((node, index) => {
        const angle = index * 2.399963;
        const radius = 3 + Math.sqrt(index) * 2.8;
        graph.setNodeAttribute(node, "x", Math.cos(angle) * radius);
        graph.setNodeAttribute(node, "y", Math.sin(angle) * radius);
      });
      forceAtlas2.assign(graph, { iterations: 80, settings: forceAtlas2.inferSettings(graph) });
    }

    // Edges: intra-cluster solid, cross-cluster ghosted (declutters the hairball)
    if (!showingOverview) {
      for (const edge of graphData.edges) {
        if (graph.hasNode(edge.source) && graph.hasNode(edge.target)) {
          const edgeId = graph.edge(edge.source, edge.target);
          if (edgeId) {
            graph.setEdgeAttribute(edgeId, "size", 1.4);
            graph.setEdgeAttribute(edgeId, "color", "rgba(201,169,97,0.38)");
          } else if (edge.type === "RELATED_TO") {
            graph.addEdge(edge.source, edge.target, {
              size: 0.6,
              color: "rgba(139, 147, 167, 0.14)",
            });
          }
        }
      }
    }

    // No global ForceAtlas — it smears every island back into one hairball.
    // The golden-angle scatter inside each domain ring already gives tight,
    // non-overlapping clusters; edges are drawn ghosted across islands.
    if (!showingOverview) {
      // Degenerate-layout guard: if FA2 collapsed everything together,
      // fall back to the golden-angle spiral so the chart is still readable.
      let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
      graph.forEachNode((_, attrs) => {
        minX = Math.min(minX, attrs.x); maxX = Math.max(maxX, attrs.x);
        minY = Math.min(minY, attrs.y); maxY = Math.max(maxY, attrs.y);
      });
      if (maxX - minX < 0.5 && maxY - minY < 0.5) {
        let i = 0;
        graph.forEachNode((_, attrs) => {
          const angle = i * 2.399963;
          const radius = 4 + Math.sqrt(i) * 2.5;
          attrs.x = Math.cos(angle) * radius;
          attrs.y = Math.sin(angle) * radius;
          i += 1;
        });
      }

      // Cluster gravity: pull nodes toward their domain centroid so concepts
      // orbit their field's hub instead of scattering uniformly.
      const centroids = new Map<string, { x: number; y: number; n: number }>();
      graph.forEachNode((node, attrs) => {
        const key = clusterOfNode.get(node) ?? attrs.domain ?? "Uncategorized";
        const c = centroids.get(key) ?? { x: 0, y: 0, n: 0 };
        c.x += attrs.x;
        c.y += attrs.y;
        c.n += 1;
        centroids.set(key, c);
      });
      centroids.forEach((c) => {
        c.x /= c.n;
        c.y /= c.n;
      });

      // Enforce breathing room: push domain centers apart until every pair
      // is at least `minSep` apart (two relaxation passes).
      const keys = [...centroids.keys()];
      for (let pass = 0; pass < 2; pass++) {
        for (let i = 0; i < keys.length; i++) {
          for (let j = i + 1; j < keys.length; j++) {
            const minSep = 10 + (clusterSizes.get(keys[i]!) ?? 1) * 0.4 + (clusterSizes.get(keys[j]!) ?? 1) * 0.4;
            const a = centroids.get(keys[i]!)!;
            const b = centroids.get(keys[j]!)!;
            let dx = b.x - a.x;
            let dy = b.y - a.y;
            let dist = Math.hypot(dx, dy);
            if (dist < 0.001) { dx = 1; dy = 0; dist = 1; }
            if (dist < minSep) {
              const push = (minSep - dist) / 2;
              const ux = dx / dist;
              const uy = dy / dist;
              a.x -= ux * push; a.y -= uy * push;
              b.x += ux * push; b.y += uy * push;
            }
          }
        }
      }

      graph.forEachNode((node, attrs) => {
        const c = centroids.get(clusterOfNode.get(node) ?? attrs.domain ?? "Uncategorized");
        if (!c) return;
        attrs.x += (c.x - attrs.x) * 0.32;
        attrs.y += (c.y - attrs.y) * 0.32;
      });
    }

    const sigma = new Sigma(graph, container, {
      allowInvalidContainer: true,
      minCameraRatio: 0.05,
      maxCameraRatio: 10,
      labelDensity: graph.order > 200 ? 1 : 2,
      labelGridCellSize: 90,
      labelRenderedSizeThreshold: graph.order > 300 ? 12 : 6,
      labelFont: "var(--font-body), sans-serif",
      labelColor: { color: "#eae5d9" },
      labelWeight: "500",
      defaultEdgeType: showingOverview ? "curve" : "line",
      edgeProgramClasses: { curve: EdgeCurveProgram },
      renderEdgeLabels: false,
      defaultDrawNodeHover: (context, data, settings) => {
        // Ink plate + parchment text: readable over any node color.
        const label = data.label;
        if (!label) return;
        const size = data.size ?? 4;
        const font = `${settings.labelWeight} ${settings.labelSize}px ${settings.labelFont}`;
        context.font = font;
        const width = context.measureText(label).width + 14;
        const height = settings.labelSize + 10;
        const x = data.x + size + 4;
        const y = data.y - height / 2;
        context.fillStyle = "#0a0e1a";
        context.beginPath();
        context.roundRect(x, y, width, height, 4);
        context.fill();
        context.strokeStyle = "rgba(201,169,97,0.6)";
        context.lineWidth = 1;
        context.stroke();
        context.fillStyle = "#eae5d9";
        context.fillText(label, x + 7, data.y + settings.labelSize / 3);
      },
      nodeReducer: (node, data) => {
        const state = brainUI();
        const res = { ...data };
        const active = state.hoveredId ?? state.selectedId;
        if (active && active !== node) {
          if (!adjacency.get(active)?.has(node)) {
            res.color = `${res.baseColor}33`; // fade unrelated
            res.label = "";
          } else {
            res.size = (res.baseSize ?? data.size) * 1.15;
          }
        }
        if (state.selectedId === node) {
          res.highlighted = true;
          res.size = (res.baseSize ?? data.size) * 1.3;
        }
        if (state.combineMode && state.combinePicks.includes(node)) {
          res.highlighted = true;
          res.color = "#c9a961";
          res.size = (res.baseSize ?? data.size) * 1.4;
        }
        return res;
      },
      edgeReducer: (edge, data) => {
        const state = brainUI();
        const active = state.hoveredId ?? state.selectedId;
        if (!active) return data;
        const [a, b] = graph.extremities(edge);
        const relevant = a === active || b === active;
        return relevant
          ? { ...data, color: "rgba(232,205,140,0.95)", size: 2.4 }
          : { ...data, color: data.color, size: data.size };
      },
    });

    // Cinematic entrance: settle wide, then ease into the constellation
    const camera = sigma.getCamera();
    camera.setState({ ratio: 2.4, x: 0, y: 0 });
    camera.animate({ ratio: 1 }, { duration: 1400, easing: "quadraticOut" });

    sigma.on("enterNode", ({ node }) => brainUI().setHovered(node));
    sigma.on("leaveNode", () => brainUI().setHovered(null));
    sigma.on("clickNode", ({ node }) => {
      if (showingOverview && node.startsWith("island:")) {
        const hubId = islandHubId.get(node.slice("island:".length));
        if (brainUI().combineMode && hubId) {
          brainUI().pickForCombine(hubId);
          return;
        }
        setFocusedCluster(node.slice("island:".length));
        return;
      }
      if (brainUI().combineMode) {
        brainUI().pickForCombine(node);
        return;
      }
      brainUI().select(node);
      focusNode(sigma, graph, node);
    });
    sigma.on("clickStage", () => brainUI().select(null));

    // Direct manipulation: drag stars through the sky
    let draggedId: string | null = null;
    sigma.on("downNode", ({ node }) => {
      draggedId = node;
      sigma.getCamera().disable();
    });
    sigma.getMouseCaptor().on("mousemovebody", (e) => {
      if (!draggedId) return;
      const pos = sigma.viewportToGraph(e);
      graph.setNodeAttribute(draggedId, "x", pos.x);
      graph.setNodeAttribute(draggedId, "y", pos.y);
      e.preventSigmaDefault();
      e.original.preventDefault();
      e.original.stopPropagation();
    });
    const endDrag = () => {
      if (draggedId) sigma.getCamera().enable();
      draggedId = null;
    };
    sigma.getMouseCaptor().on("mouseup", endDrag);
    sigma.getMouseCaptor().on("mouseleave", endDrag);

    // EdgeCurveProgram widens the generic; our reducers guarantee NodeAttrs.
    sigmaRef.current = sigma as unknown as Sigma<NodeAttrs>;

    return () => {
      sigma.kill();
      sigmaRef.current = null;
    };
  }, [graphData, viewMode, domainFilter, focusedCluster]);

  // Selection/hover state changes need an explicit refresh for reducers to re-run.
  useEffect(() => {
    return useBrainStore.subscribe(() => {
      sigmaRef.current?.refresh();
    });
  }, []);

  if (isPending) {
    return (
      <div className="flex h-full items-center justify-center" aria-busy="true">
        <div className="space-y-3 text-center">
          <div className="mx-auto h-16 w-16 rounded-full bg-[var(--accent-muted)] shadow-[0_0_30px_rgba(201,169,97,0.25)]" />
          <p className="text-sm text-[var(--text-secondary)]">Mapping your Brain…</p>
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex h-full items-center justify-center p-8">
        <div
          role="alert"
          className="max-w-sm rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-6 text-center"
        >
          <p className="mb-4 text-sm text-[var(--danger)]">
            Couldn&apos;t load your Brain. The API may be unreachable.
          </p>
          <button
            onClick={() => void refetch()}
            className="rounded-lg bg-[var(--accent)] px-4 py-2 text-sm font-semibold text-white hover:bg-[var(--accent-hover)]"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (graphData && graphData.nodes.length === 0) {
    return <EmptyBrain />;
  }

  return (
    <div className="relative h-full w-full" style={{ filter: "drop-shadow(0 0 10px rgba(200, 176, 120, 0.22))" }}>
      <div aria-hidden className="graticule absolute inset-0 opacity-20" />
      <div ref={containerRef} className="absolute inset-0" aria-label="Knowledge graph canvas" />
      {focusedCluster && (
        <button
          onClick={() => setFocusedCluster(null)}
          className="absolute left-4 top-4 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-2 text-xs font-medium text-[var(--text-secondary)] shadow-[var(--shadow-md)] hover:text-[var(--text-primary)]"
        >
          ← All islands
        </button>
      )}
      <DomainLegend nodes={graphData?.nodes ?? []} />
      <ZoomControls sigmaRef={sigmaRef} />
    </div>
  );
}

function focusNode(
  sigma: { getCamera: () => { ratio: number; animate: (state: object, opts?: object) => void } },
  graph: Graph<NodeAttrs>,
  nodeId: string,
) {
  if (!graph.hasNode(nodeId)) return;
  const attrs = graph.getNodeAttributes(nodeId);
  const camera = sigma.getCamera();
  camera.animate(
    {
      x: attrs.x,
      y: attrs.y,
      ratio: Math.min(Math.max(camera.ratio, 0.7), 1.4),
    },
    { duration: 350, easing: "quadraticOut" },
  );
}

function ZoomControls({ sigmaRef }: { sigmaRef: React.RefObject<Sigma<NodeAttrs> | null> }) {
  const zoom = (factor: number) => {
    const sigma = sigmaRef.current;
    if (!sigma) return;
    const camera = sigma.getCamera();
    camera.animate({ ratio: camera.ratio * factor }, { duration: 200 });
  };

  return (
    <div className="absolute bottom-4 right-4 flex flex-col gap-1.5">
      {[
        { label: "Zoom in", glyph: "+", action: () => zoom(0.7) },
        { label: "Zoom out", glyph: "−", action: () => zoom(1.4) },
        {
          label: "Fit view",
          glyph: "⤢",
          action: () =>
            sigmaRef.current?.getCamera().animate({ ratio: 1, x: 0, y: 0 }, { duration: 300 }),
        },
      ].map(({ label, glyph, action }) => (
        <button
          key={label}
          onClick={action}
          aria-label={label}
          title={label}
          className="flex h-9 w-9 items-center justify-center rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] text-[var(--text-secondary)] shadow-[var(--shadow-md)] transition-colors duration-[var(--duration-fast)] hover:bg-[var(--bg-raised)] hover:text-[var(--text-primary)]"
        >
          {glyph}
        </button>
      ))}
    </div>
  );
}

function DomainLegend({ nodes }: { nodes: BrainNode[] }) {
  const domains = [...new Set(nodes.map((n) => n.domain).filter(Boolean))] as string[];
  if (domains.length === 0) return null;

  return (
    <div className="absolute bottom-4 left-4 flex flex-wrap gap-2 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)]/85 p-3 backdrop-blur-sm">
      {domains.slice(0, 8).map((domain) => (
        <span key={domain} className="flex items-center gap-1.5 text-xs text-[var(--text-secondary)]">
          <span
            aria-hidden
            className="inline-block h-2 w-2 rounded-full"
            style={{ background: domainColor(domain) }}
          />
          {domain}
        </span>
      ))}
    </div>
  );
}

function EmptyBrain() {
  return (
    <div className="flex h-full flex-col items-center justify-center p-8 text-center">
      <div className="mb-6 flex h-20 w-20 items-center justify-center rounded-3xl bg-[var(--accent-muted)] text-3xl">
        🧠
      </div>
      <h2 className="mb-2 text-xl font-semibold">Your Brain is empty</h2>
      <p className="mb-8 max-w-md text-sm leading-relaxed text-[var(--text-secondary)]">
        Every topic you add becomes a living node here — connected by what you learn,
        colored by mastery, and growing as you do.
      </p>
      <div className="w-full max-w-sm rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-6 shadow-[var(--shadow-md)]">
        <AddInterest />
      </div>
    </div>
  );
}
