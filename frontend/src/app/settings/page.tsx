"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useSession, signOut } from "next-auth/react";
import { Save, LogOut, Trash2, Loader2, ArrowLeft, User } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Sidebar } from "@/components/Sidebar";
import { getToken } from "@/lib/auth";
import { getMe, updateMe } from "@/lib/api";
import type { UserUpdateDTO } from "@/types/dto";

export default function SettingsPage() {
  const { data: session, status } = useSession();
  const router = useRouter();

  const [form, setForm] = useState<UserUpdateDTO & { name: string }>({
    name: "",
    dailyNewNodeCap: 5,
    dailyReminderTime: "20:00",
    sessionLengthPref: 20,
    notifyReminders: true,
    notifyDueReviews: true,
    notifyProcessing: true,
  });
  const [saving, setSaving]   = useState(false);
  const [saved, setSaved]     = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState("");

  useEffect(() => {
    if (status === "unauthenticated") { router.push("/"); return; }
    if (status !== "authenticated") return;

    const token = getToken(session);
    getMe(token)
      .then(({ user }) => {
        setForm((f) => ({
          ...f,
          name:                user.name,
          dailyNewNodeCap:     user.dailyNewNodeCap,
          dailyReminderTime:   user.dailyReminderTime ?? "20:00",
          sessionLengthPref:   user.sessionLengthPref,
          notifyReminders:     user.notifyReminders,
          notifyDueReviews:    user.notifyDueReviews,
          notifyProcessing:    user.notifyProcessing,
        }));
        setLoading(false);
      })
      .catch(() => {
        setError("Could not load settings.");
        setLoading(false);
      });
  }, [status, session, router]);

  const save = async () => {
    setSaving(true);
    setError("");
    try {
      await updateMe(getToken(session), form);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch {
      setError("Failed to save. Please try again.");
    } finally {
      setSaving(false);
    }
  };

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

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 ml-16 lg:ml-56 p-6 max-w-2xl">
        <div className="flex items-center gap-3 mb-6">
          <button onClick={() => router.back()} className="text-slate-400 hover:text-slate-600">
            <ArrowLeft className="h-5 w-5" />
          </button>
          <h1 className="text-2xl font-bold text-slate-900">Profile &amp; Settings</h1>
        </div>

        {/* Profile */}
        <Card className="mb-5">
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <User className="h-4 w-4" /> Profile
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Name</label>
              <input
                id="input-name"
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Email</label>
              <input
                value={session?.user?.email ?? ""}
                disabled
                className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm bg-slate-50 text-slate-500"
              />
            </div>
          </CardContent>
        </Card>

        {/* Learning settings */}
        <Card className="mb-5">
          <CardHeader>
            <CardTitle className="text-base">Learning settings</CardTitle>
          </CardHeader>
          <CardContent className="space-y-5">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Daily new node cap: <strong>{form.dailyNewNodeCap}</strong>
              </label>
              <input
                id="range-node-cap"
                type="range"
                min={1}
                max={20}
                value={form.dailyNewNodeCap}
                onChange={(e) =>
                  setForm((f) => ({ ...f, dailyNewNodeCap: Number(e.target.value) }))
                }
                className="w-full accent-indigo-600"
              />
              <div className="flex justify-between text-xs text-slate-400 mt-1">
                <span>1 (easy)</span>
                <span>20 (intensive)</span>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Daily reminder time
              </label>
              <input
                id="input-reminder-time"
                type="time"
                value={form.dailyReminderTime ?? "20:00"}
                onChange={(e) =>
                  setForm((f) => ({ ...f, dailyReminderTime: e.target.value }))
                }
                className="px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Session length preference: <strong>{form.sessionLengthPref} min</strong>
              </label>
              <input
                id="range-session-length"
                type="range"
                min={5}
                max={60}
                step={5}
                value={form.sessionLengthPref}
                onChange={(e) =>
                  setForm((f) => ({ ...f, sessionLengthPref: Number(e.target.value) }))
                }
                className="w-full accent-indigo-600"
              />
            </div>
          </CardContent>
        </Card>

        {/* Notifications */}
        <Card className="mb-5">
          <CardHeader>
            <CardTitle className="text-base">Notifications</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {(
              [
                { key: "notifyReminders" as const,   label: "Daily study reminders" },
                { key: "notifyDueReviews" as const,  label: "Due review alerts" },
                { key: "notifyProcessing" as const,  label: "Book processing complete" },
              ]
            ).map(({ key, label }) => (
              <label key={key} className="flex items-center justify-between cursor-pointer">
                <span className="text-sm text-slate-700">{label}</span>
                <div
                  id={`toggle-${key}`}
                  onClick={() =>
                    setForm((f) => ({ ...f, [key]: !f[key] }))
                  }
                  className={`relative h-5 w-9 rounded-full transition-colors cursor-pointer ${
                    form[key] ? "bg-indigo-600" : "bg-slate-200"
                  }`}
                >
                  <div
                    className={`absolute top-0.5 h-4 w-4 rounded-full bg-white shadow transition-transform ${
                      form[key] ? "translate-x-4" : "translate-x-0.5"
                    }`}
                  />
                </div>
              </label>
            ))}
          </CardContent>
        </Card>

        {error && (
          <p className="text-sm text-red-600 mb-4">{error}</p>
        )}

        <div className="flex flex-col gap-3">
          <Button id="btn-save-settings" onClick={save} disabled={saving}>
            {saving ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Save className="h-4 w-4" />
            )}
            {saved ? "Saved!" : "Save settings"}
          </Button>

          <Button
            id="btn-sign-out"
            variant="outline"
            onClick={() => signOut({ callbackUrl: "/" })}
          >
            <LogOut className="h-4 w-4" /> Sign out
          </Button>

          <Button
            id="btn-delete-account"
            variant="destructive"
            className="bg-red-50 text-red-600 hover:bg-red-100 border border-red-200"
            onClick={() => {
              // TODO: implement account deletion flow
              if (confirm("Delete your account? This cannot be undone.")) {
                // call DELETE /users/me when backend implements it
              }
            }}
          >
            <Trash2 className="h-4 w-4" /> Delete account
          </Button>
        </div>
      </main>
    </div>
  );
}
