import { ReactNode } from "react";
import { ChevronLeft } from "lucide-react";
//
// Telegram Bot API 7.2+ injects these CSS variables after WebApp.ready():
//
// Base CSS provides env() fallbacks for non-Telegram browser mode.
const appTopInset = "var(--app-top-inset)";
const appLeftInset = "var(--app-left-inset)";
const appRightInset = "var(--app-right-inset)";
const appBottomInset = "var(--app-bottom-inset)";

const headerPadLeft = appLeftInset;
const headerPadRight = appRightInset;
const headerPadTop = appTopInset;

// Total top padding for <main>: device notch + Telegram UI + topbar height.
// Using 5.5rem gives a ~0.5rem buffer above both mobile (4.75rem) and desktop (5rem) topbar heights.
const mainPadTop = `calc(${headerPadTop} + 5.5rem)`;

// Total bottom padding for <main>: device home indicator + Telegram main button.
const mainPadBottom = `calc(${appBottomInset} + 1rem)`;
const mainPadLeft = appLeftInset;
const mainPadRight = appRightInset;

interface TopbarProps {
  backUrl?: string;
  title: string;
  subtitle?: string;
  subtitleContent?: ReactNode;
  titleIcon?: ReactNode;
  leadingContent?: ReactNode;
  rightContent?: ReactNode;
}

export function Topbar({
  backUrl,
  title,
  subtitle,
  subtitleContent,
  titleIcon,
  leadingContent,
  rightContent,
}: TopbarProps) {
  return (
    <header
      className="fixed inset-x-0 top-0 z-40 border-b border-foreground/5 bg-surface shadow-card"
      style={{ paddingTop: headerPadTop, paddingLeft: headerPadLeft, paddingRight: headerPadRight }}
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
          {leadingContent}
          {title || subtitle || subtitleContent ? (
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
          ) : null}
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
    // overflow: hidden clips the shell so body-level scroll stays disabled.
    <div className="flex app-height flex-col overflow-hidden bg-background">
      {topbar}

      {/*
       * flex-1 + min-h-0: required pair for a scrollable flex child.
       * Without min-h-0 the item can't shrink, overflow-y-auto never fires,
       * and content is silently clipped by the shell's overflow:hidden.
       *
       * overflow-x-hidden keeps the page itself from drifting sideways; dense
       * tables and carousels use their own inner scroll containers.
       */}
      <main
        className="min-h-0 flex-1 overflow-y-auto overflow-x-hidden px-3 sm:px-4 md:px-6 lg:px-8"
        style={{
          paddingTop: mainPadTop,
          paddingBottom: mainPadBottom,
          paddingLeft: `calc(${mainPadLeft} + 0.75rem)`,
          paddingRight: `calc(${mainPadRight} + 0.75rem)`,
          overscrollBehaviorY: "contain",
          WebkitOverflowScrolling: "touch",
        }}
      >
        <div className="mx-auto w-full max-w-4xl">
          {children}
        </div>
      </main>
    </div>
  );
}
