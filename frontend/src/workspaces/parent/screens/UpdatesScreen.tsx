import { useQuery } from "@tanstack/react-query";
import { Bell, Pin } from "lucide-react";
import { getParent } from "@/workspaces/parent/api";
import {
  EmptyState,
  ErrorState,
  formatDate,
  LoadingState,
  ParentPageHeader,
} from "@/workspaces/parent/components";
import type { ParentLanguage, UpdatesPayload } from "@/workspaces/parent/model";

export function UpdatesScreen({ language }: { language: ParentLanguage }) {
  const isRu = language === "ru";
  const query = useQuery({
    queryKey: ["parent", "updates"],
    queryFn: ({ signal }) => getParent<UpdatesPayload>("/updates", signal),
  });

  if (query.isLoading) {
    return <LoadingState label={isRu ? "Загрузка новостей" : "Yangiliklar yuklanmoqda"} />;
  }
  if (query.isError) {
    return (
      <ErrorState
        message={query.error instanceof Error ? query.error.message : "Could not load updates."}
        retry={() => void query.refetch()}
        label={isRu ? "Повторить" : "Qayta urinish"}
      />
    );
  }
  const updates = query.data?.items || [];
  return (
    <>
      <ParentPageHeader
        title={isRu ? "Новости школы" : "Maktab yangiliklari"}
        description={isRu
          ? "Опубликованные объявления для родителей."
          : "Ota-onalar uchun e’lon qilingan xabarlar."}
      />
      {updates.length ? (
        <div className="space-y-3">
          {updates.map((item) => (
            <article key={item.announcementId} className="rounded-xl border border-border bg-surface p-4 shadow-card">
              <div className="flex items-start gap-3">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
                  {item.isPinned ? <Pin className="h-4 w-4" /> : <Bell className="h-4 w-4" />}
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <h2 className="font-black text-foreground">{item.title}</h2>
                    {item.priority === "urgent" ? (
                      <span className="rounded-full bg-destructive/10 px-2 py-1 text-[0.6875rem] font-bold text-destructive">
                        {isRu ? "Срочно" : "Shoshilinch"}
                      </span>
                    ) : null}
                  </div>
                  <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-muted-foreground">{item.body}</p>
                  <p className="mt-3 text-xs font-semibold text-muted-foreground">{formatDate(item.publishedAt)}</p>
                </div>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <EmptyState
          title={isRu ? "Объявлений пока нет" : "Hozircha e’lonlar yo‘q"}
          description={isRu
            ? "Новые сообщения школы появятся здесь."
            : "Maktabning yangi xabarlari shu yerda ko‘rinadi."}
        />
      )}
    </>
  );
}
