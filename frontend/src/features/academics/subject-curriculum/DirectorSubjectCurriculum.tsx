import { useEffect, useMemo, useState, type FormEvent } from "react";
import { BookMarked, Plus } from "lucide-react";
import { csrfHeaders, jsonCsrfHeaders } from "@/shared/lib/api";
import { ConfirmDialog } from "@/shared/ui/ConfirmDialog";
import { CurriculumTable } from "./CurriculumTable";
import { FundamentalsItemEditor } from "./FundamentalsItemEditor";
import {
  curriculumApi,
  defaultVariant,
  moveItemIds,
  type CurriculumDetail,
  type CurriculumItem,
  type CurriculumItemWrite,
  type CurriculumVariantKey,
  type SubjectCurriculumCatalog,
} from "./model";

const API_ROOT = "/api/v1/academic-director/academic/subject-curricula";

const EMPTY_ITEM: CurriculumItemWrite = {
  lessonNumber: "",
  itemType: "lesson",
  title: "",
  termLabel: "",
  weekLabel: "",
  specificationPoints: "",
  bookPages: "",
  lessonCount: "",
  durationHours: "",
  contentBlocks: [],
};

function normalizeSubject(value: string) {
  return value.trim().toLowerCase().replace(/[^a-z0-9]+/g, "");
}

function itemDraft(item: CurriculumItem | null): CurriculumItemWrite {
  if (!item) return { ...EMPTY_ITEM };
  return {
    lessonNumber: item.lessonNumber,
    itemType: item.itemType,
    title: item.title,
    termLabel: item.termLabel,
    weekLabel: item.weekLabel,
    specificationPoints: item.specificationPoints,
    bookPages: item.bookPages,
    lessonCount: item.lessonCount,
    durationHours: item.durationHours,
    contentBlocks: item.contentBlocks,
    expectedVersion: item.version,
  };
}

export function DirectorSubjectCurriculum({
  subjectKey,
  csrfToken,
}: {
  subjectKey: string;
  csrfToken: string;
}) {
  const [catalog, setCatalog] = useState<SubjectCurriculumCatalog>({ subjects: [] });
  const [variantKey, setVariantKey] = useState<CurriculumVariantKey>("primary");
  const [detail, setDetail] = useState<CurriculumDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [editorItem, setEditorItem] = useState<CurriculumItem | null | undefined>();
  const [draft, setDraft] = useState<CurriculumItemWrite>(EMPTY_ITEM);
  const [busy, setBusy] = useState(false);
  const [busyItemId, setBusyItemId] = useState(0);
  const [archiveItem, setArchiveItem] = useState<CurriculumItem | null>(null);
  const [archiveReason, setArchiveReason] = useState("");

  useEffect(() => {
    setLoading(true);
    setError("");
    void curriculumApi<SubjectCurriculumCatalog>(API_ROOT)
      .then(setCatalog)
      .catch((reason: unknown) => {
        setError(reason instanceof Error ? reason.message : "Unable to load subject curricula.");
      })
      .finally(() => setLoading(false));
  }, []);

  const subject = useMemo(() => {
    const key = normalizeSubject(subjectKey);
    return (
      catalog.subjects.find((entry) => normalizeSubject(entry.subjectKey) === key) ||
      catalog.subjects.find((entry) => normalizeSubject(entry.subjectName) === key) ||
      null
    );
  }, [catalog.subjects, subjectKey]);
  const variants = subject?.variants || [];
  const selectedVariant =
    variants.find((variant) => variant.curriculumKey === variantKey) || variants[0] || null;

  useEffect(() => {
    if (!subject) return;
    setVariantKey(defaultVariant(subject));
  }, [subject?.subjectId]);

  useEffect(() => {
    if (!subject || !selectedVariant) {
      setDetail(null);
      return;
    }
    setLoading(true);
    setError("");
    void curriculumApi<CurriculumDetail>(
      `${API_ROOT}/${subject.subjectId}/${selectedVariant.curriculumKey}`,
    )
      .then(setDetail)
      .catch((reason: unknown) => {
        setError(reason instanceof Error ? reason.message : "Unable to load this curriculum.");
      })
      .finally(() => setLoading(false));
  }, [selectedVariant?.curriculumKey, subject?.subjectId]);

  function openEditor(item: CurriculumItem | null) {
    setEditorItem(item);
    setDraft(itemDraft(item));
    setError("");
  }

  async function saveItem(event: FormEvent) {
    event.preventDefault();
    if (!subject) return;
    setBusy(true);
    setError("");
    const isEditing = Boolean(editorItem);
    const url = isEditing
      ? `${API_ROOT}/${subject.subjectId}/fundamentals/items/${editorItem!.itemId}`
      : `${API_ROOT}/${subject.subjectId}/fundamentals/items`;
    try {
      const nextDetail = await curriculumApi<CurriculumDetail>(url, {
        method: isEditing ? "PATCH" : "POST",
        headers: jsonCsrfHeaders(csrfToken),
        body: JSON.stringify(draft),
      });
      setDetail(nextDetail);
      setEditorItem(undefined);
      await refreshCatalog();
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Unable to save this lesson.");
    } finally {
      setBusy(false);
    }
  }

  async function refreshCatalog() {
    const nextCatalog = await curriculumApi<SubjectCurriculumCatalog>(API_ROOT);
    setCatalog(nextCatalog);
  }

  async function moveItem(item: CurriculumItem, direction: -1 | 1) {
    if (!subject || !detail) return;
    setBusyItemId(item.itemId);
    setError("");
    try {
      const nextDetail = await curriculumApi<CurriculumDetail>(
        `${API_ROOT}/${subject.subjectId}/fundamentals/reorder`,
        {
          method: "POST",
          headers: jsonCsrfHeaders(csrfToken),
          body: JSON.stringify({
            itemIds: moveItemIds(detail.items, item.itemId, direction),
            expectedCurriculumVersion: detail.variant.version,
          }),
        },
      );
      setDetail(nextDetail);
      await refreshCatalog();
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Unable to reorder this curriculum.");
    } finally {
      setBusyItemId(0);
    }
  }

  async function setArchived(item: CurriculumItem, archive: boolean) {
    if (!subject) return;
    setBusyItemId(item.itemId);
    setError("");
    try {
      const action = archive ? "archive" : "restore";
      const body = archive
        ? { expectedVersion: item.version, reason: archiveReason.trim() }
        : { expectedVersion: item.version };
      const nextDetail = await curriculumApi<CurriculumDetail>(
        `${API_ROOT}/${subject.subjectId}/fundamentals/items/${item.itemId}/${action}`,
        {
          method: "POST",
          headers: jsonCsrfHeaders(csrfToken),
          body: JSON.stringify(body),
        },
      );
      setDetail(nextDetail);
      setArchiveItem(null);
      setArchiveReason("");
      await refreshCatalog();
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Unable to update this lesson.");
    } finally {
      setBusyItemId(0);
    }
  }

  async function addExternalAsset(
    assetKind: "link" | "video",
    assetTitle: string,
    assetUrl: string,
  ) {
    if (!subject || !editorItem) return false;
    setBusy(true);
    setError("");
    try {
      const nextDetail = await curriculumApi<CurriculumDetail>(
        `${API_ROOT}/${subject.subjectId}/fundamentals/items/${editorItem.itemId}/assets`,
        {
          method: "POST",
          headers: jsonCsrfHeaders(csrfToken),
          body: JSON.stringify({
            assetKind,
            title: assetTitle.trim(),
            externalUrl: assetUrl.trim(),
          }),
        },
      );
      setDetail(nextDetail);
      const refreshed = nextDetail.items.find((item) => item.itemId === editorItem.itemId) || null;
      setEditorItem(refreshed);
      return true;
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Unable to add this material.");
    } finally {
      setBusy(false);
    }
    return false;
  }

  async function uploadFile(fileTitle: string, file: File) {
    if (!subject || !editorItem) return false;
    const formData = new FormData();
    formData.set("title", fileTitle.trim() || file.name);
    formData.set("document", file);
    setBusy(true);
    setError("");
    try {
      const nextDetail = await curriculumApi<CurriculumDetail>(
        `${API_ROOT}/${subject.subjectId}/fundamentals/items/${editorItem.itemId}/files`,
        {
          method: "POST",
          headers: csrfHeaders(csrfToken),
          body: formData,
        },
      );
      setDetail(nextDetail);
      const refreshed = nextDetail.items.find((item) => item.itemId === editorItem.itemId) || null;
      setEditorItem(refreshed);
      return true;
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Unable to upload this file.");
    } finally {
      setBusy(false);
    }
    return false;
  }

  async function archiveAsset(assetId: number, expectedVersion: number) {
    if (!subject || !editorItem) return;
    setBusy(true);
    setError("");
    try {
      const nextDetail = await curriculumApi<CurriculumDetail>(
        `${API_ROOT}/${subject.subjectId}/fundamentals/assets/${assetId}/archive`,
        {
          method: "POST",
          headers: jsonCsrfHeaders(csrfToken),
          body: JSON.stringify({ expectedVersion }),
        },
      );
      setDetail(nextDetail);
      const refreshed = nextDetail.items.find((item) => item.itemId === editorItem.itemId) || null;
      setEditorItem(refreshed);
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Unable to archive this material.");
    } finally {
      setBusy(false);
    }
  }

  if (!loading && !subject) {
    return (
      <section className="rounded-xl border border-dashed border-border bg-surface px-5 py-12 text-center">
        <BookMarked className="mx-auto h-8 w-8 text-muted-foreground/60" />
        <p className="mt-3 text-sm font-black">This subject has no curriculum record yet.</p>
      </section>
    );
  }

  const isEditable = selectedVariant?.curriculumKey === "fundamentals";
  return (
    <section className="space-y-3">
      {variants.length > 1 ? (
        <nav
          className="inline-grid w-full grid-cols-2 rounded-xl border border-border bg-surface p-1 sm:w-auto"
          aria-label="Curriculum variants"
        >
          {variants.map((variant) => (
            <button
              key={variant.curriculumKey}
              type="button"
              aria-current={variant.curriculumKey === selectedVariant?.curriculumKey ? "page" : undefined}
              onClick={() => setVariantKey(variant.curriculumKey)}
              className={`min-h-10 rounded-lg px-5 text-sm font-black ${
                variant.curriculumKey === selectedVariant?.curriculumKey
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              }`}
            >
              {variant.title}
            </button>
          ))}
        </nav>
      ) : null}

      <section className="rounded-xl border border-border bg-surface p-3 shadow-card sm:p-4">
        <header className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-base font-black">
              {selectedVariant?.title || "Primary Curriculum"}
            </h2>
            <p className="mt-0.5 text-xs font-semibold text-muted-foreground">
              {isEditable
                ? "Changes become visible to assigned ESL teachers after you save."
                : "The canonical Primary Curriculum is read-only."}
            </p>
          </div>
          {isEditable ? (
            <button
              type="button"
              onClick={() => openEditor(null)}
              className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg bg-primary px-4 text-sm font-black text-primary-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
            >
              <Plus className="h-4 w-4" />Add lesson
            </button>
          ) : null}
        </header>
        <CurriculumTable
          detail={detail}
          loading={loading}
          error={error}
          editable={isEditable}
          useGuidanceLayout={isEditable}
          busyItemId={busyItemId}
          onEdit={openEditor}
          onMove={moveItem}
          onArchive={(item) => {
            setArchiveItem(item);
            setArchiveReason("");
          }}
          onRestore={(item) => void setArchived(item, false)}
        />
      </section>

      {editorItem !== undefined ? (
        <FundamentalsItemEditor
          item={editorItem}
          draft={draft}
          busy={busy}
          error={error}
          onDraftChange={setDraft}
          onClose={() => setEditorItem(undefined)}
          onSave={saveItem}
          onAddExternalAsset={addExternalAsset}
          onUploadFile={uploadFile}
          onArchiveAsset={archiveAsset}
        />
      ) : null}

      <ConfirmDialog
        open={Boolean(archiveItem)}
        title="Archive this lesson?"
        message={
          <label>
            It will disappear from the active Fundamentals table, but its history and files remain.
            <span className="mt-3 block text-xs font-black text-foreground">Reason</span>
            <textarea
              value={archiveReason}
              onChange={(event) => setArchiveReason(event.target.value)}
              rows={2}
              className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground outline-none focus:border-primary"
            />
          </label>
        }
        confirmLabel="Archive"
        danger
        busy={busyItemId > 0}
        onCancel={() => {
          setArchiveItem(null);
          setArchiveReason("");
        }}
        onConfirm={() => {
          if (archiveItem && archiveReason.trim().length >= 3) {
            void setArchived(archiveItem, true);
          }
        }}
      />
    </section>
  );
}
