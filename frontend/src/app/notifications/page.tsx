"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import {
  Bell, BookOpen, Clock, Flame, Trophy, CheckCheck, ArrowLeft, Loader2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Sidebar } from "@/components/Sidebar";
import { getToken } from "@/lib/auth";
import { listNotifications, markNotificationRead, markAllNotificationsRead } from "@/lib/api";
import type { NotificationDTO } from "@/types/dto";

const TYPE_ICONS: Record<string, React.ReactNode> = {
  book_ready:       <BookOpen className="h-4 w-4 text-emerald-500" />,
  book_needs_review: <BookOpen className="h-4 w-4 text-amber-500" />,
  reviews_due:      <Clock className="h-4 w-4 text-orange-500" />,
  streak_reminder:  <Flame className="h-4 w-4 text-orange-400" />,
  milestone:        <Trophy className="h-4 w-4 text-indigo-500" />,
};

export default function NotificationsPage() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const [notifications, setNotifications] = useState<NotificationDTO[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (status === "unauthenticated") { router.push("/"); return; }
    if (status !== "authenticated") return;

    const token = getToken(session);
    listNotifications(token)
      .then(({ notifications: n }) => {
        setNotifications(n ?? []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [status, session, router]);

  const markAllRead = async () => {
    const token = getToken(session);
    await markAllNotificationsRead(token).catch(() => {});
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
  };

  const markRead = async (id: string) => {
    const token = getToken(session);
    await markNotificationRead(token, id).catch(() => {});
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, read: true } : n))
    );
  };

  const unreadCount = notifications.filter((n) => !n.read).length;

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
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <button onClick={() => router.back()} className="text-slate-400 hover:text-slate-600">
              <ArrowLeft className="h-5 w-5" />
            </button>
            <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
              Notifications
              {unreadCount > 0 && (
                <Badge variant="destructive" className="text-xs">
                  {unreadCount}
                </Badge>
              )}
            </h1>
          </div>
          {unreadCount > 0 && (
            <Button id="btn-mark-all-read" variant="ghost" size="sm" onClick={markAllRead}>
              <CheckCheck className="h-4 w-4" /> Mark all read
            </Button>
          )}
        </div>

        {notifications.length === 0 ? (
          <div className="text-center py-16">
            <div className="h-16 w-16 bg-slate-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <Bell className="h-8 w-8 text-slate-400" />
            </div>
            <p className="text-slate-500">No notifications yet.</p>
          </div>
        ) : (
          <div className="space-y-2">
            {notifications.map((n) => (
              <Card
                key={n.id}
                className={`cursor-pointer transition-all hover:shadow-sm ${
                  !n.read ? "border-indigo-200 bg-indigo-50/50" : ""
                }`}
                onClick={() => {
                  markRead(n.id);
                  if (n.link) router.push(n.link);
                }}
              >
                <CardContent className="p-4 flex items-start gap-3">
                  <div
                    className={`h-9 w-9 rounded-lg flex items-center justify-center shrink-0 ${
                      !n.read ? "bg-white shadow-sm" : "bg-slate-100"
                    }`}
                  >
                    {TYPE_ICONS[n.type] ?? <Bell className="h-4 w-4 text-slate-400" />}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p
                      className={`text-sm font-medium ${
                        !n.read ? "text-slate-900" : "text-slate-700"
                      }`}
                    >
                      {n.title}
                    </p>
                    <p className="text-xs text-slate-500 mt-0.5">{n.body}</p>
                    <p className="text-xs text-slate-400 mt-1">
                      {new Date(n.createdAt).toLocaleDateString("en", {
                        month: "short",
                        day: "numeric",
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </p>
                  </div>
                  {!n.read && (
                    <div className="h-2 w-2 bg-indigo-500 rounded-full mt-1.5 shrink-0" />
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
