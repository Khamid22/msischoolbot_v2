import { ExternalLink, Link2, Loader2, RefreshCw, Unlink } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { jsonBody, recruitmentRequest } from "@/features/recruitment/api";
import { dateLabel } from "@/features/recruitment/model";
import { buttonClass, queryError, secondaryButtonClass } from "@/features/recruitment/ui";

type TelegramConnection = {
  connected: boolean;
  username: string;
  linked_at?: string | null;
  open_telegram_url: string;
  bot_configured: boolean;
};

function telegramInitData() {
  const telegramWindow = window as typeof window & { Telegram?: { WebApp?: { initData?: string } } };
  return String(telegramWindow.Telegram?.WebApp?.initData || "").trim();
}

export function TelegramConnectionCard() {
  const queryClient = useQueryClient();
  const connection = useQuery({
    queryKey: ["identity", "telegram-link"],
    queryFn: () => recruitmentRequest<TelegramConnection>("/api/v1/auth/telegram-link"),
  });
  const mutation = useMutation({
    mutationFn: (action: "link" | "unlink") => action === "link"
      ? recruitmentRequest<TelegramConnection>("/api/v1/auth/telegram-link", { method: "POST", body: jsonBody({ init_data: telegramInitData() }) })
      : recruitmentRequest<TelegramConnection>("/api/v1/auth/telegram-link", { method: "DELETE" }),
    onSuccess: (data) => {
      queryClient.setQueryData(["identity", "telegram-link"], data);
      void queryClient.invalidateQueries({ queryKey: ["recruitment", "notifications"] });
    },
  });
  const data = connection.data;
  const initData = typeof window !== "undefined" ? telegramInitData() : "";

  return (
    <section className="rounded-xl border border-border bg-card p-3" aria-labelledby="telegram-connection-title">
      <div className="flex items-start gap-2">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-sky-500/10 text-sky-600"><Link2 className="h-5 w-5" /></span>
        <div className="min-w-0 flex-1">
          <h2 id="telegram-connection-title" className="text-sm font-semibold">Telegram notifications</h2>
          <p className="mt-1 text-xs leading-5 text-muted-foreground">Link your own Telegram account to receive assigned Demo Lesson changes and reminders.</p>
        </div>
      </div>
      {connection.isLoading ? <p className="mt-4 text-sm text-muted-foreground">Checking connection…</p> : null}
      {connection.error ? <p role="alert" className="mt-4 text-sm text-destructive">{queryError(connection.error)}</p> : null}
      {data ? <div className="mt-4 rounded-lg bg-muted/55 p-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Status</p>
            <p className="mt-1 text-sm font-semibold">{data.connected ? `Connected${data.username ? ` as @${data.username}` : ""}` : "Not connected"}</p>
            {data.linked_at ? <p className="mt-0.5 text-xs text-muted-foreground">Linked {dateLabel(data.linked_at)}</p> : null}
          </div>
          <div className="flex flex-wrap gap-2">
            {initData ? <button type="button" className={buttonClass} disabled={mutation.isPending} onClick={() => mutation.mutate("link")}>{mutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : data.connected ? <RefreshCw className="h-4 w-4" /> : <Link2 className="h-4 w-4" />}{data.connected ? "Refresh" : "Link Telegram"}</button> : data.open_telegram_url ? <a href={data.open_telegram_url} target="_blank" rel="noreferrer noopener" className={buttonClass}>Open Telegram Mini App<ExternalLink className="h-4 w-4" /></a> : null}
            {data.connected ? <button type="button" className={secondaryButtonClass} disabled={mutation.isPending} onClick={() => mutation.mutate("unlink")}><Unlink className="h-4 w-4" />Unlink</button> : null}
          </div>
        </div>
        {!data.bot_configured ? <p className="mt-3 text-xs text-amber-700 dark:text-amber-300">Telegram linking is unavailable until the bot username and token are configured.</p> : null}
        {mutation.error ? <p role="alert" className="mt-3 text-xs text-destructive">{queryError(mutation.error)}</p> : null}
      </div> : null}
    </section>
  );
}
