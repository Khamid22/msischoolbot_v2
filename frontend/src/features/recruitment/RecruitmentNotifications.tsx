import { Bell, Check, ExternalLink } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { MouseEvent } from "react";

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

const notificationDashboardKey = ["recruitment", "notifications", "dashboard"] as const;
const notificationUnreadKey = ["recruitment", "notifications", "unread-count"] as const;

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
    queryKey: notificationDashboardKey,
    queryFn: () => recruitmentRequest<NotificationPage>(`${RECRUITMENT_API}/notifications?per_page=8&unread_only=true`),
    refetchInterval: 30_000,
  });
  const markRead = useMutation({
    mutationFn: (id: number) => recruitmentRequest(`${RECRUITMENT_API}/notifications/${id}/read`, { method: "POST" }),
    onMutate: async (id) => {
      await queryClient.cancelQueries({ queryKey: ["recruitment", "notifications"] });
      const previousPage = queryClient.getQueryData<NotificationPage>(notificationDashboardKey);
      const previousUnread = queryClient.getQueryData<{ unread_count: number }>(notificationUnreadKey);
      queryClient.setQueryData<NotificationPage>(notificationDashboardKey, (current) => current ? {
        ...current,
        items: current.items.filter((item) => item.id !== id),
        total: Math.max(0, current.total - 1),
      } : current);
      queryClient.setQueryData<{ unread_count: number }>(notificationUnreadKey, (current) => current ? {
        unread_count: Math.max(0, current.unread_count - 1),
      } : current);
      return { previousPage, previousUnread };
    },
    onError: (_error, _id, context) => {
      if (context?.previousPage) queryClient.setQueryData(notificationDashboardKey, context.previousPage);
      if (context?.previousUnread) queryClient.setQueryData(notificationUnreadKey, context.previousUnread);
    },
    onSettled: () => void queryClient.invalidateQueries({ queryKey: ["recruitment", "notifications"] }),
  });

  const openNotification = (event: MouseEvent<HTMLAnchorElement>, item: NotificationItem) => {
    event.preventDefault();
    const href = item.action_url;
    if (!href || href === "#") {
      if (!item.read_at) markRead.mutate(item.id);
      return;
    }
    if (item.read_at) {
      window.location.assign(href);
      return;
    }
    markRead.mutate(item.id, { onSuccess: () => window.location.assign(href) });
  };

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
      {markRead.error ? <div role="alert" className="border-b border-destructive/20 bg-destructive/10 px-4 py-2 text-xs text-destructive">{queryError(markRead.error)} The notification was restored.</div> : null}
      {notifications.data ? <div className="divide-y divide-border">
        {notifications.data.items.map((item) => (
          <div key={item.id} className={`flex items-start gap-3 px-4 py-3 ${item.read_at ? "bg-card" : "bg-primary/5"}`}>
            <a href={item.action_url || "#"} onClick={(event) => openNotification(event, item)} className="min-w-0 flex-1 rounded-md focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40">
              <p className="text-sm font-semibold text-foreground">{item.title}</p>
              <p className="mt-0.5 text-xs leading-5 text-muted-foreground">{item.body}</p>
              <p className="mt-1 text-[11px] text-muted-foreground">{dateLabel(item.created_at)}</p>
            </a>
            {!item.read_at ? <button type="button" disabled={markRead.isPending} onClick={() => markRead.mutate(item.id)} className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg text-muted-foreground hover:bg-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 disabled:cursor-wait disabled:opacity-50" aria-label={`Mark ${item.title} as read`} title="Mark as read"><Check className="h-4 w-4" /></button> : null}
          </div>
        ))}
        {!notifications.data.items.length ? <div className="p-4"><EmptyLine>No assigned demo notifications.</EmptyLine></div> : null}
      </div> : null}
    </section>
  );
}
