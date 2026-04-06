import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Format a reliability score (0-100) to a color class.
 */
export function scoreColor(score: number | null | undefined): string {
  if (score == null) return "text-[var(--color-text-muted)]";
  if (score >= 75) return "text-[var(--color-green)]";
  if (score >= 50) return "text-[var(--color-yellow)]";
  if (score >= 25) return "text-[var(--color-orange)]";
  return "text-[var(--color-red)]";
}

export function scoreBg(score: number | null | undefined): string {
  if (score == null) return "bg-[var(--color-text-muted)]";
  if (score >= 75) return "bg-[var(--color-green)]";
  if (score >= 50) return "bg-[var(--color-yellow)]";
  if (score >= 25) return "bg-[var(--color-orange)]";
  return "bg-[var(--color-red)]";
}

export function biasColor(label: string | null | undefined): string {
  switch (label) {
    case "left":
      return "text-[var(--color-bias-left)]";
    case "center":
      return "text-[var(--color-bias-center)]";
    case "right":
      return "text-[var(--color-bias-right)]";
    default:
      return "text-[var(--color-bias-unclassified)]";
  }
}

export function biasBg(label: string | null | undefined): string {
  switch (label) {
    case "left":
      return "bg-[var(--color-bias-left)]";
    case "center":
      return "bg-[var(--color-bias-center)]";
    case "right":
      return "bg-[var(--color-bias-right)]";
    default:
      return "bg-[var(--color-bias-unclassified)]";
  }
}

/**
 * Format relative time (e.g. "3 hours ago").
 */
export function timeAgo(date: string | Date | null | undefined): string {
  if (!date) return "";
  const now = new Date();
  const past = new Date(date);
  const diffMs = now.getTime() - past.getTime();
  const diffMins = Math.floor(diffMs / 60000);

  if (diffMins < 1) return "just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  if (diffDays < 7) return `${diffDays}d ago`;
  return past.toLocaleDateString("en-IN", { day: "numeric", month: "short" });
}
