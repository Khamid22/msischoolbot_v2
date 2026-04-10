import { ReactNode } from "react";
import { ChevronLeft } from "lucide-react";

// ─── Safe area helpers ────────────────────────────────────────────────────────
//
// Telegram Bot API 7.2+ injects these CSS variables after WebApp.ready():
//   --tg-safe-area-inset-top/bottom   → device notch / home indicator
//   --tg-content-safe-area-inset-top  → Telegram's own UI (close btn, header)
//   --tg-content-safe-area-inset-bottom → main button / bottom bar height
//
// We fall back to the browser env() safe area when the Telegram SDK is absent
// (e.g. when opening the page in a regular browser for testing).

const safeTop =
  "var(--tg-safe-area-inset-top, env(safe-area-inset-top, 0px))";
const contentSafeTop =
  "var(--tg-content-safe-area-inset-top, 0px)";
const safeBottom =
  "var(--tg-safe-area-inset-bottom, env(safe-area-inset-bottom, 0px))";
const contentSafeBottom =
  "var(--tg-content-safe-area-inset-bottom, 0px)";

// Total top padding for the sticky header (only device safe area, not topbar).
const headerPadTop = safeTop;

// Total top padding for <main>: device notch + Telegram UI + topbar height.
// Using 5.5rem gives a ~0.5rem buffer above both mobile (4.75rem) and desktop (5rem) topbar heights.
const mainPadTop = `calc(${safeTop} + ${contentSafeTop} + 5.5rem)`;

// Total bottom padding for <main>: device home indicator + Telegram main button.
const mainPadBottom = `calc(${safeBottom} + ${contentSafeBottom} + 1.5rem)`;

// ─── Components ───────────────────────────────────────────────────────────────

interface TopbarProps {
  backUrl?: string;
  title: string;
  subtitle?: string;
  subtitleContent?: ReactNode;
  titleIcon?: ReactNode;
  rightContent?: ReactNode;
}

export function Topbar({
  backUrl,
  title,
  subtitle,
  subtitleContent,
  titleIcon,
  rightContent,
}: TopbarProps) {
  return (
    <header
      className="fixed inset-x-0 top-0 z-40 border-b border-foreground/5 bg-surface/95 shadow-card backdrop-blur"
      style={{ paddingTop: headerPadTop }}
    >
      <div className="mx-auto flex min-h-[4.75rem] w-full max-w-4xl items-center justify-between gap-2.5 px-3 py-3 sm:min-h-[5rem] sm:px-4 md:px-6 lg:max-w-5xl">
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
        {rightContent ? (
          <div className="flex shrink-0 items-center gap-2">{rightContent}</div>
        ) : null}
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
    // height: 100dvh locks the shell to the viewport — never grows beyond it.
    // overflow: hidden clips the shell so body-level scroll stays disabled.
    <div className="flex h-[100dvh] flex-col overflow-hidden bg-background">
      {topbar}

      {/*
       * flex-1 + min-h-0: required pair for a scrollable flex child.
       * Without min-h-0 the item can't shrink, overflow-y-auto never fires,
       * and content is silently clipped by the shell's overflow:hidden.
       *
       * No overflow-x set here — the shell's overflow:hidden clips any
       * stray horizontal overflow at the viewport edge. Keeping overflow-x
       * unset (defaults to auto due to CSS spec when overflow-y is set)
       * lets child overflow-x-auto scroll rows work on all browsers.
       */}
      <main
        className="min-h-0 flex-1 overflow-y-auto px-3 sm:px-4 md:px-6 lg:px-8"
        style={{
          paddingTop: mainPadTop,
          paddingBottom: mainPadBottom,
        }}
      >
        <div className="mx-auto w-full max-w-4xl">
          {children}
        </div>
      </main>
    </div>
  );
}
