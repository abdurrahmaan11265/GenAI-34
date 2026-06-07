"use client";
import { useEffect, useState, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  Send, BookOpen, X, CheckCircle, ChevronDown, ChevronUp, Loader2,
  MessageSquare, Sparkles,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Sidebar } from "@/components/Sidebar";
import { Markdown } from "@/components/Markdown";
import { useSession } from "next-auth/react";
import { getToken } from "@/lib/auth";
import { getBook, createSession, sendMessage, completeSession } from "@/lib/api";
import type { TutorMessageDTO, KGNodeDetailDTO } from "@/types/dto";

export default function LearnSessionPage() {
  const params            = useParams();
  const router            = useRouter();
  const bookId            = params.bookId as string;
  const nodeId            = params.nodeId as string;
  const { data: session } = useSession();

  const [node, setNode]               = useState<KGNodeDetailDTO | null>(null);
  const [sessionId, setSessionId]     = useState<string | null>(null);
  const [messages, setMessages]       = useState<TutorMessageDTO[]>([]);
  const [input, setInput]             = useState("");
  const [sending, setSending]         = useState(false);
  const [questionSaved, setQuestionSaved] = useState(false);
  const [sourceOpen, setSourceOpen]   = useState(false);
  const [completing, setCompleting]   = useState(false);
  const [completed, setCompleted]     = useState(false);
  const [unlockedNodes, setUnlockedNodes] = useState<string[]>([]);
  const [error, setError]             = useState("");

  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const token = getToken(session);
    if (!token) return;

    // Load node details
    getBook(token, bookId)
      .then(({ book }) => {
        const n = book?.nodes?.find((x) => x.id === nodeId);
        if (n) setNode(n);
      })
      .catch(() => setError("Failed to load node data."));

    // Create session
    createSession(token, { bookId, mode: "learning", nodeIds: [nodeId] })
      .then(({ session: s }) => {
        setSessionId(s.id);
        // Opening Socratic message
        setMessages([
          {
            role: "assistant",
            content: `Let's explore this concept together. Before I explain anything — what do you already know or think about this topic? Any initial thoughts or questions?`,
            timestamp: new Date().toISOString(),
          },
        ]);
      })
      .catch(() => setError("Failed to start session. Is the backend running?"));
  }, [bookId, nodeId, session]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = async () => {
    if (!input.trim() || !sessionId || sending) return;
    const msg = input.trim();
    const isQuestion =
      msg.includes("?") ||
      msg.toLowerCase().startsWith("what") ||
      msg.toLowerCase().startsWith("how") ||
      msg.toLowerCase().startsWith("why");

    setInput("");
    setSending(true);

    const userMsg: TutorMessageDTO = {
      role: "user",
      content: msg,
      timestamp: new Date().toISOString(),
      isQuestion,
    };
    setMessages((prev) => [...prev, userMsg]);
    if (isQuestion) setQuestionSaved(true);

    const token = getToken(session);

    try {
      const data = await sendMessage(token, sessionId, {
        message: msg,
        nodeId,
        isQuestion,
      });

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: data.response,
          timestamp: new Date().toISOString(),
          savedQuestionId: data.savedQuestionId,
        },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Sorry, I had trouble processing that. Could you try again?",
          timestamp: new Date().toISOString(),
        },
      ]);
    } finally {
      setSending(false);
    }
  };

  const complete = async () => {
    if (!sessionId) return;
    setCompleting(true);
    const token = getToken(session);

    try {
      const data = await completeSession(token, sessionId);
      setUnlockedNodes(data.unlockedNodes ?? []);
      setCompleted(true);
    } catch {
      alert("Failed to complete session.");
    } finally {
      setCompleting(false);
    }
  };

  const sourceChunks = node?.sourceChunks ?? [];

  if (error) {
    return (
      <div className="flex min-h-screen">
        <Sidebar />
        <main className="flex-1 ml-16 lg:ml-56 flex flex-col items-center justify-center">
          <p className="text-red-600 mb-4">{error}</p>
          <Button variant="outline" onClick={() => router.push(`/book/${bookId}/course`)}>
            Go back
          </Button>
        </main>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex-1 ml-16 lg:ml-56 flex flex-col" style={{ height: "100vh" }}>
        {/* Header */}
        <div className="border-b border-slate-200 bg-white px-6 py-3 flex items-center justify-between shrink-0">
          <div>
            <div className="flex items-center gap-2">
              <Badge variant="info" className="text-xs">Learning</Badge>
              <span className="font-semibold text-slate-900 text-sm">
                {node?.title ?? "Loading..."}
              </span>
            </div>
            {node?.sectionName && (
              <p className="text-xs text-slate-400 mt-0.5">§ {node.sectionName}</p>
            )}
          </div>
          <div className="flex items-center gap-2">
            {questionSaved && (
              <div className="flex items-center gap-1.5 text-xs text-indigo-600 bg-indigo-50 px-2 py-1 rounded-full border border-indigo-200">
                <MessageSquare className="h-3 w-3" /> Question saved for revision
              </div>
            )}
            <Button
              id="btn-complete-node"
              variant="success"
              size="sm"
              onClick={complete}
              disabled={completing || completed || !sessionId}
            >
              {completing ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <CheckCircle className="h-4 w-4" />
              )}
              I&apos;ve got this
            </Button>
            <button
              onClick={() => router.push(`/book/${bookId}/course`)}
              className="text-slate-400 hover:text-slate-600"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Completion overlay */}
        {completed && (
          <div className="absolute inset-0 bg-black/50 flex items-center justify-center z-50">
            <Card className="max-w-md w-full mx-4 shadow-2xl">
              <CardContent className="p-6 text-center">
                <div className="h-16 w-16 bg-emerald-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <CheckCircle className="h-8 w-8 text-emerald-600" />
                </div>
                <h2 className="text-xl font-bold text-slate-900 mb-2">
                  Node mastered!
                </h2>
                <p className="text-slate-600 text-sm mb-4">
                  {node?.title} is now in your spaced-repetition schedule.
                </p>
                {unlockedNodes.length > 0 && (
                  <div className="bg-indigo-50 rounded-lg p-3 mb-4 text-left">
                    <p className="text-xs font-semibold text-indigo-700 mb-1 flex items-center gap-1">
                      <Sparkles className="h-3.5 w-3.5" /> Unlocked{" "}
                      {unlockedNodes.length} new topic
                      {unlockedNodes.length > 1 ? "s" : ""}:
                    </p>
                    {unlockedNodes.map((n, i) => (
                      <p key={i} className="text-xs text-indigo-600">
                        → {n}
                      </p>
                    ))}
                  </div>
                )}
                <Button
                  id="btn-back-to-plan"
                  className="w-full"
                  onClick={() => router.push(`/book/${bookId}`)}
                >
                  Back to daily plan
                </Button>
              </CardContent>
            </Card>
          </div>
        )}

        <div className="flex flex-1 overflow-hidden">
          {/* Chat area */}
          <div className="flex-1 flex flex-col">
            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-6 space-y-4">
              {messages.map((m, i) => (
                <div
                  key={i}
                  className={`flex ${
                    m.role === "user" ? "justify-end" : "justify-start"
                  }`}
                >
                  {m.role === "assistant" && (
                    <div className="h-7 w-7 bg-indigo-100 rounded-full flex items-center justify-center mr-2 mt-1 shrink-0">
                      <span className="text-xs">🧠</span>
                    </div>
                  )}
                  <div
                    className={`max-w-[75%] px-4 py-3 rounded-2xl text-sm leading-relaxed ${
                      m.role === "user"
                        ? "bg-indigo-600 text-white rounded-br-sm"
                        : "bg-white border border-slate-200 text-slate-800 rounded-bl-sm shadow-sm"
                    }`}
                  >
                    {m.role === "assistant" ? (
                      <Markdown>{m.content}</Markdown>
                    ) : (
                      m.content
                    )}
                  </div>
                </div>
              ))}
              {sending && (
                <div className="flex justify-start">
                  <div className="h-7 w-7 bg-indigo-100 rounded-full flex items-center justify-center mr-2 shrink-0">
                    <span className="text-xs">🧠</span>
                  </div>
                  <div className="bg-white border border-slate-200 rounded-2xl rounded-bl-sm px-4 py-3 shadow-sm">
                    <Loader2 className="h-4 w-4 animate-spin text-slate-400" />
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Source panel */}
            {sourceChunks[0] && (
              <div className="border-t border-slate-200 bg-slate-50">
                <button
                  id="btn-toggle-source"
                  onClick={() => setSourceOpen((v) => !v)}
                  className="w-full flex items-center justify-between px-6 py-2 text-xs text-slate-500 hover:text-slate-700"
                >
                  <span className="flex items-center gap-1.5">
                    <BookOpen className="h-3.5 w-3.5" /> Book reference
                  </span>
                  {sourceOpen ? (
                    <ChevronDown className="h-4 w-4" />
                  ) : (
                    <ChevronUp className="h-4 w-4" />
                  )}
                </button>
                {sourceOpen && (
                  <div className="px-6 pb-4">
                    <p className="text-xs text-slate-600 leading-relaxed bg-white border border-slate-200 rounded-lg p-3 max-h-32 overflow-y-auto">
                      {sourceChunks[0].slice(0, 500)}...
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* Input */}
            <div className="border-t border-slate-200 bg-white p-4">
              <div className="flex gap-2">
                <input
                  id="input-chat"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && send()}
                  placeholder="Reply or ask a question... (questions are saved for revision)"
                  className="flex-1 px-4 py-2.5 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  disabled={!sessionId || completed}
                />
                <Button
                  id="btn-send-message"
                  onClick={send}
                  disabled={!input.trim() || sending || !sessionId || completed}
                  size="icon"
                >
                  <Send className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
