import { ReactNode } from "react";
import { ChevronLeft } from "lucide-react";

interface TopbarProps {
  backUrl?: string;
  title: string;
  subtitle?: string;
  subtitleContent?: ReactNode;
  titleIcon?: ReactNode;
  rightContent?: ReactNode;
}

export function Topbar({ backUrl, title, subtitle, subtitleContent, titleIcon, rightContent }: TopbarProps) {
  return (
    <header className="tg-safe-top fixed inset-x-0 top-0 z-40 border-b border-foreground/5 bg-surface/95 shadow-card backdrop-blur">
      <div className="mx-auto flex w-full max-w-4xl items-center justify-between gap-2 px-3 py-2.5 sm:px-4 md:px-6 lg:max-w-5xl">
        <div className="flex min-w-0 flex-1 items-center gap-2">
          {backUrl && (
            <a
              href={backUrl}
              className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg transition-colors hover:bg-muted"
              aria-label="Back"
            >
              <ChevronLeft className="h-5 w-5" />
            </a>
          )}
          <div className="min-w-0">
            <h1 className="flex items-center gap-1.5 truncate font-display text-sm font-bold leading-tight sm:text-base md:text-lg">
              {titleIcon}
              {title}
            </h1>
            {subtitleContent ? (
              <div className="mt-0.5 min-w-0">{subtitleContent}</div>
            ) : subtitle ? (
              <p className="mt-0.5 truncate text-xs text-muted-foreground">{subtitle}</p>
            ) : null}
          </div>
        </div>
        {rightContent ? <div className="flex shrink-0 items-center gap-2">{rightContent}</div> : null}
      </div>
    </header>
  );
}

interface TelegramLayoutProps {
  children: ReactNode;
  topbar: ReactNode;
}

export function TelegramLayout({ children, topbar }: TelegramLayoutProps) {
  return (
    <div className="flex min-h-[100dvh] flex-col bg-background">
      {topbar}
      <main className="flex-1 overflow-x-hidden px-3 pb-[calc(1rem+env(safe-area-inset-bottom,0px))] pt-[calc(5rem+var(--tg-safe-offset))] sm:px-4 sm:pt-[calc(5.25rem+var(--tg-safe-offset))] md:px-6 lg:px-8">
        <div className="mx-auto w-full max-w-4xl">
          {children}
        </div>
      </main>
    </div>
  );
}
