import { Bell, Check, ExternalLink } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { recruitmentRequest } from "@/features/recruitment/api";
import { RECRUITMENT_API, EmptyLine, queryError } from "@/features/recruitment/ui";
import { dateLabel } from "@/features/recruitment/model";

type NotificationItem = {
  id: number;
  title: string;
  body: string;
  action_url?: string;
  read_at?: string | null;
  created_at: string;
};

type NotificationPage = { items: NotificationItem[]; total: number };

export function useRecruitmentUnreadCount() {
  const query = useQuery({
    queryKey: ["recruitment", "notifications", "unread-count"],
    queryFn: () => recruitmentRequest<{ unread_count: number }>(`${RECRUITMENT_API}/notifications/unread-count`),
    refetchInterval: 30_000,
  });
  return Number(query.data?.unread_count || 0);
}

export function RecruitmentNotificationsPanel({ basePath }: { basePath: string }) {
  const queryClient = useQueryClient();
  const notifications = useQuery({
    queryKey: ["recruitment", "notifications", "dashboard"],
    queryFn: () => recruitmentRequest<NotificationPage>(`${RECRUITMENT_API}/notifications?per_page=8`),
    refetchInterval: 30_000,
  });
  const markRead = useMutation({
    mutationFn: (id: number) => recruitmentRequest(`${RECRUITMENT_API}/notifications/${id}/read`, { method: "POST" }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["recruitment", "notifications"] }),
  });

  return (
    <section className="overflow-hidden rounded-2xl border border-border bg-card shadow-card" aria-labelledby="recruitment-notifications-title">
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <div className="flex items-center gap-2">
          <Bell className="h-4 w-4 text-primary" />
          <h2 id="recruitment-notifications-title" className="text-sm font-bold">Assigned demo lessons</h2>
        </div>
        <a href={`${basePath}/recruitment/schedule`} className="inline-flex min-h-11 items-center gap-1.5 rounded-lg px-2 text-xs font-semibold text-primary hover:bg-primary/5">Open schedule<ExternalLink className="h-3.5 w-3.5" /></a>
      </div>
      {notifications.isLoading ? <div className="p-4 text-sm text-muted-foreground">Loading assignments…</div> : null}
      {notifications.error ? <div role="alert" className="p-4 text-sm text-destructive">{queryError(notifications.error)}</div> : null}
      {notifications.data ? <div className="divide-y divide-border">
        {notifications.data.items.map((item) => (
          <div key={item.id} className={`flex items-start gap-3 px-4 py-3 ${item.read_at ? "bg-card" : "bg-primary/5"}`}>
            <a href={item.action_url || "#"} onClick={() => { if (!item.read_at) markRead.mutate(item.id); }} className="min-w-0 flex-1 rounded-md focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40">
              <p className="text-sm font-semibold text-foreground">{item.title}</p>
              <p className="mt-0.5 text-xs leading-5 text-muted-foreground">{item.body}</p>
              <p className="mt-1 text-[11px] text-muted-foreground">{dateLabel(item.created_at)}</p>
            </a>
            {!item.read_at ? <button type="button" onClick={() => markRead.mutate(item.id)} className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg text-muted-foreground hover:bg-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40" aria-label={`Mark ${item.title} as read`} title="Mark as read"><Check className="h-4 w-4" /></button> : null}
          </div>
        ))}
        {!notifications.data.items.length ? <div className="p-4"><EmptyLine>No assigned demo notifications.</EmptyLine></div> : null}
      </div> : null}
    </section>
  );
}
