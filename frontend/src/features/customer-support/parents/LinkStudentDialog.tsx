import { Check, ChevronRight, Link2, Loader2, Search } from "lucide-react";
import { useEffect, useState } from "react";
import { getSupport, type SearchPayload, type SupportRecordSummary } from "@/features/customer-support/api";
import { inputClass, Label, primaryButton, secondaryButton } from "@/features/customer-support/shared/ui";
import { Modal, ModalBody, ModalFooter } from "@/shared/ui/Modal";

export function LinkStudentDialog({
  parentId,
  saving,
  onClose,
  onLink,
}: {
  parentId: number;
  saving: boolean;
  onClose: () => void;
  onLink: (studentId: number) => void;
}) {
  const [query, setQuery] = useState("");
  const [items, setItems] = useState<SupportRecordSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<number | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      setLoading(true);
      setError("");
      const params = new URLSearchParams({
        type: "student",
        status: "active",
        limit: "50",
        excludeParentId: String(parentId),
      });
      if (query.trim()) params.set("q", query.trim());
      const loadCandidates = async () => {
        const candidates = new Map<number, SupportRecordSummary>();
        const seenCursors = new Set<string>();
        let cursor = "";

        do {
          if (cursor) params.set("cursor", cursor);
          else params.delete("cursor");
          const payload = await getSupport<SearchPayload>(`/records?${params}`, controller.signal);
          payload.items.forEach((item) => candidates.set(item.id, item));
          cursor = payload.nextCursor || "";
          if (cursor && seenCursors.has(cursor)) {
            throw new Error("Student search returned a repeated cursor.");
          }
          if (cursor) seenCursors.add(cursor);
        } while (cursor);

        return [...candidates.values()];
      };
      loadCandidates()
        .then((candidates) => {
          setItems(candidates);
          setSelected((current) => (
            current && candidates.some((item) => item.id === current) ? current : null
          ));
        })
        .catch((requestError) => {
          if ((requestError as Error).name !== "AbortError") {
            setItems([]);
            setError(requestError instanceof Error ? requestError.message : "Could not search students.");
          }
        })
        .finally(() => {
          if (!controller.signal.aborted) setLoading(false);
        });
    }, 275);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [parentId, query]);

  return (
    <Modal
      title="Link student"
      subtitle="Search is limited to active students inside your allowed school scope."
      onClose={onClose}
      size="md"
      mobileMode="fullscreen"
    >
      <ModalBody>
        <Label htmlFor="link-student-search">Search student</Label>
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
          <input
            id="link-student-search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            className={`${inputClass} pl-10`}
            placeholder="Name, student code, or phone"
            autoFocus
          />
        </div>
        {error ? <p className="mt-3 text-sm font-bold text-destructive" role="alert">{error}</p> : null}
        <div className="miniapp-scroll mt-4 max-h-[50dvh] overflow-y-auto rounded-lg border border-border">
          {loading ? (
            <div className="flex min-h-28 items-center justify-center" role="status">
              <Loader2 className="h-5 w-5 animate-spin text-primary motion-reduce:animate-none" />
              <span className="sr-only">Searching students</span>
            </div>
          ) : items.length ? items.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => setSelected(item.id)}
              aria-pressed={selected === item.id}
              className={`flex min-h-16 w-full items-center justify-between gap-3 border-b border-border px-3 py-2 text-left last:border-b-0 focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary/40 ${selected === item.id ? "bg-primary/10" : "bg-background hover:bg-muted"}`}
            >
              <span className="min-w-0">
                <span className="block break-words text-sm font-black">{item.display_name}</span>
                <span className="mt-1 block break-words text-xs font-semibold text-muted-foreground">{item.secondary} · {item.school_name}</span>
              </span>
              {selected === item.id
                ? <Check className="h-4 w-4 shrink-0 text-primary" aria-hidden="true" />
                : <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />}
            </button>
          )) : (
            <p className="px-4 py-8 text-center text-sm font-semibold text-muted-foreground">No available students match this search.</p>
          )}
        </div>
      </ModalBody>
      <ModalFooter>
        <div className="flex justify-end gap-2">
          <button type="button" onClick={onClose} className={secondaryButton}>Cancel</button>
          <button type="button" disabled={!selected || saving} onClick={() => selected && onLink(selected)} className={primaryButton}>
            {saving ? <Loader2 className="h-4 w-4 animate-spin motion-reduce:animate-none" /> : <Link2 className="h-4 w-4" />}
            Link student
          </button>
        </div>
      </ModalFooter>
    </Modal>
  );
}
