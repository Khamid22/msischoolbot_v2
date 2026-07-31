import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { BookMarked, Plus } from "lucide-react";
import { csrfHeaders, jsonCsrfHeaders } from "@/shared/lib/api";
import { ConfirmDialog } from "@/shared/ui/ConfirmDialog";
import { CurriculumTable } from "./CurriculumTable";
import { FundamentalsItemEditor } from "./FundamentalsItemEditor";
import {
  curriculumApi,
  defaultVariant,
  moveItemIds,
  type CurriculumAsset,
  type CurriculumDetail,
  type CurriculumItem,
  type CurriculumLessonDraft,
  type CurriculumVariantKey,
  type SubjectCurriculumCatalog,
} from "./model";

const API_ROOT = "/api/v1/academic-director/academic/subject-curricula";
const DRAFT_AUTOSAVE_DELAY_MS = 1000;

function normalizeSubject(value: string) {
  return value.trim().toLowerCase().replace(/[^a-z0-9]+/g, "");
}

function draftFingerprint(draft: CurriculumLessonDraft) {
  return JSON.stringify({ title: draft.title, guidance: draft.guidance });
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
  const [editorDraft, setEditorDraft] = useState<CurriculumLessonDraft | null>(null);
  const [draftSaving, setDraftSaving] = useState(false);
  const [busy, setBusy] = useState(false);
  const [busyItemId, setBusyItemId] = useState(0);
  const [archiveItem, setArchiveItem] = useState<CurriculumItem | null>(null);
  const [archiveReason, setArchiveReason] = useState("");
  const lastSavedDraft = useRef("");
  const failedDraftSave = useRef("");

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
    if (
      !subject
      || !editorDraft
      || !editorDraft.assets.some((asset) =>
        asset.conversionStatus === "pending" || asset.conversionStatus === "processing"
      )
    ) {
      return undefined;
    }
    const timer = window.setTimeout(() => {
      void curriculumApi<CurriculumLessonDraft>(
        `${API_ROOT}/${subject.subjectId}/fundamentals/drafts/${editorDraft.draftId}`,
      ).then((next) => {
        setEditorDraft((current) =>
          current?.draftId === next.draftId
            ? { ...next, title: current.title, guidance: current.guidance }
            : current
        );
      }).catch(() => undefined);
    }, 3000);
    return () => window.clearTimeout(timer);
  }, [editorDraft, subject]);

  useEffect(() => {
    if (!subject || !editorDraft || busy || draftSaving) return undefined;
    const fingerprint = draftFingerprint(editorDraft);
    if (
      fingerprint === lastSavedDraft.current
      || fingerprint === failedDraftSave.current
    ) {
      return undefined;
    }
    const snapshot = editorDraft;
    const timer = window.setTimeout(() => {
      setDraftSaving(true);
      void curriculumApi<CurriculumLessonDraft>(
        `${API_ROOT}/${subject.subjectId}/fundamentals/drafts/${snapshot.draftId}`,
        {
          method: "PATCH",
          headers: jsonCsrfHeaders(csrfToken),
          body: JSON.stringify({
            title: snapshot.title,
            guidance: snapshot.guidance,
            expectedRevisionVersion: snapshot.revisionVersion,
          }),
        },
      )
        .then((savedDraft) => {
          lastSavedDraft.current = fingerprint;
          failedDraftSave.current = "";
          setEditorDraft((current) =>
            current?.draftId === savedDraft.draftId
              ? {
                  ...savedDraft,
                  title: current.title,
                  guidance: current.guidance,
                }
              : current
          );
        })
        .catch((reason: unknown) => {
          failedDraftSave.current = fingerprint;
          setError(
            reason instanceof Error
              ? reason.message
              : "Unable to save the private draft.",
          );
        })
        .finally(() => setDraftSaving(false));
    }, DRAFT_AUTOSAVE_DELAY_MS);
    return () => window.clearTimeout(timer);
  }, [busy, csrfToken, draftSaving, editorDraft, subject]);

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

  async function openEditor(item: CurriculumItem | null) {
    if (!subject) return;
    setBusy(true);
    setError("");
    try {
      const nextDraft = await curriculumApi<CurriculumLessonDraft>(
        `${API_ROOT}/${subject.subjectId}/fundamentals/drafts`,
        {
          method: "POST",
          headers: jsonCsrfHeaders(csrfToken),
          body: JSON.stringify({ itemId: item?.itemId || null }),
        },
      );
      lastSavedDraft.current = draftFingerprint(nextDraft);
      failedDraftSave.current = "";
      setEditorDraft(nextDraft);
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Unable to open the lesson editor.");
    } finally {
      setBusy(false);
    }
  }

  async function saveItem(event: FormEvent) {
    event.preventDefault();
    if (!subject || !editorDraft) return;
    setBusy(true);
    setError("");
    try {
      const nextDetail = await curriculumApi<CurriculumDetail>(
        `${API_ROOT}/${subject.subjectId}/fundamentals/drafts/${editorDraft.draftId}/publish`,
        {
        method: "POST",
        headers: jsonCsrfHeaders(csrfToken),
        body: JSON.stringify({
          title: editorDraft.title,
          guidance: editorDraft.guidance,
          expectedRevisionVersion: editorDraft.revisionVersion,
        }),
      },
      );
      setDetail(nextDetail);
      lastSavedDraft.current = "";
      failedDraftSave.current = "";
      setEditorDraft(null);
      await refreshCatalog();
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Unable to save this lesson.");
    } finally {
      setBusy(false);
    }
  }

  async function closeEditor() {
    if (!subject || !editorDraft) return;
    const confirmed = window.confirm(
      "Discard this private draft? The published lesson will remain unchanged.",
    );
    if (!confirmed) return;
    setBusy(true);
    setError("");
    try {
      await curriculumApi<{ message: string }>(
        `${API_ROOT}/${subject.subjectId}/fundamentals/drafts/${editorDraft.draftId}/abandon`,
        {
          method: "POST",
          headers: jsonCsrfHeaders(csrfToken),
        },
      );
      lastSavedDraft.current = "";
      failedDraftSave.current = "";
      setEditorDraft(null);
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Unable to discard this draft.");
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
    assetKind: "link" | "embed",
    assetTitle: string,
    assetUrl: string,
  ) {
    if (!subject || !editorDraft) return null;
    setBusy(true);
    setError("");
    try {
      return await curriculumApi<CurriculumLessonDraft>(
        `${API_ROOT}/${subject.subjectId}/fundamentals/drafts/${editorDraft.draftId}/assets`,
        {
          method: "POST",
          headers: jsonCsrfHeaders(csrfToken),
          body: JSON.stringify({
            assetKind: "link",
            renderKind: assetKind,
            title: assetTitle.trim(),
            externalUrl: assetUrl.trim(),
          }),
        },
      );
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Unable to add this material.");
    } finally {
      setBusy(false);
    }
    return null;
  }

  async function uploadFile(
    fileTitle: string,
    file: File,
    onProgress: (percent: number) => void,
  ) {
    if (!subject || !editorDraft) return null;
    const formData = new FormData();
    formData.set("title", fileTitle.trim() || file.name);
    formData.set("document", file);
    setBusy(true);
    setError("");
    try {
      return await new Promise<CurriculumLessonDraft>((resolve, reject) => {
        const request = new XMLHttpRequest();
        request.open(
          "POST",
          `${API_ROOT}/${subject.subjectId}/fundamentals/drafts/${editorDraft.draftId}/files`,
        );
        request.withCredentials = true;
        Object.entries(csrfHeaders(csrfToken)).forEach(([name, value]) => {
          request.setRequestHeader(name, value);
        });
        request.upload.addEventListener("progress", (event) => {
          if (event.lengthComputable) {
            onProgress(Math.min(99, Math.round((event.loaded / event.total) * 100)));
          }
        });
        request.addEventListener("load", () => {
          let payload: {
            status?: string;
            data?: CurriculumLessonDraft;
            detail?: string;
            message?: string;
          } = {};
          try {
            payload = JSON.parse(request.responseText) as typeof payload;
          } catch {
            reject(new Error("The upload response was not readable."));
            return;
          }
          if (
            request.status < 200
            || request.status >= 300
            || payload.status === "error"
            || !payload.data
          ) {
            reject(
              new Error(
                payload.detail || payload.message || "Unable to upload this file.",
              ),
            );
            return;
          }
          onProgress(100);
          resolve(payload.data);
        });
        request.addEventListener("error", () => {
          reject(new Error("The file upload was interrupted. Try again."));
        });
        request.send(formData);
      });
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Unable to upload this file.");
    } finally {
      setBusy(false);
    }
    return null;
  }

  async function detachAsset(asset: CurriculumAsset) {
    if (!subject || !editorDraft) return null;
    setBusy(true);
    setError("");
    try {
      return await curriculumApi<CurriculumLessonDraft>(
        `${API_ROOT}/${subject.subjectId}/fundamentals/drafts/${editorDraft.draftId}/assets/${asset.assetId}/detach`,
        {
          method: "POST",
          headers: jsonCsrfHeaders(csrfToken),
          body: JSON.stringify({ expectedVersion: asset.placementVersion }),
        },
      );
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Unable to archive this material.");
    } finally {
      setBusy(false);
    }
    return null;
  }

  async function retryConversion(assetId: number) {
    if (!subject || !editorDraft) return null;
    setBusy(true);
    setError("");
    try {
      return await curriculumApi<CurriculumLessonDraft>(
        `${API_ROOT}/${subject.subjectId}/fundamentals/drafts/${editorDraft.draftId}/assets/${assetId}/retry`,
        {
          method: "POST",
          headers: jsonCsrfHeaders(csrfToken),
        },
      );
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Unable to retry this presentation.");
    } finally {
      setBusy(false);
    }
    return null;
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
              onClick={() => void openEditor(null)}
              disabled={busy}
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
          onEdit={(item) => void openEditor(item)}
          onMove={moveItem}
          onArchive={(item) => {
            setArchiveItem(item);
            setArchiveReason("");
          }}
          onRestore={(item) => void setArchived(item, false)}
        />
      </section>

      {editorDraft ? (
        <FundamentalsItemEditor
          draft={editorDraft}
          busy={busy || draftSaving}
          savingDraft={draftSaving}
          error={error}
          onDraftChange={setEditorDraft}
          onClose={closeEditor}
          onSave={saveItem}
          onAddExternalAsset={addExternalAsset}
          onUploadFile={uploadFile}
          onDetachAsset={detachAsset}
          onRetryConversion={retryConversion}
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
