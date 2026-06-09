"use client";
import { useEffect, useState, useCallback } from "react";
import { useRouter, useParams } from "next/navigation";
import { z } from "zod";
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
import { AlertTriangle, CheckCircle, Loader2, Info, Send, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Sidebar } from "@/components/Sidebar";
import { useSession } from "next-auth/react";
import { getToken } from "@/lib/auth";
import {
  getGraph,
  getBook,
  confirmGraph,
  deleteGraphNode,
  deleteGraphEdge,
  updateGraphNode,
  createGraphEdge,
  createGraphNode,
  updateGraphEdge,
} from "@/lib/api";
import type { KGNodeDTO, KGEdgeDTO } from "@/types/dto";

const DIFF_COLORS: Record<string, string> = {
  beginner:     "#10b981",
  intermediate: "#6366f1",
  advanced:     "#f59e0b",
};

// CR: Replace plain TS interfaces with Zod schemas; validate API response
const ChatProposalSchema = z.object({
  action:      z.string(),
  description: z.string(),
  nodeId:      z.string().optional(),
  edgeId:      z.string().optional(),
  fromNodeId:  z.string().optional(),
  toNodeId:    z.string().optional(),
  newTitle:    z.string().optional(),
  newSummary:  z.string().optional(),
});
type ChatProposal = z.infer<typeof ChatProposalSchema>;

// CR: Only these actions have a working applyProposal handler
const SUPPORTED_ACTIONS = new Set([
  "delete_node",
  "delete_edge",
  "rename_node",
  "update_node",
  "create_edge",
  "create_node",
  "update_edge",
]);

interface ChatMessage {
  role:      "user" | "assistant";
  text:      string;
  proposal?: ChatProposal;
  applied?:  boolean;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function GraphVerifyPage() {
  const router             = useRouter();
  const params             = useParams();
  const bookId             = params.bookId as string;
  // CR: also destructure status to detect loading vs unauthenticated
  const { data: session, status } = useSession();

  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [rawNodes, setRawNodes]          = useState<KGNodeDTO[]>([]);
  const [selected, setSelected]          = useState<KGNodeDTO | null>(null);
  const [loading, setLoading]            = useState(true);
  const [confirming, setConfirming]      = useState(false);
  const [hasLowConf, setHasLowConf]      = useState(false);
  const [bookTitle, setBookTitle]        = useState("");
  const [error, setError]                = useState("");

  const [chatInput, setChatInput]       = useState("");
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatLoading, setChatLoading]   = useState(false);

  const loadGraph = useCallback(async () => {
    // CR: don't act while NextAuth is still resolving
    if (status === "loading") return;

    const token = getToken(session);
    // CR: clear loading state and show error instead of stranding on spinner
    if (!token) {
      setLoading(false);
      setError("Please sign in again.");
      return;
    }

    setLoading(true);
    try {
      const [graph, { book }] = await Promise.all([
        getGraph(token, bookId),
        getBook(token, bookId),
      ]);
      setRawNodes(graph.nodes);
      setHasLowConf(graph.edges.some((e: KGEdgeDTO) => e.confidence < 0.6));
      setBookTitle(book?.title ?? "");

      const flowNodes: Node[] = graph.nodes.map((n: KGNodeDTO, i: number) => ({
        id:       n.id,
        data:     { label: n.title, tier: n.difficultyTier },
        position: { x: (i % 4) * 220, y: Math.floor(i / 4) * 120 },
        style: {
          background:  "#fff",
          border:      `2px solid ${DIFF_COLORS[n.difficultyTier] ?? "#6366f1"}`,
          borderRadius: 10,
          padding:     "8px 14px",
          fontSize:    12,
          fontWeight:  500,
          color:       "#1e293b",
          maxWidth:    180,
        },
      }));

      const flowEdges: Edge[] = graph.edges
        .filter((e: KGEdgeDTO) => String(e.type).toLowerCase() === "prerequisite")
        .map((e: KGEdgeDTO) => ({
          id:       e.id ?? `${e.fromNodeId}-${e.toNodeId}`,
          source:   e.fromNodeId,
          target:   e.toNodeId,
          animated: e.confidence < 0.6,
          style: {
            stroke:      e.confidence < 0.6 ? "#f97316" : "#94a3b8",
            strokeWidth: e.confidence < 0.6 ? 2 : 1.5,
          },
          label:      e.confidence < 0.6 ? `⚠ ${Math.round(e.confidence * 100)}%` : undefined,
          labelStyle: { fontSize: 10, fill: "#f97316" },
          markerEnd:  { type: MarkerType.ArrowClosed, color: "#94a3b8" },
        }));

      setNodes(flowNodes);
      setEdges(flowEdges);
    } catch {
      setError("Failed to load graph verification view.");
    } finally {
      setLoading(false);
    }
  }, [bookId, session, status]);

  useEffect(() => { loadGraph(); }, [loadGraph]);

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

  // ── Chat handlers ──────────────────────────────────────────────────────────

  const sendChatMessage = async () => {
    const token = getToken(session);
    if (!chatInput.trim() || !token) return;

    const userMsg: ChatMessage = { role: "user", text: chatInput };
    setChatMessages((prev) => [...prev, userMsg]);
    const sentInput = chatInput;
    setChatInput("");
    setChatLoading(true);

    try {
      const res = await fetch(
        `${API_BASE}/api/v1/books/${bookId}/graph/chat`,
        {
          method:  "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization:  `Bearer ${token}`,
          },
          body: JSON.stringify({ message: sentInput }),
        }
      );

      // CR: check HTTP status before parsing
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        const msg = errData?.detail?.error?.message ?? "Request failed. Try again.";
        setChatMessages((prev) => [...prev, { role: "assistant", text: msg }]);
        return;
      }

      const data = await res.json();

      // CR: Zod parse the proposal — don't trust raw API shape
      const parsed = ChatProposalSchema.safeParse(data.proposal);
      if (!parsed.success) {
        setChatMessages((prev) => [
          ...prev,
          { role: "assistant", text: "Received an unexpected response. Please try again." },
        ]);
        return;
      }

      const proposal = parsed.data;
      // CR: AI output is suggestion only — shown to user for review, not applied automatically
      const assistantMsg: ChatMessage = {
        role:     "assistant",
        text:     proposal.description,
        proposal: proposal,
      };
      setChatMessages((prev) => [...prev, assistantMsg]);
    } catch {
      setChatMessages((prev) => [
        ...prev,
        { role: "assistant", text: "Sorry, something went wrong. Try again." },
      ]);
    } finally {
      setChatLoading(false);
    }
  };

  const applyProposal = async (msg: ChatMessage, index: number) => {
    const token = getToken(session);
    if (!msg.proposal || !token) return;
    const p = msg.proposal;

    try {
      // CR: all mutations come from deterministic UI logic after user confirmation
      switch (p.action) {
        case "delete_node":
          if (p.nodeId) await deleteGraphNode(token, bookId, p.nodeId);
          break;
        case "delete_edge":
          if (p.edgeId) await deleteGraphEdge(token, bookId, p.edgeId);
          break;
        case "rename_node":
        case "update_node":
          if (p.nodeId)
            await updateGraphNode(token, bookId, p.nodeId, {
              title:   p.newTitle,
              summary: p.newSummary,
            });
          break;
        case "create_edge":
          if (p.fromNodeId && p.toNodeId)
            await createGraphEdge(token, bookId, {
              fromNodeId: p.fromNodeId,
              toNodeId:   p.toNodeId,
              type:       "prerequisite",
              confidence: 0.9,
            });
          break;
        // CR: handle remaining supported actions
        case "create_node":
          if (p.newTitle)
            await createGraphNode(token, bookId, {
              title:         p.newTitle,
              summary:       p.newSummary ?? "",
              difficultyTier: "beginner",
            });
          break;
        case "update_edge":
          if (p.edgeId)
            await updateGraphEdge(token, bookId, p.edgeId, {});
          break;
        default:
          return;
      }

      setChatMessages((prev) =>
        prev.map((m, i) => (i === index ? { ...m, applied: true } : m))
      );
      await loadGraph();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "unknown error";
      alert(`Failed to apply change: ${message}`);
    }
  };

  // ── Render ─────────────────────────────────────────────────────────────────

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
            <Button id="btn-confirm-graph" onClick={handleConfirm} disabled={confirming}>
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
          {/* Graph canvas */}
          <div className="flex-1" style={{ height: "calc(100vh - 80px)" }}>
            {/* CR: empty state when all nodes deleted */}
            {nodes.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full gap-4 text-slate-400">
                <p className="text-sm">No concepts in this graph yet.</p>
                <p className="text-xs">
                  Use the chat panel to add nodes, or go back and re-run ingestion.
                </p>
                <Button variant="outline" size="sm" onClick={() => router.push("/library")}>
                  Back to library
                </Button>
              </div>
            ) : (
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
            )}
          </div>

          {/* Right sidebar */}
          <div
            className="w-80 border-l border-slate-200 bg-white flex flex-col"
            style={{ height: "calc(100vh - 80px)" }}
          >
            {/* Legend */}
            <div className="p-4 border-b border-slate-100">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
                Legend
              </p>
              <div className="space-y-1.5">
                {Object.entries(DIFF_COLORS).map(([tier, color]) => (
                  <div key={tier} className="flex items-center gap-2 text-xs">
                    <div className="h-3 w-3 rounded-sm border-2" style={{ borderColor: color }} />
                    <span className="capitalize">{tier}</span>
                  </div>
                ))}
                <div className="flex items-center gap-2 text-xs text-orange-600 mt-2">
                  <div className="h-0.5 w-6 bg-orange-400" />
                  Low-confidence edge
                </div>
              </div>
            </div>

            {/* Selected node info */}
            {selected && (
              <div className="p-4 border-b border-slate-100">
                <Card>
                  <CardContent className="p-3 space-y-2">
                    <p className="font-semibold text-sm text-slate-900">{selected.title}</p>
                    <Badge variant={selected.difficultyTier as "default"} className="capitalize text-xs">
                      {selected.difficultyTier}
                    </Badge>
                    <p className="text-xs text-slate-600">{selected.summary}</p>
                    {selected.sectionName && (
                      <p className="text-xs text-slate-400">§ {selected.sectionName}</p>
                    )}
                    <details className="text-xs">
                      <summary className="cursor-pointer text-slate-500 flex items-center gap-1">
                        <Info className="h-3 w-3" />
                        Source text
                      </summary>
                      <p className="mt-1 text-slate-600 bg-slate-50 rounded p-2 leading-relaxed">
                        {selected.sourceChunks?.[0]?.slice(0, 300)}…
                      </p>
                    </details>
                  </CardContent>
                </Card>
              </div>
            )}

            {/* Chat panel */}
            <div className="flex flex-col flex-1 overflow-hidden">
              <div className="px-4 pt-3 pb-2 border-b border-slate-100">
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
                  Edit via chat
                </p>
                <p className="text-xs text-slate-400 mt-0.5">
                  Describe a change — the AI will suggest it for your review.
                </p>
              </div>

              {/* Messages */}
              <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
                {chatMessages.length === 0 && (
                  <p className="text-xs text-slate-400 text-center mt-4">
                    Try: "delete the node about X" or "add edge from A to B"
                  </p>
                )}
                {chatMessages.map((msg, i) => (
                  <div
                    key={i}
                    className={`flex flex-col gap-1 ${
                      msg.role === "user" ? "items-end" : "items-start"
                    }`}
                  >
                    <div
                      className={`text-xs rounded-lg px-3 py-2 max-w-[90%] ${
                        msg.role === "user"
                          ? "bg-indigo-500 text-white"
                          : "bg-slate-100 text-slate-800"
                      }`}
                    >
                      {msg.text}
                    </div>

                    {/* CR: only show Apply button for supported actions */}
                    {msg.proposal &&
                      msg.proposal.action !== "unknown" &&
                      SUPPORTED_ACTIONS.has(msg.proposal.action) &&
                      !msg.applied && (
                        <Button
                          size="sm"
                          variant="outline"
                          className="text-xs h-7 px-2 border-emerald-300 text-emerald-700 hover:bg-emerald-50"
                          onClick={() => applyProposal(msg, i)}
                        >
                          <CheckCircle className="h-3 w-3 mr-1" />
                          Apply this change
                        </Button>
                      )}

                    {msg.applied && (
                      <span className="text-xs text-emerald-600 flex items-center gap-1">
                        <CheckCircle className="h-3 w-3" /> Applied
                      </span>
                    )}
                  </div>
                ))}
                {chatLoading && (
                  <div className="flex items-center gap-2 text-xs text-slate-400">
                    <Loader2 className="h-3 w-3 animate-spin" />
                    Thinking…
                  </div>
                )}
              </div>

              {/* CR: accessible input + button */}
              <div className="p-3 border-t border-slate-100 flex gap-2">
                <label htmlFor="graph-chat-input" className="sr-only">
                  Describe a graph edit
                </label>
                <input
                  id="graph-chat-input"
                  type="text"
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  onKeyDown={(e) =>
                    e.key === "Enter" && !chatLoading && sendChatMessage()
                  }
                  placeholder="Describe an edit…"
                  aria-label="Describe a graph edit"
                  className="flex-1 text-xs border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-300"
                  disabled={chatLoading}
                />
                <Button
                  size="sm"
                  onClick={sendChatMessage}
                  disabled={chatLoading || !chatInput.trim()}
                  className="h-8 w-8 p-0"
                  aria-label="Send graph edit request"
                >
                  <Send className="h-3 w-3" />
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}