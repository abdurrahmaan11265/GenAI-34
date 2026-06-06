"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Clock, RefreshCw, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Sidebar } from "@/components/Sidebar";
import { estimateMinutes, timeAgo, daysUntil } from "@/lib/utils";
import { useSession } from "next-auth/react";
import { getToken } from "@/lib/auth";
import { getBook, getRevisionQueue } from "@/lib/api";
import type { RevisionCardDTO } from "@/types/dto";

export default function RevisionListPage() {
  const params            = useParams();
  const router            = useRouter();
  const bookId            = params.bookId as string;
  const { data: session } = useSession();

  const [dueNodes, setDueNodes]           = useState<RevisionCardDTO[]>([]);
  const [upcomingNodes, setUpcomingNodes] = useState<RevisionCardDTO[]>([]);
  const [tab, setTab]                     = useState<"due" | "upcoming">("due");
  const [loading, setLoading]             = useState(true);
  const [bookTitle, setBookTitle]         = useState("");

  useEffect(() => {
    const token = getToken(session);
    if (!token) return;

    Promise.all([
      getBook(token, bookId),
      getRevisionQueue(token, bookId),
    ])
      .then(([{ book }, queue]) => {
        setBookTitle(book?.title ?? "");
        setDueNodes(queue.due ?? []);
        setUpcomingNodes(queue.upcoming ?? []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [bookId, session]);

  const displayed = tab === "due" ? dueNodes : upcomingNodes;

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
      <main className="flex-1 ml-16 lg:ml-56 p-6 max-w-2xl">
        <div className="flex items-center gap-3 mb-6">
          <button
            onClick={() => router.push(`/book/${bookId}`)}
            className="text-slate-400 hover:text-slate-600"
          >
            <ArrowLeft className="h-5 w-5" />
          </button>
          <div>
            <h1 className="font-bold text-slate-900 text-xl">Revision</h1>
            <p className="text-sm text-slate-500">{bookTitle}</p>
          </div>
        </div>

        {/* Summary */}
        <div className="flex items-center gap-4 mb-6">
          <div className="flex items-center gap-2 text-sm">
            <Clock className="h-4 w-4 text-orange-500" />
            <span className="font-medium text-slate-900">
              {dueNodes.length} due now
            </span>
          </div>
          <span className="text-slate-300">·</span>
          <span className="text-sm text-slate-500">
            {estimateMinutes(dueNodes.length)} min estimated
          </span>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 bg-slate-100 rounded-xl p-1 mb-5 w-fit">
          <button
            id="tab-due"
            onClick={() => setTab("due")}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              tab === "due" ? "bg-white shadow-sm text-slate-900" : "text-slate-500"
            }`}
          >
            Due now ({dueNodes.length})
          </button>
          <button
            id="tab-upcoming"
            onClick={() => setTab("upcoming")}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              tab === "upcoming"
                ? "bg-white shadow-sm text-slate-900"
                : "text-slate-500"
            }`}
          >
            Upcoming ({upcomingNodes.length})
          </button>
        </div>

        {displayed.length === 0 ? (
          <div className="text-center py-16">
            <div className="h-16 w-16 bg-emerald-50 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <RefreshCw className="h-8 w-8 text-emerald-400" />
            </div>
            <h3 className="font-semibold text-slate-900 mb-1">
              {tab === "due" ? "All caught up!" : "Nothing upcoming"}
            </h3>
            <p className="text-sm text-slate-500">
              {tab === "due"
                ? "No reviews due today. Check the upcoming tab."
                : "Keep learning to build your review queue."}
            </p>
          </div>
        ) : (
          <>
            <div className="space-y-2 mb-6">
              {displayed.map((n, i) => (
                <Card key={i} className="hover:shadow-sm transition-shadow">
                  <CardContent className="p-4 flex items-center gap-4">
                    <div className="h-9 w-9 bg-orange-100 rounded-lg flex items-center justify-center shrink-0">
                      <RefreshCw className="h-4 w-4 text-orange-600" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-slate-900 truncate">
                        {n.nodeTitle}
                      </p>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className="text-xs text-slate-500">
                          {timeAgo(n.daysOverdue <= 0 ? new Date().toISOString() : null)} {/* Hack for UX — better handled in DTO */}
                        </span>
                        <span className="text-slate-300">·</span>
                        <span
                          className={`text-xs font-medium ${
                            tab === "due" ? "text-orange-600" : "text-slate-500"
                          }`}
                        >
                          {n.daysOverdue > 0 ? `${n.daysOverdue} days overdue` : "Due today"}
                        </span>
                      </div>
                    </div>
                    <div className="text-right shrink-0">
                      <div className="text-xs font-medium text-slate-600">
                        {Math.round((n.recallProbability ?? 0.9) * 100)}% recall
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>

            {tab === "due" && (
              <Button
                id="btn-start-revision"
                className="w-full"
                size="lg"
                onClick={() => router.push(`/book/${bookId}/revision/session`)}
              >
                Start revision session ({dueNodes.length} cards)
              </Button>
            )}
          </>
        )}
      </main>
    </div>
  );
}
