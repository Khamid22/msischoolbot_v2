import { Bell, CreditCard, LifeBuoy, TrendingUp, UsersRound } from "lucide-react";
import { EmptyState, formatMoney, ParentPageHeader } from "@/workspaces/parent/components";
import type { ParentLanguage, ParentOverview } from "@/workspaces/parent/model";

export function HomeScreen({
  overview,
  language,
}: {
  overview: ParentOverview;
  language: ParentLanguage;
}) {
  const isRu = language === "ru";
  const summary = [
    {
      label: isRu ? "Дети" : "Bolalar",
      value: String(overview.children.length),
      detail: isRu ? "подключено" : "ulangan",
      icon: UsersRound,
    },
    {
      label: isRu ? "Посещаемость" : "Davomat",
      value: overview.averageAttendanceRate === null ? "—" : `${overview.averageAttendanceRate}%`,
      detail: isRu ? "средний показатель" : "o‘rtacha ko‘rsatkich",
      icon: TrendingUp,
    },
    {
      label: isRu ? "К оплате" : "To‘lov",
      value: formatMoney(
        overview.paymentSummary.debtTotal + overview.paymentSummary.dueTotal,
        overview.paymentSummary.currency,
      ),
      detail: isRu ? "долг и текущие платежи" : "qarz va joriy to‘lovlar",
      icon: CreditCard,
    },
    {
      label: isRu ? "Открытые обращения" : "Ochiq murojaatlar",
      value: String(overview.openTicketCount),
      detail: isRu ? "ожидают решения" : "yechim kutilmoqda",
      icon: LifeBuoy,
    },
  ];

  return (
    <>
      <ParentPageHeader
        title={isRu ? "Главная" : "Asosiy"}
        description={isRu
          ? "Самое важное о детях, оплате и сообщениях школы."
          : "Bolalar, to‘lovlar va maktab xabarlari bo‘yicha eng muhim ma’lumotlar."}
      />

      <div className="grid grid-cols-2 gap-2 lg:grid-cols-4">
        {summary.map((item) => {
          const Icon = item.icon;
          return (
            <section key={item.label} className="rounded-xl border border-border bg-surface p-3 shadow-card">
              <div className="flex items-center gap-2 text-xs font-bold text-muted-foreground">
                <Icon className="h-4 w-4" />
                <span>{item.label}</span>
              </div>
              <p className="mt-3 break-words text-lg font-black tabular-nums text-foreground sm:text-xl">
                {item.value}
              </p>
              <p className="mt-1 text-xs text-muted-foreground">{item.detail}</p>
            </section>
          );
        })}
      </div>

      {overview.children.length ? (
        <section>
          <div className="mb-3 flex items-center justify-between gap-3">
            <h2 className="text-base font-black text-foreground">{isRu ? "Дети" : "Bolalar"}</h2>
            <a href="/parent/children" className="text-sm font-bold text-primary hover:underline">
              {isRu ? "Открыть" : "Ochish"}
            </a>
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            {overview.children.map((child) => (
              <a
                key={child.studentRowId}
                href={`/parent/children/${child.studentRowId}`}
                className="rounded-xl border border-border bg-surface p-4 shadow-card transition-colors hover:border-primary/35 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/35"
              >
                <p className="font-black text-foreground">{child.fullName}</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  {child.studentCode} · {child.schoolName}
                </p>
                <div className="mt-3 flex flex-wrap gap-2 text-xs font-bold">
                  <span className="rounded-md bg-muted px-2 py-1 text-foreground">
                    {isRu ? "Посещаемость" : "Davomat"}{" "}
                    {child.academicIndicators[0]?.attendanceRate ?? "—"}%
                  </span>
                  <span className="rounded-md bg-muted px-2 py-1 text-foreground">
                    {isRu ? "Прогресс" : "O‘sish"}{" "}
                    {child.academicIndicators[0]?.completionRate ?? "—"}%
                  </span>
                </div>
              </a>
            ))}
          </div>
        </section>
      ) : (
        <EmptyState
          title={isRu ? "Дети ещё не подключены" : "Bolalar hali ulanmagan"}
          description={isRu
            ? "Откройте новую ссылку-приглашение от школы внутри Telegram."
            : "Maktab yuborgan yangi taklif havolasini Telegram ichida oching."}
        />
      )}

      <section>
        <div className="mb-3 flex items-center justify-between gap-3">
          <h2 className="flex items-center gap-2 text-base font-black text-foreground">
            <Bell className="h-4 w-4 text-primary" />
            {isRu ? "Последние новости" : "So‘nggi yangiliklar"}
          </h2>
          <a href="/parent/updates" className="text-sm font-bold text-primary hover:underline">
            {isRu ? "Все" : "Barchasi"}
          </a>
        </div>
        {overview.latestUpdates.length ? (
          <div className="space-y-2">
            {overview.latestUpdates.map((announcement) => (
              <article key={announcement.announcementId} className="rounded-xl border border-border bg-surface p-4">
                <h3 className="font-bold text-foreground">{announcement.title}</h3>
                <p className="mt-1 line-clamp-2 text-sm leading-6 text-muted-foreground">{announcement.body}</p>
              </article>
            ))}
          </div>
        ) : (
          <p className="rounded-xl border border-dashed border-border bg-surface p-5 text-sm text-muted-foreground">
            {isRu ? "Новых объявлений пока нет." : "Hozircha yangi e’lonlar yo‘q."}
          </p>
        )}
      </section>
    </>
  );
}
