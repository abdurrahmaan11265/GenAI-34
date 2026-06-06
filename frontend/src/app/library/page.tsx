"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import {
  Bell, Plus, Flame, BookOpen, Clock, ChevronRight,
  Loader2, AlertTriangle, BrainCircuit, User, SortAsc,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { ProgressRing } from "@/components/ProgressRing";
import { Sidebar } from "@/components/Sidebar";
import { estimateMinutes } from "@/lib/utils";
import { getToken } from "@/lib/auth";
import { listBooks, listNotifications, getMe } from "@/lib/api";
import { ApiError } from "@/lib/api-client";
import type { BookSummaryDTO } from "@/types/dto";

const STATUS_BADGE: Record<
  string,
  { label: string; color: "default" | "warning" | "success" | "info" | "secondary" }
> = {
  uploaded:    { label: "Uploaded",      color: "secondary" },
  parsing:     { label: "Processing",    color: "info" },
  kg_built:    { label: "Processing",    color: "info" },
  kg_verified: { label: "Needs review",  color: "warning" },
  ready:       { label: "Ready",         color: "success" },
};

export default function LibraryPage() {
  const { data: session, status } = useSession();
  const router = useRouter();

  const [books, setBooks]               = useState<BookSummaryDTO[]>([]);
  const [globalStreak, setGlobalStreak] = useState(0);
  const [unreadCount, setUnreadCount]   = useState(0);
  const [loading, setLoading]           = useState(true);
  const [error, setError]               = useState("");
  const [sort, setSort]                 = useState<"recent" | "due" | "alpha">("recent");

  useEffect(() => {
    if (status === "unauthenticated") { router.push("/"); return; }
    if (status !== "authenticated") return;

    const token = getToken(session);

    Promise.all([
      listBooks(token),
      listNotifications(token),
      getMe(token),
    ])
      .then(([booksData, notifData, userData]) => {
        setBooks(booksData.books ?? []);
        setUnreadCount(
          (notifData.notifications ?? []).filter((n) => !n.read).length
        );
        setGlobalStreak(userData.user?.globalStreak ?? 0);
        setLoading(false);
      })
      .catch((err: ApiError) => {
        if (err.status === 401) { router.push("/"); return; }
        setError("Failed to load library. Is the backend running?");
        setLoading(false);
      });
  }, [status, session, router]);

  const totalDue = books.reduce((s, b) => s + b.dueToday, 0);

  const sorted = [...books].sort((a, b) => {
    if (sort === "due")   return b.dueToday - a.dueToday;
    if (sort === "alpha") return a.title.localeCompare(b.title);
    return 0; // "recent" — server returns by updatedAt desc
  });

  const getBookAction = (book: BookSummaryDTO) => {
    if (book.status === "kg_verified") return `/book/${book.id}/verify`;
    if (book.status === "ready")       return `/book/${book.id}`;
    if (book.status === "parsing" || book.status === "kg_built")
      return `/book/${book.id}/processing`;
    return `/book/${book.id}`;
  };

  // Most-due book for the "Start today's plan" CTA
  const priorityBook = [...books].sort((a, b) => b.dueToday - a.dueToday)[0];

  if (status === "loading" || loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-indigo-500" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-600 font-medium mb-2">{error}</p>
          <Button variant="outline" onClick={() => window.location.reload()}>
            Retry
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 ml-16 lg:ml-56 p-6 max-w-5xl">
        {/* Header */}
        <header className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">My Library</h1>
            <p className="text-sm text-slate-500 mt-0.5">
              Welcome back, {session?.user?.name?.split(" ")[0] ?? "there"}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="icon"
              className="relative"
              onClick={() => router.push("/notifications")}
              id="btn-notifications"
            >
              <Bell className="h-5 w-5" />
              {unreadCount > 0 && (
                <span className="absolute top-1 right-1 h-4 w-4 bg-red-500 text-white text-[10px] rounded-full flex items-center justify-center">
                  {unreadCount}
                </span>
              )}
            </Button>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => router.push("/settings")}
              id="btn-profile"
            >
              <User className="h-5 w-5" />
            </Button>
          </div>
        </header>

        {/* Streak + Summary strip */}
        {books.length > 0 && (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
            <Card className="p-4 flex items-center gap-3">
              <div className="h-10 w-10 bg-orange-100 rounded-xl flex items-center justify-center">
                <Flame className="h-5 w-5 text-orange-500" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-900">{globalStreak}</p>
                <p className="text-xs text-slate-500">Day streak</p>
              </div>
            </Card>

            <Card className="p-4 flex items-center gap-3">
              <div className="h-10 w-10 bg-red-100 rounded-xl flex items-center justify-center">
                <Clock className="h-5 w-5 text-red-500" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-900">{totalDue}</p>
                <p className="text-xs text-slate-500">Reviews due today</p>
              </div>
            </Card>

            <Card className="p-4 flex items-center gap-3 bg-indigo-600 border-indigo-600">
              <div className="h-10 w-10 bg-indigo-500 rounded-xl flex items-center justify-center">
                <BookOpen className="h-5 w-5 text-white" />
              </div>
              <div className="flex-1">
                <p className="text-sm font-semibold text-white">
                  {estimateMinutes(totalDue)} min plan
                </p>
                {priorityBook && (
                  <button
                    id="btn-start-plan"
                    onClick={() => router.push(getBookAction(priorityBook))}
                    className="text-xs text-indigo-200 hover:text-white underline"
                  >
                    Start today&apos;s plan →
                  </button>
                )}
              </div>
            </Card>
          </div>
        )}

        {/* Books grid */}
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold text-slate-900">Books ({books.length})</h2>
          <div className="flex items-center gap-2">
            <SortAsc className="h-4 w-4 text-slate-400" />
            <select
              id="select-sort"
              value={sort}
              onChange={(e) => setSort(e.target.value as typeof sort)}
              className="text-sm border border-slate-200 rounded-lg px-2 py-1 bg-white"
            >
              <option value="recent">Recently studied</option>
              <option value="due">Most due</option>
              <option value="alpha">A–Z</option>
            </select>
          </div>
        </div>

        {books.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-24 text-center">
            <div className="h-24 w-24 bg-indigo-50 rounded-3xl flex items-center justify-center mb-6">
              <BrainCircuit className="h-12 w-12 text-indigo-400" />
            </div>
            <h3 className="text-xl font-semibold text-slate-900 mb-2">No books yet</h3>
            <p className="text-slate-500 mb-6 max-w-sm">
              Upload your first book and Lexis will build a knowledge graph,
              assess your knowledge, then teach you concept by concept.
            </p>
            <Button id="btn-first-upload" onClick={() => router.push("/upload")}>
              <Plus className="h-4 w-4" />
              Upload your first book
            </Button>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {/* Add Book card */}
            <button
              id="btn-add-book"
              onClick={() => router.push("/upload")}
              className="flex flex-col items-center justify-center gap-3 p-8 rounded-xl border-2 border-dashed border-slate-200 text-slate-400 hover:border-indigo-300 hover:text-indigo-500 transition-colors min-h-[200px]"
            >
              <Plus className="h-8 w-8" />
              <span className="text-sm font-medium">Add book</span>
            </button>

            {sorted.map((book) => (
              <Link key={book.id} href={getBookAction(book)}>
                <Card className="hover:shadow-md transition-shadow cursor-pointer overflow-hidden h-full">
                  {/* Cover gradient */}
                  <div className="h-32 bg-gradient-to-br from-indigo-400 to-purple-600 flex items-center justify-center">
                    <BookOpen className="h-10 w-10 text-white/80" />
                  </div>

                  <div className="p-4">
                    <div className="flex items-start justify-between gap-2 mb-2">
                      <div className="flex-1 min-w-0">
                        <h3 className="font-semibold text-slate-900 truncate text-sm">
                          {book.title}
                        </h3>
                        {book.author && (
                          <p className="text-xs text-slate-500 truncate">{book.author}</p>
                        )}
                      </div>
                      <Badge
                        variant={STATUS_BADGE[book.status]?.color ?? "secondary"}
                        className="shrink-0 text-[10px]"
                      >
                        {STATUS_BADGE[book.status]?.label ?? book.status}
                      </Badge>
                    </div>

                    {book.status === "ready" && (
                      <div className="flex items-center justify-between mt-3">
                        <ProgressRing pct={book.progressPct ?? 0} size={44} stroke={4} />
                        <div className="text-right">
                          {book.dueToday > 0 && (
                            <p className="text-xs font-medium text-orange-600">
                              {book.dueToday} due
                            </p>
                          )}
                          {book.bookStreak > 0 && (
                            <p className="text-xs text-slate-500 flex items-center gap-1 justify-end">
                              <Flame className="h-3 w-3 text-orange-400" />
                              {book.bookStreak}d
                            </p>
                          )}
                        </div>
                      </div>
                    )}

                    {(book.status === "parsing" || book.status === "kg_built") && (
                      <div className="flex items-center gap-2 mt-3 text-xs text-slate-500">
                        <Loader2 className="h-3 w-3 animate-spin" />
                        Building knowledge graph...
                      </div>
                    )}

                    {book.status === "kg_verified" && (
                      <div className="flex items-center gap-1 mt-3 text-xs text-amber-600">
                        <AlertTriangle className="h-3 w-3" />
                        Needs your review
                      </div>
                    )}

                    <div className="flex items-center justify-end mt-2">
                      <ChevronRight className="h-4 w-4 text-slate-300" />
                    </div>
                  </div>
                </Card>
              </Link>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
