"use client";
import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { Loader2, ChevronRight, CheckCircle, XCircle, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Sidebar } from "@/components/Sidebar";
import { Markdown } from "@/components/Markdown";
import { useSession } from "next-auth/react";
import { getToken } from "@/lib/auth";
import {
  startAssessment,
  submitAssessmentAnswer,
  getNextAssessmentQuestion,
  completeAssessment,
} from "@/lib/api";
import type {
  QuestionDTO,
  ConfidenceLevel,
  AssessmentStartResponseDTO,
} from "@/types/dto";

const CONFIDENCE_OPTS: Array<{
  label: string;
  value: ConfidenceLevel;
  className: string;
}> = [
  {
    label: "Not sure",
    value: "not_sure",
    className: "bg-slate-100 text-slate-700 hover:bg-slate-200",
  },
  {
    label: "Fairly sure",
    value: "fairly_sure",
    className: "bg-amber-50 text-amber-700 hover:bg-amber-100 border-amber-200",
  },
  {
    label: "Certain",
    value: "certain",
    className: "bg-green-50 text-green-700 hover:bg-green-100 border-green-200",
  },
];

export default function AssessmentQuestionPage() {
  const router            = useRouter();
  const params            = useParams();
  const bookId            = params.bookId as string;
  const { data: session } = useSession();

  const [question, setQuestion]       = useState<QuestionDTO | null>(null);
  const [nodeId, setNodeId]           = useState("");
  const [nodeTitle, setNodeTitle]     = useState("");
  const [topicIndex, setTopicIndex]   = useState(1);
  const [totalTopics, setTotalTopics] = useState(10);

  const [confidence, setConfidence]   = useState<ConfidenceLevel | "">("");
  const [selected, setSelected]       = useState<number | null>(null);
  const [freeText, setFreeText]       = useState("");
  const [submitted, setSubmitted]     = useState(false);
  const [isCorrect, setIsCorrect]     = useState<boolean | null>(null);
  const [explanation, setExplanation] = useState<string | null>(null);
  const [correctAnswer, setCorrectAnswer] = useState<string | null>(null);
  const [correctOption, setCorrectOption] = useState<number | null>(null);
  const [branchStop, setBranchStop]   = useState(false);

  const [loading, setLoading]         = useState(true);
  const [nextLoading, setNextLoading] = useState(false);
  const [error, setError]             = useState("");

  useEffect(() => {
    const token = getToken(session);
    if (!token) return;

    startAssessment(token, bookId)
      .then((data) => {
        if (data.done) {
          router.push(`/book/${bookId}/assessment/results`);
          return;
        }
        applyQuestion(data as AssessmentStartResponseDTO);
        setLoading(false);
      })
      .catch(() => {
        setError("Could not start assessment. Is the backend running?");
        setLoading(false);
      });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [bookId, session]);

  function applyQuestion(data: AssessmentStartResponseDTO) {
    setQuestion(data.question);
    setNodeId(data.nodeId);
    setNodeTitle(data.nodeTitle);
    setTopicIndex(data.topicIndex);
    setTotalTopics(data.totalTopics);
    // Reset answer state
    setSelected(null);
    setFreeText("");
    setConfidence("");
    setSubmitted(false);
    setIsCorrect(null);
    setExplanation(null);
    setCorrectAnswer(null);
    setCorrectOption(null);
    setBranchStop(false);
  }

  const submit = async () => {
    if (!confidence || !question) return;
    const token = getToken(session);
    const answer = question.type === "mcq" ? (selected ?? 0) : freeText;

    setSubmitted(true);

    try {
      const data = await submitAssessmentAnswer(token, {
        bookId,
        nodeId,
        questionId: question.id,
        answer,
        confidence,
      });
      setIsCorrect(data.correct);
      setExplanation(data.explanation ?? null);
      setCorrectAnswer(data.correctAnswer ?? null);
      setCorrectOption(data.correctOption ?? null);
      setBranchStop(!data.isMastered);
    } catch {
      setError("Failed to submit answer.");
    }
  };

  const next = async () => {
    setNextLoading(true);
    const token = getToken(session);

    try {
      const data = await getNextAssessmentQuestion(token, bookId);
      if (data.done) {
        // Complete the assessment before navigating to results
        await completeAssessment(token, bookId).catch(() => {});
        router.push(`/book/${bookId}/assessment/results`);
        return;
      }
      applyQuestion(data as AssessmentStartResponseDTO);
    } catch {
      setError("Failed to get next question.");
    } finally {
      setNextLoading(false);
    }
  };

  const skipToResults = async () => {
    const token = getToken(session);
    await completeAssessment(token, bookId).catch(() => {});
    router.push(`/book/${bookId}/assessment/results`);
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
            <Button variant="outline" onClick={() => router.push(`/book/${bookId}/assessment`)}>
              Go back
            </Button>
          </div>
        </main>
      </div>
    );
  }

  const pct = Math.round((topicIndex / totalTopics) * 100);
  const canSubmit =
    confidence !== "" &&
    (question?.type === "mcq" ? selected !== null : freeText.trim().length > 0);

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 ml-16 lg:ml-56 p-6">
        <div className="max-w-2xl mx-auto">
          {/* Progress bar */}
          <div className="mb-6">
            <div className="flex items-center justify-between text-sm text-slate-500 mb-2">
              <span className="font-medium text-slate-700">{nodeTitle}</span>
              <span>Topic {topicIndex} of ~{totalTopics}</span>
            </div>
            <Progress value={pct} />
          </div>

          {question && (
            <Card className="mb-6">
              <CardContent className="p-6 space-y-5">
                {/* Tier badge */}
                <Badge variant="info" className="capitalize">{question.type}</Badge>

                {/* Question body */}
                <Markdown className="text-base font-medium text-slate-900">
                  {question.body}
                </Markdown>

                {/* Confidence selector (shown before submit) */}
                {!submitted && (
                  <div>
                    <p className="text-sm font-medium text-slate-700 mb-2">
                      How confident are you?
                    </p>
                    <div className="flex gap-2">
                      {CONFIDENCE_OPTS.map((opt) => (
                        <button
                          id={`confidence-${opt.value}`}
                          key={opt.value}
                          onClick={() => setConfidence(opt.value)}
                          className={`flex-1 py-2 px-3 rounded-lg border text-sm font-medium transition-all ${
                            confidence === opt.value
                              ? "ring-2 ring-indigo-500 " + opt.className
                              : "border-slate-200 " + opt.className
                          }`}
                        >
                          {opt.label}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* MCQ options */}
                {!submitted && question.type === "mcq" && question.options && (
                  <div className="space-y-2">
                    {question.options.map((opt, i) => (
                      <button
                        id={`option-${i}`}
                        key={i}
                        onClick={() => setSelected(i)}
                        className={`w-full text-left px-4 py-3 rounded-lg border text-sm transition-all ${
                          selected === i
                            ? "border-indigo-500 bg-indigo-50 text-indigo-700"
                            : "border-slate-200 hover:border-slate-300"
                        }`}
                      >
                        <span className="font-medium mr-2">
                          {String.fromCharCode(65 + i)}.
                        </span>
                        {opt}
                      </button>
                    ))}
                  </div>
                )}

                {/* Free-text input */}
                {!submitted &&
                  (question.type === "theory" || question.type === "applied") && (
                    <textarea
                      id="input-free-text"
                      value={freeText}
                      onChange={(e) => setFreeText(e.target.value)}
                      placeholder="Type your answer..."
                      rows={4}
                      className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
                    />
                  )}

                {/* Feedback after submit */}
                {submitted && (
                  <div
                    className={`flex items-start gap-3 p-4 rounded-xl ${
                      isCorrect
                        ? "bg-emerald-50 border border-emerald-200"
                        : "bg-red-50 border border-red-200"
                    }`}
                  >
                    {isCorrect ? (
                      <CheckCircle className="h-5 w-5 text-emerald-600 mt-0.5" />
                    ) : (
                      <XCircle className="h-5 w-5 text-red-500 mt-0.5" />
                    )}
                    <div>
                      <p
                        className={`text-sm font-medium ${
                          isCorrect ? "text-emerald-700" : "text-red-700"
                        }`}
                      >
                        {isCorrect ? "Correct!" : "Not quite."}
                      </p>
                      {!isCorrect && correctAnswer && (
                        <div className="mt-2 text-xs">
                          <span className="font-semibold text-slate-700">Correct answer: </span>
                          {correctOption !== null && question?.options?.[correctOption] ? (
                            <span className="text-slate-700">
                              {String.fromCharCode(65 + correctOption)}. {question.options[correctOption]}
                            </span>
                          ) : (
                            <Markdown className="inline text-slate-700">{correctAnswer}</Markdown>
                          )}
                        </div>
                      )}
                      {explanation && (
                        <div className="text-xs text-slate-600 mt-1">
                          <Markdown>{explanation}</Markdown>
                        </div>
                      )}
                      {confidence === "certain" && !isCorrect && (
                        <p className="text-xs text-red-600 mt-1 flex items-center gap-1">
                          <AlertCircle className="h-3 w-3" /> You were certain but incorrect
                          — flagged for priority revision.
                        </p>
                      )}
                    </div>
                  </div>
                )}

                {branchStop && submitted && (
                  <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 text-sm text-slate-600">
                    We&apos;ll teach <strong>{nodeTitle}</strong> and topics that build on it
                    from scratch. Moving on.
                  </div>
                )}

                {/* Actions */}
                <div className="flex gap-3">
                  {!submitted ? (
                    <>
                      <Button
                        id="btn-dont-know"
                        variant="outline"
                        onClick={() => {
                          setConfidence("not_sure");
                          setSelected(null);
                          setFreeText("");
                          // Submit with "not_sure" confidence and no answer
                          setTimeout(() => submit(), 0);
                        }}
                      >
                        I don&apos;t know
                      </Button>
                      <Button
                        id="btn-submit-answer"
                        onClick={submit}
                        disabled={!canSubmit}
                        className="flex-1"
                      >
                        Submit answer
                      </Button>
                    </>
                  ) : (
                    <Button
                      id="btn-next-topic"
                      onClick={next}
                      disabled={nextLoading}
                      className="flex-1"
                    >
                      {nextLoading ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <>Next topic <ChevronRight className="h-4 w-4" /></>
                      )}
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Escape hatch */}
          <button
            onClick={skipToResults}
            className="text-xs text-slate-400 hover:text-slate-600 underline"
          >
            End assessment now and see results
          </button>
        </div>
      </main>
    </div>
  );
}
