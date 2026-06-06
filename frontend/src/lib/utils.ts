import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export const NODE_STATE_COLORS: Record<string, { bg: string; border: string; text: string; dot: string }> = {
  locked: {
    bg: "bg-slate-100",
    border: "border-slate-200",
    text: "text-slate-400",
    dot: "bg-slate-300",
  },
  available: {
    bg: "bg-blue-50",
    border: "border-blue-300",
    text: "text-blue-700",
    dot: "bg-blue-400",
  },
  in_progress: {
    bg: "bg-amber-50",
    border: "border-amber-300",
    text: "text-amber-700",
    dot: "bg-amber-400",
  },
  mastered: {
    bg: "bg-emerald-50",
    border: "border-emerald-300",
    text: "text-emerald-700",
    dot: "bg-emerald-500",
  },
  due: {
    bg: "bg-orange-50",
    border: "border-orange-300",
    text: "text-orange-700",
    dot: "bg-orange-500",
  },
};

export const NODE_STATE_LABELS: Record<string, string> = {
  locked: "Locked",
  available: "Available",
  in_progress: "In Progress",
  mastered: "Mastered",
  due: "Due for Review",
};

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "Never";
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export function timeAgo(iso: string | null | undefined): string {
  if (!iso) return "Never";
  const diff = Date.now() - new Date(iso).getTime();
  const days = Math.floor(diff / 86400000);
  if (days === 0) return "Today";
  if (days === 1) return "Yesterday";
  if (days < 7) return `${days} days ago`;
  if (days < 30) return `${Math.floor(days / 7)} weeks ago`;
  return `${Math.floor(days / 30)} months ago`;
}

export function daysUntil(iso: string | null | undefined): string {
  if (!iso) return "Not scheduled";
  const diff = new Date(iso).getTime() - Date.now();
  const days = Math.ceil(diff / 86400000);
  if (days < 0) return `${Math.abs(days)}d overdue`;
  if (days === 0) return "Due today";
  if (days === 1) return "Due tomorrow";
  return `Due in ${days} days`;
}

export function estimateMinutes(nodeCount: number): number {
  return Math.max(1, Math.round(nodeCount * 4));
}
