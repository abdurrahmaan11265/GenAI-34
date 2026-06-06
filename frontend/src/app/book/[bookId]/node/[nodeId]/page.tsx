"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, BookOpen, Lock, MessageSquare, RefreshCw, ChevronRight, Loader2, ExternalLink } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Sidebar } from "@/components/Sidebar";
import { NodeStateBadge } from "@/components/NodeStateBadge";
import { timeAgo, daysUntil, formatDate } from "@/lib/utils";

export default function NodeDetailPage() {
  const params = useParams();
  const router = useRouter();
  const bookId = params.bookId as string;
  const nodeId = params.nodeId as string;

  const [node, setNode] = useState<Record<string, unknown> | null>(null);
  const [userState, setUserState] = useState<Record<string, unknown> | null>(null);
  const [prereqs, setPrereqs] = useState<Array<Record<string, unknown>>>([]);
  const [unlocks, setUnlocks] = useState<Array<Record<string, unknown>>>([]);
  const [pastQuestions, setPastQuestions] = useState<Array<{ id: string; body: string; source: string }>>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`/api/books/${bookId}`)
      .then(r => r.json())
      .then(({ book }) => {
        const n = book?.nodes?.find((x: Record<string, unknown>) => x.id === nodeId);
        if (!n) { setLoading(false); return; }

        setNode(n);
        const us = (n.userNodeStates as Array<Record<string, unknown>>)?.[0];
        setUserState(us ?? null);

        // Prereqs: nodes that this node depends on
        const prereqIds = new Set((n.incomingEdges as Array<{ fromNodeId: string; type: string }>).filter((e) => e.type === "prerequisite").map(e => e.fromNodeId));
        setPrereqs(book.nodes.filter((x: Record<string, unknown>) => prereqIds.has(x.id as string)));

        // Unlocks: nodes this node is a prereq for
        const unlockIds = new Set((n.outgoingEdges as Array<{ toNodeId: string; type: string }>).filter((e) => e.type === "prerequisite").map(e => e.toNodeId));
        setUnlocks(book.nodes.filter((x: Record<string, unknown>) => unlockIds.has(x.id as string)));

        // Past user-asked questions
        const qs = (n.questions as Array<{ id: string; body: string; source: string }>)?.filter((q) => q.source === "user_asked") ?? [];
        setPastQuestions(qs);
        setLoading(false);
      });
  }, [bookId, nodeId]);

  if (loading) return (
    <div className="flex min-h-screen"><Sidebar />
      <main className="flex-1 ml-16 lg:ml-56 flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-indigo-500" />
      </main>
    </div>
  );

  if (!node) return (
    <div className="flex min-h-screen"><Sidebar />
      <main className="flex-1 ml-16 lg:ml-56 p-6">Node not found.</main>
    </div>
  );

  const state = (userState?.state ?? "locked") as string;
  const isLocked = state === "locked";
  const isMastered = state === "mastered" || state === "due";

  const sourceChunks = JSON.parse((node.sourceChunks as string) || "[]") as string[];

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 ml-16 lg:ml-56 p-6 max-w-2xl">
        <button onClick={() => router.push(`/book/${bookId}/course`)} className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700 mb-6">
          <ArrowLeft className="h-4 w-4" /> Course
        </button>

        {/* Header */}
        <div className="mb-6">
          <div className="flex items-start justify-between gap-4 mb-2">
            <h1 className="text-2xl font-bold text-slate-900">{node.title as string}</h1>
            <NodeStateBadge state={state as "locked" | "available" | "in_progress" | "mastered" | "due"} />
          </div>
          <p className="text-slate-600 leading-relaxed">{node.summary as string}</p>
        </div>

        {/* Metrics */}
        {userState && (
          <div className="grid grid-cols-3 gap-3 mb-6">
            <Card><CardContent className="p-3 text-center">
              <p className="text-xl font-bold text-slate-900">{Math.round(((userState.masteryScore as number) ?? 0) * 100)}%</p>
              <p className="text-xs text-slate-500">Mastery</p>
            </CardContent></Card>
            <Card><CardContent className="p-3 text-center">
              <p className="text-sm font-semibold text-slate-700">{timeAgo(userState.lastReviewed as string)}</p>
              <p className="text-xs text-slate-500">Last reviewed</p>
            </CardContent></Card>
            <Card><CardContent className="p-3 text-center">
              <p className="text-sm font-semibold text-slate-700">{daysUntil(userState.nextDue as string)}</p>
              <p className="text-xs text-slate-500">Next due</p>
            </CardContent></Card>
          </div>
        )}

        {/* Source excerpt */}
        {sourceChunks[0] && (
          <Card className="mb-6">
            <CardContent className="p-4">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2 flex items-center gap-1.5">
                <BookOpen className="h-3.5 w-3.5" /> Source excerpt
              </p>
              <p className="text-sm text-slate-700 leading-relaxed line-clamp-4">{sourceChunks[0]}</p>
            </CardContent>
          </Card>
        )}

        {/* Prerequisites */}
        {prereqs.length > 0 && (
          <div className="mb-5">
            <p className="text-sm font-semibold text-slate-700 mb-2">Prerequisites</p>
            <div className="space-y-1.5">
              {prereqs.map(p => {
                const ps = (p.userNodeStates as Array<Record<string, unknown>>)?.[0];
                return (
                  <div key={p.id as string} className="flex items-center gap-2 text-sm text-slate-600">
                    <span className={`h-2 w-2 rounded-full ${ps?.state === "mastered" ? "bg-emerald-500" : "bg-slate-300"}`} />
                    {p.title as string}
                    {ps?.state != null && <Badge variant={ps.state as "locked"} className="text-[10px] ml-auto">{String(ps.state)}</Badge>}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Unlocks */}
        {unlocks.length > 0 && (
          <div className="mb-5">
            <p className="text-sm font-semibold text-slate-700 mb-2">This unlocks</p>
            <div className="space-y-1.5">
              {unlocks.map(u => (
                <div key={u.id as string} className="flex items-center gap-2 text-sm text-slate-500">
                  <ChevronRight className="h-3.5 w-3.5 text-indigo-400" />
                  {u.title as string}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Past user questions */}
        {pastQuestions.length > 0 && (
          <div className="mb-6">
            <p className="text-sm font-semibold text-slate-700 mb-2 flex items-center gap-1.5">
              <MessageSquare className="h-4 w-4 text-indigo-400" /> Your past questions
            </p>
            <div className="space-y-2">
              {pastQuestions.map(q => (
                <div key={q.id} className="bg-slate-50 rounded-lg px-3 py-2 text-sm text-slate-600 border border-slate-100">
                  {q.body}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* CTAs */}
        <div className="flex gap-3">
          {isLocked ? (
            <div className="flex items-center gap-2 text-sm text-slate-500 bg-slate-50 border border-slate-200 rounded-lg px-4 py-2.5">
              <Lock className="h-4 w-4" /> Complete prerequisites to unlock this node.
            </div>
          ) : isMastered ? (
            <>
              <Button variant="outline" className="flex-1" onClick={() => router.push(`/book/${bookId}/revision`)}>
                <RefreshCw className="h-4 w-4" /> Revise
              </Button>
              <Button className="flex-1" onClick={() => router.push(`/book/${bookId}/learn/${nodeId}`)}>
                <BookOpen className="h-4 w-4" /> Learn again
              </Button>
            </>
          ) : (
            <Button className="flex-1" size="lg" onClick={() => router.push(`/book/${bookId}/learn/${nodeId}`)}>
              <BookOpen className="h-4 w-4" /> Learn this
            </Button>
          )}
        </div>
      </main>
    </div>
  );
}
