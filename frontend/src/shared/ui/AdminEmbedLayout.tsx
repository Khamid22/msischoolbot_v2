import { ReactNode } from "react";
import { ChevronLeft } from "lucide-react";

interface AdminEmbedLayoutProps {
  title: string;
  subtitle?: string;
  backUrl?: string;
  badge?: string;
  headerAction?: ReactNode;
  children: ReactNode;
}

export function AdminEmbedLayout({
  title,
  subtitle,
  backUrl,
  badge,
  headerAction,
  children,
}: AdminEmbedLayoutProps) {
  const normalizedBackUrl = withEmbedMode(backUrl);

  return (
    <div className="flex app-height min-h-0 flex-col overflow-y-auto bg-background px-3 py-3 sm:px-4">
      <div className="w-full space-y-3 pb-[calc(var(--app-bottom-inset)+1rem)]">
        <section className="flex flex-col gap-3 rounded-xl border border-foreground/10 bg-surface p-4 shadow-card sm:flex-row sm:items-center sm:justify-between">
          <div className="flex min-w-0 items-center gap-3">
            {normalizedBackUrl ? (
              <a
                href={normalizedBackUrl}
                className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg transition-colors hover:bg-muted"
                aria-label="Back"
              >
                <ChevronLeft className="h-5 w-5" />
              </a>
            ) : null}
            <div className="min-w-0">
              <h2 className="font-display text-base font-bold leading-tight">{title}</h2>
              {subtitle ? <p className="mt-1 truncate text-xs text-muted-foreground">{subtitle}</p> : null}
            </div>
          </div>
          {headerAction ? (
            headerAction
          ) : badge ? (
            <span className="w-fit rounded-md bg-muted px-2.5 py-1 text-[11px] font-bold">{badge}</span>
          ) : null}
        </section>
        {children}
      </div>
    </div>
  );
}

export function isAdminEmbedMode(embedMode?: string) {
  return String(embedMode || "").trim().toLowerCase() === "admin";
}

export function withEmbedMode(url?: string) {
  const trimmedUrl = String(url || "").trim();
  if (!trimmedUrl) {
    return "";
  }
  if (/[?&]embed=/.test(trimmedUrl)) {
    return trimmedUrl;
  }
  const separator = trimmedUrl.includes("?") ? "&" : "?";
  return `${trimmedUrl}${separator}embed=admin`;
}
