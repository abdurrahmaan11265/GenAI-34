"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import {
  Flame, BookOpen, TrendingUp, Trophy, Loader2, AlertTriangle,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { ProgressRing } from "@/components/ProgressRing";
import { Sidebar } from "@/components/Sidebar";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";
import { getToken } from "@/lib/auth";
import { getProgress } from "@/lib/api";
import type { ProgressDTO } from "@/types/dto";

export default function ProgressPage() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const [progress, setProgress] = useState<ProgressDTO | null>(null);
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState("");

  useEffect(() => {
    if (status === "unauthenticated") { router.push("/"); return; }
    if (status !== "authenticated") return;

    const token = getToken(session);
    getProgress(token)
      .then((data) => {
        setProgress(data);
        setLoading(false);
      })
      .catch(() => {
        setError("Could not load progress data.");
        setLoading(false);
      });
  }, [status, session, router]);

  if (status === "loading" || loading) {
    return (
      <div className="flex min-h-screen">
        <Sidebar />
        <main className="flex-1 ml-16 lg:ml-56 flex items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-indigo-500" />
        </main>
      </div>
    );
  }

  if (error || !progress) {
    return (
      <div className="flex min-h-screen">
        <Sidebar />
        <main className="flex-1 ml-16 lg:ml-56 p-6">
          <p className="text-red-600">{error || "No data"}</p>
        </main>
      </div>
    );
  }

  const { global: g, books, weakSpots } = progress;

  // Build chart data from activity history
  const chartData = g.activityHistory.slice(-14).map((d) => ({
    day: new Date(d.date).toLocaleDateString("en", { weekday: "short" }),
    reviewed: d.conceptsReviewed,
    learned: d.conceptsLearned,
  }));

  const retentionPct = Math.round(g.retentionRate * 100);

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 ml-16 lg:ml-56 p-6 max-w-4xl">
        <h1 className="text-2xl font-bold text-slate-900 mb-6">Progress</h1>

        {/* Global stats */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <Card>
            <CardContent className="p-4 flex items-center gap-3">
              <div className="h-10 w-10 bg-emerald-100 rounded-xl flex items-center justify-center">
                <Trophy className="h-5 w-5 text-emerald-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-900">
                  {g.totalConceptsMastered}
                </p>
                <p className="text-xs text-slate-500">Concepts mastered</p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 flex items-center gap-3">
              <div className="h-10 w-10 bg-indigo-100 rounded-xl flex items-center justify-center">
                <BookOpen className="h-5 w-5 text-indigo-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-900">{books.length}</p>
                <p className="text-xs text-slate-500">Books active</p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 flex items-center gap-3">
              <div className="h-10 w-10 bg-orange-100 rounded-xl flex items-center justify-center">
                <Flame className="h-5 w-5 text-orange-500" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-900">{g.globalStreak}</p>
                <p className="text-xs text-slate-500">Day streak</p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 flex items-center gap-3">
              <div className="h-10 w-10 bg-blue-100 rounded-xl flex items-center justify-center">
                <TrendingUp className="h-5 w-5 text-blue-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-900">{retentionPct}%</p>
                <p className="text-xs text-slate-500">Retention rate</p>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Activity chart */}
        <Card className="mb-8">
          <CardHeader>
            <CardTitle className="text-base">Activity — last 14 days</CardTitle>
          </CardHeader>
          <CardContent>
            {chartData.length === 0 ? (
              <div className="h-40 flex items-center justify-center text-sm text-slate-400">
                Start learning to see your activity chart.
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={160}>
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="day" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Line
                    type="monotone"
                    dataKey="reviewed"
                    stroke="#6366f1"
                    strokeWidth={2}
                    dot={false}
                    name="Reviewed"
                  />
                  <Line
                    type="monotone"
                    dataKey="learned"
                    stroke="#10b981"
                    strokeWidth={2}
                    dot={false}
                    name="Learned"
                  />
                </LineChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        {/* Weak spots */}
        {weakSpots.length > 0 && (
          <Card className="mb-8 border-amber-200">
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 text-amber-500" />
                Weak spots — priority for revision
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {weakSpots.map((ws) => (
                  <div
                    key={ws.nodeId}
                    className="flex items-center justify-between text-sm"
                  >
                    <div>
                      <span className="font-medium text-slate-800">{ws.nodeTitle}</span>
                      <span className="text-slate-400 ml-2 text-xs">
                        {ws.bookTitle}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant="warning" className="text-[10px]">
                        {Math.round(ws.masteryScore * 100)}% mastery
                      </Badge>
                      {ws.lapseCount > 0 && (
                        <span className="text-xs text-red-500">
                          {ws.lapseCount} lapse{ws.lapseCount > 1 ? "s" : ""}
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Per-book breakdown */}
        <h2 className="font-semibold text-slate-900 mb-4">Books</h2>
        {books.length === 0 ? (
          <p className="text-sm text-slate-500">
            No books yet —{" "}
            <button
              onClick={() => router.push("/upload")}
              className="text-indigo-600 hover:underline"
            >
              upload one
            </button>
            .
          </p>
        ) : (
          <div className="space-y-4">
            {books.map((book) => (
              <Card
                key={book.bookId}
                className="cursor-pointer hover:shadow-sm transition-shadow"
                onClick={() => router.push(`/book/${book.bookId}`)}
              >
                <CardContent className="p-4">
                  <div className="flex items-center gap-4">
                    <ProgressRing pct={book.progressPct} size={52} stroke={5} />
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-slate-900 truncate">{book.title}</p>
                      <div className="flex items-center gap-3 mt-1">
                        <span className="text-xs text-slate-500">
                          {book.masteredCount}/{book.totalNodes} mastered
                        </span>
                        {book.dueToday > 0 && (
                          <Badge variant="due" className="text-[10px]">
                            {book.dueToday} due
                          </Badge>
                        )}
                        {book.bookStreak > 0 && (
                          <span className="text-xs text-orange-500 flex items-center gap-0.5">
                            <Flame className="h-3 w-3" />{book.bookStreak}d
                          </span>
                        )}
                      </div>
                      <Progress value={book.progressPct} className="mt-2 h-1.5" />
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
