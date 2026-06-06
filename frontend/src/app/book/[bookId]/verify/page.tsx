"use client";
import { useEffect, useState, useCallback } from "react";
import { useRouter, useParams } from "next/navigation";
import ReactFlow, {
  Node,
  Edge,
  Controls,
  Background,
  MiniMap,
  useNodesState,
  useEdgesState,
  addEdge,
  Connection,
  MarkerType,
} from "reactflow";
import "reactflow/dist/style.css";
import { AlertTriangle, CheckCircle, Loader2, Info } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Sidebar } from "@/components/Sidebar";
import { useSession } from "next-auth/react";
import { getToken } from "@/lib/auth";
import { getGraph, getBook, confirmGraph } from "@/lib/api";
import type { KGNodeDTO, KGEdgeDTO } from "@/types/dto";

const DIFF_COLORS: Record<string, string> = {
  beginner: "#10b981",
  intermediate: "#6366f1",
  advanced: "#f59e0b",
};

export default function GraphVerifyPage() {
  const router            = useRouter();
  const params            = useParams();
  const bookId            = params.bookId as string;
  const { data: session } = useSession();

  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [rawNodes, setRawNodes]          = useState<KGNodeDTO[]>([]);
  const [selected, setSelected]          = useState<KGNodeDTO | KGEdgeDTO | null>(null);
  const [loading, setLoading]            = useState(true);
  const [confirming, setConfirming]      = useState(false);
  const [hasLowConf, setHasLowConf]      = useState(false);
  const [bookTitle, setBookTitle]        = useState("");
  const [error, setError]                = useState("");

  useEffect(() => {
    const token = getToken(session);
    if (!token) return;

    Promise.all([
      getGraph(token, bookId),
      getBook(token, bookId),
    ])
      .then(([graph, { book }]) => {
        setRawNodes(graph.nodes);
        const lowConf = graph.edges.some((e) => e.confidence < 0.6);
        setHasLowConf(lowConf);
        setBookTitle(book?.title ?? "");

        // Layout nodes in a DAG-ish grid (placeholder for Dagre layout)
        const flowNodes: Node[] = graph.nodes.map((n, i) => ({
          id: n.id,
          data: { label: n.title, tier: n.difficultyTier },
          position: { x: (i % 4) * 220, y: Math.floor(i / 4) * 120 },
          style: {
            background: "#fff",
            border: `2px solid ${DIFF_COLORS[n.difficultyTier] ?? "#6366f1"}`,
            borderRadius: 10,
            padding: "8px 14px",
            fontSize: 12,
            fontWeight: 500,
            color: "#1e293b",
            maxWidth: 180,
          },
        }));

        const flowEdges: Edge[] = graph.edges.map((e) => ({
          id: e.id ?? `${e.fromNodeId}-${e.toNodeId}`,
          source: e.fromNodeId,
          target: e.toNodeId,
          animated: e.confidence < 0.6,
          style: {
            stroke: e.confidence < 0.6 ? "#f97316" : "#94a3b8",
            strokeWidth: e.confidence < 0.6 ? 2 : 1.5,
          },
          label: e.confidence < 0.6 ? `⚠ ${Math.round(e.confidence * 100)}%` : undefined,
          labelStyle: { fontSize: 10, fill: "#f97316" },
          markerEnd: { type: MarkerType.ArrowClosed, color: "#94a3b8" },
        }));

        setNodes(flowNodes);
        setEdges(flowEdges);
        setLoading(false);
      })
      .catch(() => {
        setError("Failed to load graph verification view.");
        setLoading(false);
      });
  }, [bookId, session]);

  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  );

  const onNodeClick = (_: React.MouseEvent, node: Node) => {
    const raw = rawNodes.find((n) => n.id === node.id);
    if (raw) setSelected(raw);
  };

  const handleConfirm = async () => {
    setConfirming(true);
    const token = getToken(session);

    try {
      await confirmGraph(token, bookId);
      router.push(`/book/${bookId}/assessment`);
    } catch {
      alert("Failed to confirm graph.");
      setConfirming(false);
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-screen">
        <Sidebar />
        <main className="flex-1 ml-16 lg:ml-56 flex items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-indigo-500" />
        </main>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex min-h-screen">
        <Sidebar />
        <main className="flex-1 ml-16 lg:ml-56 flex items-center justify-center p-6">
          <div className="text-center">
            <p className="text-red-600 mb-4">{error}</p>
            <Button variant="outline" onClick={() => router.push("/library")}>
              Go back
            </Button>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex-1 ml-16 lg:ml-56 flex flex-col">
        {/* Header */}
        <div className="border-b border-slate-200 bg-white px-6 py-4 flex items-center justify-between">
          <div>
            <h1 className="font-bold text-slate-900">Review Knowledge Graph</h1>
            <p className="text-sm text-slate-500">{bookTitle}</p>
          </div>
          <div className="flex items-center gap-3">
            {hasLowConf && (
              <div className="flex items-center gap-1.5 text-amber-600 text-sm bg-amber-50 px-3 py-1.5 rounded-lg border border-amber-200">
                <AlertTriangle className="h-4 w-4" />
                Low-confidence edges highlighted in orange
              </div>
            )}
            <Button
              id="btn-confirm-graph"
              onClick={handleConfirm}
              disabled={confirming}
            >
              {confirming ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <CheckCircle className="h-4 w-4" />
              )}
              Looks good — mark ready
            </Button>
          </div>
        </div>

        <div className="flex flex-1">
          {/* Graph */}
          <div className="flex-1" style={{ height: "calc(100vh - 80px)" }}>
            <ReactFlow
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onConnect={onConnect}
              onNodeClick={onNodeClick}
              fitView
            >
              <Controls />
              <MiniMap nodeStrokeWidth={3} />
              <Background gap={16} color="#f1f5f9" />
            </ReactFlow>
          </div>

          {/* Side panel */}
          <div className="w-72 border-l border-slate-200 bg-white p-4 overflow-y-auto">
            <div className="mb-4">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
                Legend
              </p>
              <div className="space-y-1.5">
                {Object.entries(DIFF_COLORS).map(([tier, color]) => (
                  <div key={tier} className="flex items-center gap-2 text-xs">
                    <div
                      className="h-3 w-3 rounded-sm border-2"
                      style={{ borderColor: color }}
                    />
                    <span className="capitalize">{tier}</span>
                  </div>
                ))}
                <div className="flex items-center gap-2 text-xs text-orange-600 mt-2">
                  <div className="h-0.5 w-6 bg-orange-400" />
                  Low-confidence edge
                </div>
              </div>
            </div>

            {selected && "title" in selected && (
              <Card>
                <CardContent className="p-3 space-y-2">
                  <p className="font-semibold text-sm text-slate-900">
                    {(selected as KGNodeDTO).title}
                  </p>
                  <Badge
                    variant={(selected as KGNodeDTO).difficultyTier as "default"}
                    className="capitalize text-xs"
                  >
                    {(selected as KGNodeDTO).difficultyTier}
                  </Badge>
                  <p className="text-xs text-slate-600">
                    {(selected as KGNodeDTO).summary}
                  </p>
                  {(selected as KGNodeDTO).sectionName && (
                    <p className="text-xs text-slate-400">
                      § {(selected as KGNodeDTO).sectionName}
                    </p>
                  )}
                  <details className="text-xs">
                    <summary className="cursor-pointer text-slate-500 flex items-center gap-1">
                      <Info className="h-3 w-3" />
                      Source text
                    </summary>
                    <p className="mt-1 text-slate-600 bg-slate-50 rounded p-2 leading-relaxed">
                      {(selected as KGNodeDTO).sourceChunks?.[0]?.slice(0, 300)}...
                    </p>
                  </details>
                </CardContent>
              </Card>
            )}

            {!selected && (
              <p className="text-xs text-slate-400 text-center mt-8">
                Click a node to inspect it
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
