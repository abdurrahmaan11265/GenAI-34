"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  Lock, Loader2, ArrowLeft, RefreshCw, BookOpen, ChevronRight,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Sidebar } from "@/components/Sidebar";
import { NodeStateBadge } from "@/components/NodeStateBadge";
import { NODE_STATE_COLORS } from "@/lib/utils";
import { useSession } from "next-auth/react";
import { getToken } from "@/lib/auth";
import { getBook } from "@/lib/api";
import type { BookDetailDTO, KGNodeDetailDTO, NodeState } from "@/types/dto";

type TabType = "learning" | "revision";

export default function CourseViewPage() {
  const params            = useParams();
  const router            = useRouter();
  const bookId            = params.bookId as string;
  const { data: session } = useSession();

  const [book, setBook]   = useState<BookDetailDTO | null>(null);
  const [tab, setTab]     = useState<TabType>("learning");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = getToken(session);
    if (!token) return;

    getBook(token, bookId)
      .then(({ book: b }) => {
        setBook(b);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [bookId, session]);

  const nodes   = book?.nodes ?? [];
  const sections = [...new Set(nodes.map((n) => n.sectionName ?? "General"))];

  const filtered =
    tab === "revision"
      ? nodes.filter((n) => {
          const s = n.userNodeStates?.[0]?.state;
          return s === "due" || s === "mastered";
        })
      : nodes;

  const getNodeAction = (n: KGNodeDetailDTO) => {
    const state = n.userNodeStates?.[0]?.state ?? "locked";
    if (state === "locked") return null;
    if (state === "due") return () => router.push(`/book/${bookId}/revision`);
    return () => router.push(`/book/${bookId}/node/${n.id}`);
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

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 ml-16 lg:ml-56 max-w-3xl p-6">
        {/* Back */}
        <div className="flex items-center gap-3 mb-6">
          <button
            onClick={() => router.push(`/book/${bookId}`)}
            className="text-slate-400 hover:text-slate-600"
          >
            <ArrowLeft className="h-5 w-5" />
          </button>
          <h1 className="font-bold text-slate-900 text-xl">{book?.title}</h1>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 bg-slate-100 rounded-xl p-1 mb-6 w-fit">
          <button
            id="tab-learning"
            onClick={() => setTab("learning")}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              tab === "learning"
                ? "bg-white shadow-sm text-slate-900"
                : "text-slate-500"
            }`}
          >
            <BookOpen className="h-4 w-4" /> Learning
          </button>
          <button
            id="tab-revision"
            onClick={() => setTab("revision")}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              tab === "revision"
                ? "bg-white shadow-sm text-slate-900"
                : "text-slate-500"
            }`}
          >
            <RefreshCw className="h-4 w-4" /> Revision
          </button>
        </div>

        {/* Sections */}
        {sections.map((section) => {
          const sectionNodes = filtered.filter(
            (n) => (n.sectionName ?? "General") === section
          );
          if (sectionNodes.length === 0) return null;

          const mastered = sectionNodes.filter((n) => {
            const s = n.userNodeStates?.[0]?.state;
            return s === "mastered" || s === "due";
          }).length;
          const sectionPct = Math.round((mastered / sectionNodes.length) * 100);

          return (
            <div key={section} className="mb-8">
              <div className="flex items-center justify-between mb-3">
                <h2 className="font-semibold text-slate-800">{section}</h2>
                <div className="flex items-center gap-2 text-xs text-slate-500">
                  <span>
                    {mastered}/{sectionNodes.length}
                  </span>
                  <Progress value={sectionPct} className="w-20 h-1.5" />
                </div>
              </div>

              <div className="space-y-2">
                {sectionNodes.map((node) => {
                  const state = (node.userNodeStates?.[0]?.state ??
                    "locked") as NodeState;
                  const isLocked  = state === "locked";
                  const action    = getNodeAction(node);
                  const prereqTitle =
                    isLocked &&
                    node.incomingEdges?.[0]?.fromNodeId
                      ? nodes.find(
                          (n) => n.id === node.incomingEdges[0].fromNodeId
                        )?.title
                      : null;

                  return (
                    <div
                      key={node.id}
                      onClick={() => !isLocked && action?.()}
                      className={`flex items-center gap-4 p-4 rounded-xl border transition-all ${
                        isLocked
                          ? "bg-slate-50 border-slate-100 opacity-60 cursor-not-allowed"
                          : "bg-white border-slate-200 hover:border-indigo-200 hover:shadow-sm cursor-pointer"
                      }`}
                    >
                      <div
                        className={`h-9 w-9 rounded-lg flex items-center justify-center shrink-0 ${
                          NODE_STATE_COLORS[state]?.bg ?? "bg-slate-100"
                        }`}
                      >
                        {isLocked ? (
                          <Lock className="h-4 w-4 text-slate-400" />
                        ) : (
                          <span className="text-sm">
                            {state === "mastered"
                              ? "✓"
                              : state === "due"
                              ? "↺"
                              : "→"}
                          </span>
                        )}
                      </div>

                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <p
                            className={`text-sm font-medium truncate ${
                              isLocked ? "text-slate-400" : "text-slate-900"
                            }`}
                          >
                            {node.title}
                          </p>
                          <NodeStateBadge state={state} />
                        </div>
                        {isLocked && prereqTitle ? (
                          <p className="text-xs text-slate-400 mt-0.5">
                            Complete &quot;{prereqTitle}&quot; first
                          </p>
                        ) : (
                          <p className="text-xs text-slate-500 mt-0.5 truncate">
                            {node.summary}
                          </p>
                        )}
                      </div>

                      {!isLocked && (
                        <div className="text-right shrink-0">
                          {node.userNodeStates?.[0]?.masteryScore ? (
                            <p className="text-xs font-medium text-slate-700">
                              {Math.round(
                                node.userNodeStates[0].masteryScore * 100
                              )}
                              %
                            </p>
                          ) : null}
                          <ChevronRight className="h-4 w-4 text-slate-300 ml-auto mt-0.5" />
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </main>
    </div>
  );
}
