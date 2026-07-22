import { BellRing, Check, ExternalLink, Loader2, Play, Volume2, X } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

import { jsonBody, recruitmentRequest } from "@/features/recruitment/api";
import { RECRUITMENT_API, buttonClass, queryError, secondaryButtonClass } from "@/features/recruitment/ui";
import { uiLayers } from "@/shared/ui/layers";

export type BrowserReminderAlert = {
  id: number;
  candidate_id: number;
  appointment_id: number;
  title: string;
  body: string;
  action_url?: string;
  deliver_at?: string;
  is_test?: boolean;
};

type BrowserReminderPreference = {
  account_id: number;
  enabled: boolean;
  version: number;
  updated_at?: string;
};

type BrowserReminderPreferenceMutation = {
  message: string;
  preference: BrowserReminderPreference;
};

type BrowserReminderAlerts = { items: BrowserReminderAlert[] };

export const browserReminderRoles = new Set([
  "hr_manager",
  "academic_director",
  "head_of_department",
]);

export const browserReminderPreferenceKey = [
  "recruitment",
  "notifications",
  "browser-preference",
] as const;

const reminderTestEvent = "msi:recruitment-reminder-test";
let reminderAudioContext: AudioContext | null = null;

function browserPermission(): NotificationPermission | "unsupported" {
  return typeof window !== "undefined" && "Notification" in window
    ? Notification.permission
    : "unsupported";
}

async function audioContext() {
  if (typeof window === "undefined") return null;
  const AudioContextClass = window.AudioContext;
  if (!AudioContextClass) return null;
  reminderAudioContext ||= new AudioContextClass();
  if (reminderAudioContext.state === "suspended") {
    await reminderAudioContext.resume();
  }
  return reminderAudioContext;
}

export async function unlockReminderAudio() {
  await audioContext();
}

export async function playReminderChime() {
  const context = await audioContext();
  if (!context) return;
  const start = context.currentTime;
  const gain = context.createGain();
  gain.gain.setValueAtTime(0.0001, start);
  gain.gain.exponentialRampToValueAtTime(0.055, start + 0.025);
  gain.gain.exponentialRampToValueAtTime(0.0001, start + 0.52);
  gain.connect(context.destination);

  [
    { frequency: 659.25, offset: 0, duration: 0.2 },
    { frequency: 880, offset: 0.22, duration: 0.28 },
  ].forEach(({ frequency, offset, duration }) => {
    const oscillator = context.createOscillator();
    oscillator.type = "sine";
    oscillator.frequency.setValueAtTime(frequency, start + offset);
    oscillator.connect(gain);
    oscillator.start(start + offset);
    oscillator.stop(start + offset + duration);
  });
}

function showDesktopNotification(alert: BrowserReminderAlert) {
  if (browserPermission() !== "granted") return;
  const notification = new Notification(alert.title, {
    body: alert.body,
    icon: "/static/favicon.ico",
    tag: alert.is_test
      ? "recruitment-reminder-test"
      : `recruitment-reminder-${alert.id}`,
  });
  notification.onclick = () => {
    window.focus();
    if (alert.action_url) window.location.assign(alert.action_url);
    notification.close();
  };
}

function dispatchReminderTest(alert: BrowserReminderAlert) {
  window.dispatchEvent(
    new CustomEvent<BrowserReminderAlert>(reminderTestEvent, { detail: alert }),
  );
}

function ReminderToast({
  alert,
  onDismiss,
  onOpen,
}: {
  alert: BrowserReminderAlert;
  onDismiss: () => void;
  onOpen: () => void;
}) {
  return (
    <article className="relative overflow-hidden rounded-xl border border-border bg-card shadow-card-hover">
      <span aria-hidden="true" className="absolute inset-y-0 left-0 w-1 bg-primary" />
      <div className="flex items-start gap-3 p-3 pl-4">
        <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
          <BellRing className="h-4 w-4" />
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-bold text-foreground">{alert.title}</p>
          <p className="mt-1 break-words text-xs leading-5 text-muted-foreground">{alert.body}</p>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            {alert.action_url ? (
              <button type="button" onClick={onOpen} className="inline-flex min-h-11 items-center gap-1.5 rounded-lg bg-primary px-3 text-xs font-semibold text-primary-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40">
                Open candidate <ExternalLink className="h-3.5 w-3.5" />
              </button>
            ) : null}
            <button type="button" onClick={onDismiss} className="inline-flex min-h-11 items-center rounded-lg px-3 text-xs font-semibold text-muted-foreground hover:bg-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30">
              Dismiss
            </button>
          </div>
        </div>
        <button type="button" onClick={onDismiss} className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg text-muted-foreground hover:bg-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30" aria-label={`Dismiss ${alert.title}`}>
          <X className="h-4 w-4" />
        </button>
      </div>
    </article>
  );
}

export function BrowserRecruitmentReminders({ role }: { role?: string }) {
  const normalizedRole = String(role || "").trim().toLowerCase().replace(/-/g, "_");
  const eligible = browserReminderRoles.has(normalizedRole);
  const queryClient = useQueryClient();
  const [visibleAlerts, setVisibleAlerts] = useState<BrowserReminderAlert[]>([]);
  const seenIds = useRef(new Set<number>());
  const preference = useQuery({
    queryKey: browserReminderPreferenceKey,
    queryFn: () => recruitmentRequest<BrowserReminderPreference>(`${RECRUITMENT_API}/notifications/browser-preference`),
    enabled: eligible,
    refetchInterval: 60_000,
  });
  const canPoll = eligible && Boolean(preference.data?.enabled) && browserPermission() === "granted";
  const alerts = useQuery({
    queryKey: ["recruitment", "notifications", "browser-alerts"],
    queryFn: () => recruitmentRequest<BrowserReminderAlerts>(`${RECRUITMENT_API}/notifications/browser-alerts?limit=10`),
    enabled: canPoll,
    refetchInterval: canPoll ? 15_000 : false,
    refetchIntervalInBackground: true,
    refetchOnWindowFocus: true,
  });

  const present = useCallback((items: BrowserReminderAlert[]) => {
    const fresh = items.filter((item) => item.is_test || !seenIds.current.has(item.id));
    if (!fresh.length) return;
    fresh.forEach((item) => {
      if (!item.is_test) seenIds.current.add(item.id);
      showDesktopNotification(item);
    });
    void playReminderChime().catch(() => undefined);
    setVisibleAlerts((current) => {
      const next = [...fresh, ...current.filter((item) => !fresh.some((freshItem) => freshItem.id === item.id))];
      return next.slice(0, 4);
    });
  }, []);

  useEffect(() => {
    if (alerts.data?.items.length) present(alerts.data.items);
  }, [alerts.data, present]);

  useEffect(() => {
    if (!eligible) return undefined;
    const handleTest = (event: Event) => {
      const alert = (event as CustomEvent<BrowserReminderAlert>).detail;
      if (alert) present([alert]);
    };
    window.addEventListener(reminderTestEvent, handleTest);
    return () => window.removeEventListener(reminderTestEvent, handleTest);
  }, [eligible, present]);

  useEffect(() => {
    if (!eligible) return undefined;
    const unlock = () => {
      window.removeEventListener("pointerdown", unlock);
      window.removeEventListener("keydown", unlock);
      void unlockReminderAudio().catch(() => undefined);
    };
    window.addEventListener("pointerdown", unlock, { once: true });
    window.addEventListener("keydown", unlock, { once: true });
    return () => {
      window.removeEventListener("pointerdown", unlock);
      window.removeEventListener("keydown", unlock);
    };
  }, [eligible]);

  useEffect(() => {
    if (!canPoll) return undefined;
    const refetch = () => void alerts.refetch();
    const handleVisibility = () => {
      if (document.visibilityState === "visible") refetch();
    };
    window.addEventListener("focus", refetch);
    document.addEventListener("visibilitychange", handleVisibility);
    return () => {
      window.removeEventListener("focus", refetch);
      document.removeEventListener("visibilitychange", handleVisibility);
    };
  }, [canPoll, alerts.refetch]);

  const markRead = async (alert: BrowserReminderAlert) => {
    setVisibleAlerts((current) => current.filter((item) => item !== alert));
    if (!alert.is_test && alert.id > 0) {
      await recruitmentRequest(`${RECRUITMENT_API}/notifications/${alert.id}/read`, { method: "POST" }).catch(() => undefined);
      void queryClient.invalidateQueries({ queryKey: ["recruitment", "notifications"] });
    }
  };

  if (!eligible || !visibleAlerts.length) return null;
  return createPortal(
    <div className={`fixed inset-x-3 ${uiLayers.toast} bottom-[calc(var(--app-bottom-inset)+5.5rem)] mx-auto flex max-w-md flex-col gap-2 lg:bottom-auto lg:left-auto lg:right-4 lg:top-[4.5rem] lg:mx-0 lg:w-96`} role="region" aria-label="Recruitment appointment reminders" aria-live="assertive">
      {visibleAlerts.map((alert, index) => (
        <ReminderToast
          key={`${alert.is_test ? "test" : alert.id}-${index}`}
          alert={alert}
          onDismiss={() => void markRead(alert)}
          onOpen={() => {
            void markRead(alert).finally(() => {
              if (alert.action_url) window.location.assign(alert.action_url);
            });
          }}
        />
      ))}
    </div>,
    document.body,
  );
}

export function BrowserReminderPreferencesCard() {
  const queryClient = useQueryClient();
  const [permission, setPermission] = useState(browserPermission());
  const [message, setMessage] = useState("");
  const preference = useQuery({
    queryKey: browserReminderPreferenceKey,
    queryFn: () => recruitmentRequest<BrowserReminderPreference>(`${RECRUITMENT_API}/notifications/browser-preference`),
  });
  const mutation = useMutation({
    mutationFn: ({ enabled, expectedVersion }: { enabled: boolean; expectedVersion: number }) =>
      recruitmentRequest<BrowserReminderPreferenceMutation>(`${RECRUITMENT_API}/notifications/browser-preference`, {
        method: "PATCH",
        body: jsonBody({ enabled, expected_version: expectedVersion }),
      }),
    onSuccess: (result) => {
      queryClient.setQueryData(browserReminderPreferenceKey, result.preference);
      setMessage(result.message);
      void queryClient.invalidateQueries({ queryKey: ["recruitment", "notifications"] });
    },
    onError: (error) => setMessage(queryError(error)),
  });
  const test = useMutation({
    mutationFn: () => recruitmentRequest<BrowserReminderAlert>(`${RECRUITMENT_API}/notifications/browser-test`, { method: "POST" }),
    onSuccess: (alert) => {
      dispatchReminderTest(alert);
      setMessage("Test reminder sent on this device.");
    },
    onError: (error) => setMessage(queryError(error)),
  });
  const enabled = Boolean(preference.data?.enabled);
  const status = permission === "unsupported"
    ? "Unsupported"
    : permission === "denied"
      ? "Blocked"
      : enabled && permission === "granted"
        ? "Enabled"
        : "Disabled";
  const statusClass = status === "Enabled"
    ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-500/15 dark:text-emerald-200"
    : status === "Blocked" || status === "Unsupported"
      ? "bg-rose-100 text-rose-800 dark:bg-rose-500/15 dark:text-rose-200"
      : "bg-muted text-muted-foreground";

  const enable = async () => {
    setMessage("");
    if (permission === "unsupported") {
      setMessage("This browser does not support desktop notifications.");
      return;
    }
    await unlockReminderAudio();
    const nextPermission = permission === "granted"
      ? "granted"
      : await Notification.requestPermission();
    setPermission(nextPermission);
    if (nextPermission !== "granted") {
      setMessage("Desktop notifications are blocked. Allow them in the browser site settings, then try again.");
      return;
    }
    if (!enabled) {
      mutation.mutate({ enabled: true, expectedVersion: Number(preference.data?.version || 0) });
    } else {
      setMessage("Browser reminders are enabled on this device.");
    }
  };

  return (
    <section className="rounded-xl border border-border bg-card p-3" aria-labelledby="browser-reminders-title">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex min-w-0 items-start gap-2">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary"><BellRing className="h-5 w-5" /></span>
          <div className="min-w-0">
            <h2 id="browser-reminders-title" className="text-sm font-semibold">Browser appointment reminders</h2>
            <p className="mt-1 max-w-2xl text-xs leading-5 text-muted-foreground">Receive a top-right alert and a gentle two-tone chime before assigned interviews and demo lessons. At least one MSI portal tab must remain open.</p>
          </div>
        </div>
        <span className={`rounded-full px-2.5 py-1 text-[0.6875rem] font-bold ${statusClass}`}>{status}</span>
      </div>
      {preference.isLoading ? <p className="mt-3 text-xs text-muted-foreground">Loading reminder settings…</p> : null}
      {preference.error ? <p role="alert" className="mt-3 text-xs text-destructive">{queryError(preference.error)}</p> : null}
      <div className="mt-4 flex flex-wrap gap-2">
        {status !== "Enabled" ? (
          <button type="button" className={buttonClass} disabled={preference.isLoading || mutation.isPending} onClick={() => void enable()}>
            {mutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <BellRing className="h-4 w-4" />}Enable reminders
          </button>
        ) : (
          <button type="button" className={buttonClass} disabled={test.isPending} onClick={() => test.mutate()}>
            {test.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}Send test reminder
          </button>
        )}
        {enabled ? <button type="button" className={secondaryButtonClass} disabled={mutation.isPending} onClick={() => mutation.mutate({ enabled: false, expectedVersion: Number(preference.data?.version || 0) })}>Disable</button> : null}
      </div>
      {message ? <p className="mt-3 flex items-start gap-1.5 text-xs leading-5 text-muted-foreground"><Check className="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-600" />{message}</p> : null}
      <p className="mt-3 flex items-center gap-1.5 text-[0.6875rem] text-muted-foreground"><Volume2 className="h-3.5 w-3.5" />Sound: one restrained two-tone chime per reminder batch.</p>
    </section>
  );
}
