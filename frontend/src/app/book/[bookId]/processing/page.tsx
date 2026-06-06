"use client";
import { useEffect, useRef, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { CheckCircle, Loader2, XCircle, ArrowRight, BrainCircuit } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Sidebar } from "@/components/Sidebar";
import { useSession } from "next-auth/react";
import { getToken } from "@/lib/auth";
import { getBookStatus } from "@/lib/api";
import type { BookStatus, ProcessingStep } from "@/types/dto";

const STAGES: Array<{ key: BookStatus | "done"; label: ProcessingStep; desc: string }> = [
  {
    key: "parsing",
    label: "Parsing & chunking",
    desc: "Extracting text and splitting into sections",
  },
  {
    key: "kg_built",
    label: "Extracting concepts",
    desc: "Identifying key concept nodes from each section",
  },
  {
    key: "kg_verified",
    label: "Inferring prerequisites",
    desc: "Building the prerequisite dependency graph",
  },
  {
    key: "done",
    label: "Ready for review",
    desc: "Knowledge graph built — review before starting",
  },
];

const STATUS_TO_INDEX: Record<string, number> = {
  uploaded: 0,
  parsing: 0,
  kg_built: 1,
  kg_verified: 2,
  ready: 3,
};

const POLL_INTERVAL_MS   = 3000;
const MAX_POLL_ATTEMPTS  = 80; // 4 minutes max

export default function ProcessingPage() {
  const router              = useRouter();
  const params              = useParams();
  const bookId              = params.bookId as string;
  const { data: session }   = useSession();

  const [bookTitle, setBookTitle]         = useState("Your book");
  const [status, setStatus]               = useState<BookStatus>("parsing");
  const [failed, setFailed]               = useState(false);
  const [failReason, setFailReason]       = useState("");
  const [estimatedSecs, setEstimatedSecs] = useState<number | null>(null);

  const attemptsRef = useRef(0);
  const timerRef    = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const token = getToken(session);

    const poll = async () => {
      try {
        const data = await getBookStatus(token, bookId);
        setStatus(data.status);
        setEstimatedSecs(data.estimatedSecondsRemaining);

        if (data.error) {
          setFailed(true);
          setFailReason(data.error);
          return;
        }

        if (data.status === "kg_verified" || data.status === "ready") {
          return; // done — stop polling, show CTA
        }

        if (attemptsRef.current++ < MAX_POLL_ATTEMPTS) {
          timerRef.current = setTimeout(poll, POLL_INTERVAL_MS);
        } else {
          setFailed(true);
          setFailReason("Processing is taking too long. Please try again.");
        }
      } catch {
        if (attemptsRef.current++ < MAX_POLL_ATTEMPTS) {
          // Backend might not be ready yet — keep polling silently
          timerRef.current = setTimeout(poll, POLL_INTERVAL_MS);
        } else {
          setFailed(true);
          setFailReason("Could not reach the backend. Is FastAPI running?");
        }
      }
    };

    // Also fetch book title separately (from book detail or status endpoint)
    // The status endpoint returns title if the backend includes it
    poll();

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [bookId, session]);

  const currentIdx = STATUS_TO_INDEX[status] ?? 0;
  const isDone     = status === "kg_verified" || status === "ready";

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 ml-16 lg:ml-56 p-6 max-w-xl">
        <div className="mt-12">
          <div className="flex items-center justify-center h-16 w-16 bg-indigo-100 rounded-2xl mb-6">
            <BrainCircuit className="h-8 w-8 text-indigo-600" />
          </div>

          <h1 className="text-2xl font-bold text-slate-900 mb-1">
            Building your knowledge graph
          </h1>
          {bookTitle && (
            <p className="text-slate-500 mb-8">{bookTitle}</p>
          )}

          {/* Pipeline stepper */}
          <div className="space-y-4 mb-10">
            {STAGES.map((stage, i) => {
              const done   = isDone ? true : i < currentIdx;
              const active = !isDone && i === currentIdx;

              return (
                <div key={stage.key} className="flex items-start gap-4">
                  <div className="mt-0.5 flex-shrink-0">
                    {failed && active ? (
                      <XCircle className="h-6 w-6 text-red-500" />
                    ) : done ? (
                      <CheckCircle className="h-6 w-6 text-emerald-500" />
                    ) : active ? (
                      <Loader2 className="h-6 w-6 text-indigo-500 animate-spin" />
                    ) : (
                      <div className="h-6 w-6 rounded-full border-2 border-slate-200" />
                    )}
                  </div>
                  <div>
                    <p
                      className={`text-sm font-medium ${
                        active
                          ? "text-indigo-700"
                          : done
                          ? "text-slate-700"
                          : "text-slate-400"
                      }`}
                    >
                      {stage.label}
                    </p>
                    {(active || done) && (
                      <p className="text-xs text-slate-500 mt-0.5">{stage.desc}</p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* ETA */}
          {!failed && !isDone && estimatedSecs !== null && estimatedSecs > 0 && (
            <p className="text-xs text-slate-400 mb-4">
              Estimated time remaining: ~{Math.ceil(estimatedSecs / 60)} min
            </p>
          )}

          {/* Result states */}
          {failed ? (
            <div className="bg-red-50 border border-red-200 rounded-xl p-4 mb-6">
              <p className="text-sm font-medium text-red-700">Processing failed</p>
              <p className="text-xs text-red-600 mt-1">{failReason}</p>
              <Button
                variant="outline"
                size="sm"
                className="mt-3"
                onClick={() => router.push("/upload")}
              >
                Try a different file
              </Button>
            </div>
          ) : isDone ? (
            <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 mb-6">
              <p className="text-sm font-medium text-emerald-700">
                Knowledge graph built!
              </p>
              <p className="text-xs text-emerald-600 mt-1">
                Review the graph before starting your learning journey.
              </p>
              <Button
                id="btn-review-graph"
                className="mt-3"
                onClick={() => router.push(`/book/${bookId}/verify`)}
              >
                Review graph <ArrowRight className="h-4 w-4" />
              </Button>
            </div>
          ) : (
            <p className="text-sm text-slate-500">
              This usually takes 1–2 minutes. You can leave — we&apos;ll notify you
              when it&apos;s ready.
            </p>
          )}

          <button
            id="btn-back-to-library"
            onClick={() => router.push("/library")}
            className="text-sm text-slate-400 hover:text-slate-600 underline mt-4 block"
          >
            Go back to library
          </button>
        </div>
      </main>
    </div>
  );
}
