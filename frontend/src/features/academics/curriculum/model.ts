import { asString, asNumber } from "@/shared/lib/workspace";

type ProgramItem = Record<string, unknown>;

export function filterProgramItems(
  items: ProgramItem[],
  programId: number,
  queryValue: string,
  itemType: "all" | "lesson" | "exam",
) {
  const query = queryValue.trim().toLowerCase();
  return items
    .filter((item) => asNumber(item.program_id) === programId)
    .filter((item) => {
      if (itemType !== "all" && asString(item.item_type) !== itemType) return false;
      if (!query) return true;
      return [
        item.lesson_number,
        item.title,
        item.item_type,
        item.term_label,
        item.week_label,
        item.specification_points,
        item.book_pages,
      ]
        .map(asString)
        .join(" ")
        .toLowerCase()
        .includes(query);
    });
}
