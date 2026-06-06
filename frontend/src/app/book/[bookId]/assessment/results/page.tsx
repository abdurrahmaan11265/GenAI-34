"use client";
import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { CheckCircle, BookOpen, Lock, AlertTriangle, Map, ArrowRight, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Sidebar } from "@/components/Sidebar";
import { useSession } from "next-auth/react";
import { getToken } from "@/lib/auth";
import { completeAssessment } from "@/lib/api";
import type { AssessmentCompleteResponseDTO, NodeState } from "@/types/dto";

const STATE_COLOR: Record<NodeState, string> = {
  mastered:    "bg-emerald-500",
  available:   "bg-indigo-400",
  in_progress: "bg-blue-400",
  due:         "bg-orange-400",
  locked:      "bg-slate-200",
};

export default function AssessmentResultsPage() {
  const router            = useRouter();
  const params            = useParams();
  const bookId            = params.bookId as string;
  const { data: session } = useSession();

  const [results, setResults] = useState<AssessmentCompleteResponseDTO | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState("");

  useEffect(() => {
    const token = getToken(session);
    if (!token) return;

    completeAssessment(token, bookId)
      .then((data) => {
        setResults(data);
        setLoading(false);
      })
      .catch(() => {
        setError("Could not load assessment results.");
        setLoading(false);
      });
  // eslint-disable-next-line react-hooks/exhaustive-deps
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

  if (error || !results) {
    return (
      <div className="flex min-h-screen">
        <Sidebar />
        <main className="flex-1 ml-16 lg:ml-56 p-6">
          <p className="text-red-600">{error || "No results"}</p>
          <Button className="mt-4" onClick={() => router.push(`/book/${bookId}`)}>
            Go to book
          </Button>
        </main>
      </div>
    );
  }

  const total =
    results.mastered + results.available + results.locked;

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 ml-16 lg:ml-56 flex items-center justify-center p-6">
        <div className="max-w-lg w-full">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold text-slate-900 mb-2">
              Here&apos;s where you&apos;re starting.
            </h1>
            <p className="text-slate-500">
              We&apos;ve mapped your knowledge so you don&apos;t repeat what you already know.
            </p>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-3 gap-3 mb-8">
            <Card className="text-center p-4">
              <CheckCircle className="h-6 w-6 text-emerald-500 mx-auto mb-2" />
              <p className="text-2xl font-bold text-slate-900">{results.mastered}</p>
              <p className="text-xs text-slate-500">Already mastered</p>
            </Card>
            <Card className="text-center p-4">
              <BookOpen className="h-6 w-6 text-indigo-500 mx-auto mb-2" />
              <p className="text-2xl font-bold text-slate-900">{results.available}</p>
              <p className="text-xs text-slate-500">Ready to learn</p>
            </Card>
            <Card className="text-center p-4">
              <Lock className="h-6 w-6 text-slate-400 mx-auto mb-2" />
              <p className="text-2xl font-bold text-slate-900">{results.locked}</p>
              <p className="text-xs text-slate-500">Locked (prereqs first)</p>
            </Card>
          </div>

          {/* Progress bar */}
          {total > 0 && (
            <div className="mb-6">
              <div className="flex rounded-full overflow-hidden h-3">
                <div
                  className="bg-emerald-500 transition-all"
                  style={{ width: `${(results.mastered / total) * 100}%` }}
                />
                <div
                  className="bg-indigo-400 transition-all"
                  style={{ width: `${(results.available / total) * 100}%` }}
                />
                <div
                  className="bg-slate-200 transition-all"
                  style={{ width: `${(results.locked / total) * 100}%` }}
                />
              </div>
              <div className="flex justify-between text-xs text-slate-400 mt-1">
                <span>Mastered</span>
                <span>Available</span>
                <span>Locked</span>
              </div>
            </div>
          )}

          {/* Mini graph preview */}
          {results.graphPreview.length > 0 && (
            <Card className="mb-6">
              <CardContent className="p-4">
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">
                  Knowledge graph preview
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {results.graphPreview.map((node) => (
                    <span
                      key={node.id}
                      title={`${node.title} — ${node.state}`}
                      className={`inline-block h-3 w-3 rounded-sm ${STATE_COLOR[node.state]} opacity-80`}
                    />
                  ))}
                </div>
                <div className="flex items-center gap-4 mt-3">
                  {(
                    [
                      ["bg-emerald-500", "Mastered"],
                      ["bg-indigo-400",  "Available"],
                      ["bg-slate-200",   "Locked"],
                    ] as [string, string][]
                  ).map(([cls, label]) => (
                    <span key={label} className="flex items-center gap-1 text-xs text-slate-500">
                      <span className={`h-2.5 w-2.5 rounded-sm ${cls}`} />{label}
                    </span>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Confident-but-wrong weak spots */}
          {results.weakSpots.length > 0 && (
            <Card className="mb-6 border-amber-200">
              <CardContent className="p-4">
                <div className="flex items-center gap-2 mb-2">
                  <AlertTriangle className="h-4 w-4 text-amber-500" />
                  <p className="text-sm font-medium text-amber-700">
                    Confident-but-wrong — priority revision later
                  </p>
                </div>
                <ul className="space-y-1">
                  {results.weakSpots.map((s, i) => (
                    <li
                      key={i}
                      className="text-xs text-slate-600 flex items-center gap-1.5"
                    >
                      <span className="h-1.5 w-1.5 rounded-full bg-amber-400 shrink-0" />
                      {s}
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}

          {/* CTAs */}
          <div className="grid grid-cols-2 gap-3">
            <Button
              id="btn-see-graph"
              variant="outline"
              onClick={() => router.push(`/book/${bookId}/graph`)}
            >
              <Map className="h-4 w-4" /> See my graph
            </Button>
            <Button
              id="btn-start-learning"
              onClick={() => router.push(`/book/${bookId}`)}
            >
              Start learning <ArrowRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </main>
    </div>
  );
}
