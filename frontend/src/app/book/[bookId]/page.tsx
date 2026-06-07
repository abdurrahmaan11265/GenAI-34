"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  BookOpen, Flame, Clock, RefreshCw, Map, ChevronRight, CheckCircle,
  Loader2, Sparkles,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ProgressRing } from "@/components/ProgressRing";
import { Sidebar } from "@/components/Sidebar";
import { estimateMinutes } from "@/lib/utils";
import { useSession } from "next-auth/react";
import { getToken } from "@/lib/auth";
import { getBook, getDailyPlan } from "@/lib/api";
import type { BookDetailDTO, DailyPlanDTO, PlanMode } from "@/types/dto";

const MODE_INFO: Record<PlanMode, { title: string; desc: string; color: string }> = {
  revise_only: {
    title: "Revision day",
    desc: "You have reviews due — let's keep your memory sharp.",
    color: "bg-orange-50 border-orange-200",
  },
  learn_only: {
    title: "Learning day",
    desc: "Nothing due yet — time to unlock new concepts.",
    color: "bg-indigo-50 border-indigo-200",
  },
  both: {
    title: "Mixed session",
    desc: "A bit of revision, a bit of new learning.",
    color: "bg-slate-50 border-slate-200",
  },
  all_caught_up: {
    title: "All caught up! 🎉",
    desc: "No reviews due and no new nodes available yet.",
    color: "bg-emerald-50 border-emerald-200",
  },
};

export default function BookHomePage() {
  const params            = useParams();
  const router            = useRouter();
  const bookId            = params.bookId as string;
  const { data: session } = useSession();

  const [book, setBook]   = useState<BookDetailDTO | null>(null);
  const [plan, setPlan]   = useState<DailyPlanDTO | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = getToken(session);
    if (!token) return;

    Promise.all([
      getBook(token, bookId),
      getDailyPlan(token, bookId),
    ])
      .then(([{ book: b }, planData]) => {
        setBook(b);
        setPlan(planData);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [bookId, session]);

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

  const planInfo = MODE_INFO[plan?.mode ?? "all_caught_up"];

  const handleStartPlan = () => {
    if (!plan) return;
    if (plan.mode === "revise_only" || plan.mode === "both") {
      router.push(`/book/${bookId}/revision`);
    } else {
      router.push(`/book/${bookId}/course`);
    }
  };

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 ml-16 lg:ml-56 p-6 max-w-3xl">
        {/* Book header */}
        <div className="flex items-start gap-5 mb-8">
          <div className="h-20 w-14 bg-gradient-to-br from-indigo-400 to-purple-600 rounded-lg flex items-center justify-center shrink-0">
            <BookOpen className="h-7 w-7 text-white/80" />
          </div>
          <div className="flex-1">
            <h1 className="text-2xl font-bold text-slate-900">{book?.title}</h1>
            {book?.author && (
              <p className="text-slate-500 text-sm">{book.author}</p>
            )}
            <div className="flex items-center gap-4 mt-2">
              {(book?.bookStreak ?? 0) > 0 && (
                <div className="flex items-center gap-1 text-sm text-orange-600">
                  <Flame className="h-4 w-4" /> {book?.bookStreak}d streak
                </div>
              )}
              {plan && (
                <span className="text-sm text-slate-500">
                  {plan.masteredCount}/{plan.totalNodes} mastered
                </span>
              )}
            </div>
          </div>
          {plan && (
            <ProgressRing pct={plan.progressPct} size={64} stroke={6} />
          )}
        </div>

        {/* Today's plan card */}
        <Card className={`mb-6 border-2 ${planInfo.color}`}>
          <CardContent className="p-5">
            <div className="flex items-center justify-between mb-3">
              <div>
                <h2 className="font-bold text-slate-900">{planInfo.title}</h2>
                <p className="text-sm text-slate-600 mt-0.5">{planInfo.desc}</p>
              </div>
              {plan?.mode !== "all_caught_up" && (
                <div className="text-right">
                  <p className="text-2xl font-bold text-slate-900">
                    {estimateMinutes(plan?.planNodes.length ?? 0)}
                  </p>
                  <p className="text-xs text-slate-500">min today</p>
                </div>
              )}
            </div>

            {/* Plan breakdown preview */}
            {(plan?.planNodes?.length ?? 0) > 0 && (
              <div className="space-y-2 mb-4">
                {plan?.planNodes.slice(0, 5).map((n, i) => (
                  <div
                    key={i}
                    className="bg-white rounded-lg p-2.5 border border-slate-100"
                  >
                    <div className="flex items-center gap-3">
                      <Badge
                        variant={n.planType === "revise" ? "due" : "available"}
                        className="text-[10px] shrink-0"
                      >
                        {n.planType === "revise" ? (
                          <><RefreshCw className="h-2.5 w-2.5" /> Revise</>
                        ) : (
                          <><Sparkles className="h-2.5 w-2.5" /> Learn</>
                        )}
                      </Badge>
                      <span className="text-sm text-slate-700 flex-1 truncate">
                        {n.node?.title ?? n.nodeId}
                      </span>
                      <ChevronRight className="h-4 w-4 text-slate-300" />
                    </div>
                    {(n.subtopics?.length ?? 0) > 0 && (
                      <div className="flex flex-wrap gap-1.5 mt-2 pl-1">
                        {n.subtopics!.map((st, si) => (
                          <span key={si} className="text-[10px] text-slate-500 bg-slate-100 rounded-full px-2 py-0.5">
                            {st}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
                {(plan?.planNodes.length ?? 0) > 5 && (
                  <p className="text-xs text-slate-400 text-center">
                    +{(plan?.planNodes.length ?? 0) - 5} more
                  </p>
                )}
              </div>
            )}

            {plan?.mode !== "all_caught_up" ? (
              <Button id="btn-start-plan" className="w-full" onClick={handleStartPlan}>
                Start today&apos;s plan
              </Button>
            ) : (
              <div className="flex items-center gap-2 text-sm text-emerald-700">
                <CheckCircle className="h-4 w-4" /> Come back tomorrow for your next review!
              </div>
            )}
          </CardContent>
        </Card>

        {/* Due load indicator */}
        {(plan?.dueCount ?? 0) > 0 && (
          <div className="flex items-center gap-2 bg-orange-50 border border-orange-200 rounded-lg px-4 py-2.5 mb-6 text-sm text-orange-700">
            <Clock className="h-4 w-4 shrink-0" />
            <span>
              <strong>{plan?.dueCount}</strong> concepts due for review today
            </span>
          </div>
        )}

        {/* Navigation tabs */}
        <div className="grid grid-cols-3 gap-3">
          <button
            id="btn-nav-course"
            onClick={() => router.push(`/book/${bookId}/course`)}
            className="flex flex-col items-center gap-2 p-4 bg-white border border-slate-200 rounded-xl hover:border-indigo-300 hover:bg-indigo-50 transition-colors"
          >
            <BookOpen className="h-5 w-5 text-indigo-500" />
            <span className="text-sm font-medium text-slate-700">Course</span>
          </button>
          <button
            id="btn-nav-revision"
            onClick={() => router.push(`/book/${bookId}/revision`)}
            className="flex flex-col items-center gap-2 p-4 bg-white border border-slate-200 rounded-xl hover:border-orange-300 hover:bg-orange-50 transition-colors relative"
          >
            <RefreshCw className="h-5 w-5 text-orange-500" />
            <span className="text-sm font-medium text-slate-700">Revision</span>
            {(plan?.dueCount ?? 0) > 0 && (
              <span className="absolute top-2 right-2 h-4 w-4 bg-orange-500 text-white text-[10px] rounded-full flex items-center justify-center">
                {plan?.dueCount}
              </span>
            )}
          </button>
          <button
            id="btn-nav-graph"
            onClick={() => router.push(`/book/${bookId}/graph`)}
            className="flex flex-col items-center gap-2 p-4 bg-white border border-slate-200 rounded-xl hover:border-purple-300 hover:bg-purple-50 transition-colors"
          >
            <Map className="h-5 w-5 text-purple-500" />
            <span className="text-sm font-medium text-slate-700">Graph</span>
          </button>
        </div>
      </main>
    </div>
  );
}
