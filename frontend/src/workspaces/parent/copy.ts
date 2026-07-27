import type { ParentLanguage } from "@/workspaces/parent/model";

export const parentCopy = {
  ru: {
    role: "Родитель",
    section: "Семья",
    home: "Главная",
    updates: "Новости",
    children: "Дети",
    payments: "Оплата",
    support: "Помощь",
    loading: "Загрузка данных…",
    retry: "Повторить",
    logout: "Выйти",
    language: "Язык",
    allChildren: "Все дети",
    noChildren: "Дети ещё не подключены",
  },
  uz: {
    role: "Ota-ona",
    section: "Oila",
    home: "Asosiy",
    updates: "Yangilik",
    children: "Bolalar",
    payments: "To‘lov",
    support: "Yordam",
    loading: "Ma’lumot yuklanmoqda…",
    retry: "Qayta urinish",
    logout: "Chiqish",
    language: "Til",
    allChildren: "Barcha bolalar",
    noChildren: "Bolalar hali ulanmagan",
  },
} as const satisfies Record<ParentLanguage, Record<string, string>>;
