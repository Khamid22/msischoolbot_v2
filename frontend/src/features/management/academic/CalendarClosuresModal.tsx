import { useCallback, useEffect, useMemo, useState } from "react";
import { CalendarDays, LockKeyhole, RotateCcw, Unlock, X } from "lucide-react";
import { apiData, apiErrorMessage, apiSucceeded, jsonCsrfHeaders } from "@/shared/lib/api";
import { Modal, ModalBody, ModalFooter } from "@/shared/ui/Modal";
import { asNumber, asString } from "@/features/managementTypes";
import { Select } from "./shared";

export type CalendarClosure = {
  id: number;
  schoolId: number;
  schoolCode?: string;
  schoolName?: string;
  groupId?: number | null;
  groupName?: string;
  scope: "school" | "group";
  title: string;
  startDate: string;
  endDate: string;
  status: string;
};

type ClosurePreview = {
  affectedGroupCount: number;
  affectedLessonCount: number;
  preservedRecordedLessonCount: number;
  conflicts?: string[];
};

type ClosureRoutes = {
  adminAcademicCalendarClosuresApi: (query?: string) => string;
  adminAcademicCalendarClosurePreview: string;
  adminAcademicCalendarClosureCreate: string;
  adminAcademicCalendarClosureUnlock: (closureId: number | string) => string;
};

function formatDate(value: string) {
  const parsed = new Date(`${value}T00:00:00`);
  return Number.isNaN(parsed.getTime())
    ? value
    : new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric" }).format(parsed);
}

function presetDates(year: number, preset: "june" | "july" | "august" | "summer") {
  const month = preset === "june" ? 6 : preset === "july" ? 7 : 8;
  const startMonth = preset === "summer" ? 6 : month;
  const endMonth = preset === "summer" ? 8 : month;
  const lastDay = new Date(Date.UTC(year, endMonth, 0)).getUTCDate();
  return {
    startDate: `${year}-${String(startMonth).padStart(2, "0")}-01`,
    endDate: `${year}-${String(endMonth).padStart(2, "0")}-${String(lastDay).padStart(2, "0")}`,
  };
}

export function CalendarClosuresModal({
  open,
  onClose,
  csrf,
  academicRoutes,
  schools,
  fixedSchoolId = 0,
  groupId = 0,
  groupName = "",
  initialYear,
  onChanged,
}: {
  open: boolean;
  onClose: () => void;
  csrf: string;
  academicRoutes: ClosureRoutes;
  schools: Array<Record<string, unknown>>;
  fixedSchoolId?: number;
  groupId?: number;
  groupName?: string;
  initialYear?: number;
  onChanged?: () => void | Promise<void>;
}) {
  const defaultYear = initialYear || new Date().getFullYear();
  const firstSchoolId = asNumber(schools[0]?.id);
  const [schoolId, setSchoolId] = useState(String(fixedSchoolId || firstSchoolId || ""));
  const [year, setYear] = useState(String(defaultYear));
  const [title, setTitle] = useState("Summer holiday");
  const [startDate, setStartDate] = useState(() => presetDates(defaultYear, "summer").startDate);
  const [endDate, setEndDate] = useState(() => presetDates(defaultYear, "summer").endDate);
  const [items, setItems] = useState<CalendarClosure[]>([]);
  const [preview, setPreview] = useState<ClosurePreview | null>(null);
  const [unlockTarget, setUnlockTarget] = useState<CalendarClosure | null>(null);
  const [rebuildFuture, setRebuildFuture] = useState(false);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const selectedSchoolId = fixedSchoolId || Number(schoolId || 0);
  const dirty = Boolean(preview) || title !== "Summer holiday" || startDate !== presetDates(Number(year), "summer").startDate || endDate !== presetDates(Number(year), "summer").endDate;
  const dateError = startDate && endDate && endDate < startDate
    ? "The last locked date must be on or after the first locked date."
    : "";

  const visibleItems = useMemo(
    () => items.filter((item) => item.startDate.slice(0, 4) === year || item.endDate.slice(0, 4) === year),
    [items, year],
  );

  const loadClosures = useCallback(async (signal?: AbortSignal) => {
    if (!selectedSchoolId) return;
    setLoading(true);
    setError("");
    const query = new URLSearchParams({
      school_id: String(selectedSchoolId),
      date_from: `${year}-01-01`,
      date_to: `${year}-12-31`,
    });
    if (groupId) query.set("group_id", String(groupId));
    try {
      const response = await fetch(academicRoutes.adminAcademicCalendarClosuresApi(query.toString()), {
        signal,
        cache: "no-store",
        credentials: "same-origin",
        headers: { "X-Requested-With": "XMLHttpRequest" },
      });
      const json = await response.json().catch(() => ({}));
      if (!apiSucceeded(response, json)) throw new Error(apiErrorMessage(json, "Unable to load holiday locks."));
      const data = apiData<{ items?: CalendarClosure[] }>(json);
      setItems(Array.isArray(data.items) ? data.items : []);
    } catch (reason) {
      if (reason instanceof DOMException && reason.name === "AbortError") return;
      setError(reason instanceof Error ? reason.message : "Unable to load holiday locks.");
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, [academicRoutes.adminAcademicCalendarClosuresApi, selectedSchoolId, year, groupId]);

  useEffect(() => {
    if (!open) return;
    setSchoolId(String(fixedSchoolId || firstSchoolId || ""));
    setYear(String(defaultYear));
    setTitle("Summer holiday");
    const summer = presetDates(defaultYear, "summer");
    setStartDate(summer.startDate);
    setEndDate(summer.endDate);
    setPreview(null);
    setUnlockTarget(null);
    setError("");
    setNotice("");
  }, [open, fixedSchoolId, firstSchoolId, defaultYear]);

  useEffect(() => {
    if (!open || !selectedSchoolId) return;
    const controller = new AbortController();
    setItems([]);
    void loadClosures(controller.signal);
    return () => controller.abort();
  }, [open, selectedSchoolId, loadClosures]);

  function applyPreset(preset: "june" | "july" | "august" | "summer") {
    const dates = presetDates(Number(year), preset);
    setStartDate(dates.startDate);
    setEndDate(dates.endDate);
    setTitle("Summer holiday");
    setPreview(null);
  }

  function payload() {
    return {
      school_id: selectedSchoolId,
      group_id: groupId || 0,
      title: title.trim() || "Summer holiday",
      start_date: startDate,
      end_date: endDate,
    };
  }

  async function reviewClosure() {
    setSaving(true);
    setError("");
    setNotice("");
    try {
      const response = await fetch(academicRoutes.adminAcademicCalendarClosurePreview, {
        method: "POST",
        credentials: "same-origin",
        headers: jsonCsrfHeaders(csrf),
        body: JSON.stringify(payload()),
      });
      const json = await response.json().catch(() => ({}));
      if (!apiSucceeded(response, json)) throw new Error(apiErrorMessage(json, "Unable to preview this holiday lock."));
      setPreview(apiData<ClosurePreview>(json));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to preview this holiday lock.");
    } finally {
      setSaving(false);
    }
  }

  async function createClosure() {
    setSaving(true);
    setError("");
    setNotice("");
    try {
      const response = await fetch(academicRoutes.adminAcademicCalendarClosureCreate, {
        method: "POST",
        credentials: "same-origin",
        headers: jsonCsrfHeaders(csrf),
        body: JSON.stringify(payload()),
      });
      const json = await response.json().catch(() => ({}));
      if (!apiSucceeded(response, json)) throw new Error(apiErrorMessage(json, "Unable to create this holiday lock."));
      setPreview(null);
      setTitle("Summer holiday");
      const summer = presetDates(Number(year), "summer");
      setStartDate(summer.startDate);
      setEndDate(summer.endDate);
      await loadClosures();
      await onChanged?.();
      setNotice("Holiday lock created and future lessons were safely reflowed.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to create this holiday lock.");
    } finally {
      setSaving(false);
    }
  }

  async function unlockClosure() {
    if (!unlockTarget) return;
    setSaving(true);
    setError("");
    setNotice("");
    try {
      const response = await fetch(academicRoutes.adminAcademicCalendarClosureUnlock(unlockTarget.id), {
        method: "POST",
        credentials: "same-origin",
        headers: jsonCsrfHeaders(csrf),
        body: JSON.stringify({ rebuild_future: rebuildFuture }),
      });
      const json = await response.json().catch(() => ({}));
      if (!apiSucceeded(response, json)) throw new Error(apiErrorMessage(json, "Unable to unlock this holiday."));
      setUnlockTarget(null);
      setRebuildFuture(false);
      await loadClosures();
      await onChanged?.();
      setNotice(rebuildFuture ? "Holiday unlocked and the future timetable was rebuilt." : "Holiday unlocked. Existing lesson dates were preserved.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to unlock this holiday.");
    } finally {
      setSaving(false);
    }
  }

  function close() {
    if (saving) return;
    if (dirty && !window.confirm("Discard your unsaved holiday lock?")) return;
    onClose();
  }

  return (
    <Modal
      open={open}
      onClose={close}
      title={<span className="inline-flex items-center gap-2"><LockKeyhole className="h-5 w-5 text-primary" />{groupId ? "Group Breaks" : "School Breaks"}</span>}
      subtitle={groupId ? `Lock teaching dates for ${groupName || "this group"}. School-wide locks are inherited.` : "Lock teaching dates for every group in a selected school."}
      size="lg"
      mobileMode="sheet"
      closeOnEscape={!saving}
      closeOnOutsideClick={!saving}
    >
      <div className="flex min-h-0 flex-1 flex-col">
        <ModalBody className="space-y-5">
          {error ? <p role="alert" className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm font-semibold text-red-700">{error}</p> : null}
          {notice ? <p role="status" className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm font-semibold text-emerald-800">{notice}</p> : null}

          <section className="space-y-3" aria-labelledby="new-break-title">
            <div className="flex items-center justify-between gap-3">
              <div><h4 id="new-break-title" className="text-sm font-black">New holiday lock</h4><p className="text-xs text-muted-foreground">Lessons move to the next valid teaching dates; academic records stay attached.</p></div>
              <span className="rounded-full bg-primary/8 px-2.5 py-1 text-[10px] font-bold uppercase text-primary">{groupId ? "Group only" : "School-wide"}</span>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              {!fixedSchoolId ? <label><span className="mb-1 block text-xs font-bold uppercase text-muted-foreground">School</span><Select value={schoolId} onChange={(event) => { setSchoolId(event.target.value); setPreview(null); }} required><option value="">Select school</option>{schools.map((school) => <option key={asNumber(school.id)} value={asString(school.id)}>{asString(school.name)}</option>)}</Select></label> : null}
              <label><span className="mb-1 block text-xs font-bold uppercase text-muted-foreground">Academic year</span><Select value={year} onChange={(event) => { const next = Number(event.target.value); setYear(event.target.value); const dates = presetDates(next, "summer"); setStartDate(dates.startDate); setEndDate(dates.endDate); setPreview(null); }}>{Array.from({ length: 7 }, (_, index) => defaultYear - 2 + index).map((value) => <option key={value} value={value}>{value}</option>)}</Select></label>
              <label className={!fixedSchoolId ? "" : "sm:col-span-1"}><span className="mb-1 block text-xs font-bold uppercase text-muted-foreground">Title</span><input value={title} onChange={(event) => { setTitle(event.target.value); setPreview(null); }} className="h-11 w-full rounded-lg border border-foreground/10 bg-background px-3 text-sm" /></label>
            </div>
            <fieldset><legend className="mb-2 text-xs font-bold uppercase text-muted-foreground">Quick presets</legend><div className="grid grid-cols-2 gap-2 sm:grid-cols-4">{(["june", "july", "august", "summer"] as const).map((preset) => <button key={preset} type="button" onClick={() => applyPreset(preset)} className="min-h-11 rounded-lg border border-foreground/10 bg-muted/40 px-3 text-xs font-bold capitalize transition-colors hover:border-primary/25 hover:bg-primary/5 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40">{preset === "summer" ? "Jun–Aug" : preset}</button>)}</div></fieldset>
            <div className="grid gap-3 sm:grid-cols-2">
              <label><span className="mb-1 block text-xs font-bold uppercase text-muted-foreground">First locked date</span><input type="date" required value={startDate} onChange={(event) => { setStartDate(event.target.value); setPreview(null); }} className="h-11 w-full rounded-lg border border-foreground/10 bg-background px-3 text-sm" /></label>
              <label><span className="mb-1 block text-xs font-bold uppercase text-muted-foreground">Last locked date</span><input type="date" required value={endDate} onChange={(event) => { setEndDate(event.target.value); setPreview(null); }} className="h-11 w-full rounded-lg border border-foreground/10 bg-background px-3 text-sm" /></label>
            </div>
            {dateError ? <p role="alert" className="text-xs font-semibold text-red-700">{dateError}</p> : null}
            {preview ? <div className={`rounded-xl border p-3 ${preview.conflicts?.length ? "border-red-200 bg-red-50" : "border-primary/15 bg-primary/5"}`}><p className="text-sm font-black">Review impact</p><div className="mt-2 grid grid-cols-3 gap-2 text-center"><div><strong className="block text-lg tabular-nums">{preview.affectedGroupCount}</strong><span className="text-[10px] text-muted-foreground">groups</span></div><div><strong className="block text-lg tabular-nums">{preview.affectedLessonCount}</strong><span className="text-[10px] text-muted-foreground">lessons moved</span></div><div><strong className="block text-lg tabular-nums">{preview.preservedRecordedLessonCount}</strong><span className="text-[10px] text-muted-foreground">records preserved</span></div></div>{preview.conflicts?.length ? <p className="mt-2 text-xs font-semibold text-red-700">{preview.conflicts[0]}</p> : <p className="mt-2 text-xs text-muted-foreground">Lesson IDs and academic records will not be recreated or deleted.</p>}</div> : null}
          </section>

          <section className="border-t border-foreground/8 pt-4" aria-labelledby="active-breaks-title">
            <div className="flex items-center justify-between"><div><h4 id="active-breaks-title" className="text-sm font-black">Active locks</h4><p className="text-xs text-muted-foreground">{year} calendar closures</p></div>{loading ? <span className="text-xs text-muted-foreground">Loading…</span> : null}</div>
            <div className="mt-3 space-y-2">
              {!loading && visibleItems.length === 0 ? <div className="rounded-lg border border-dashed border-foreground/15 px-4 py-6 text-center text-xs text-muted-foreground">No holiday locks for this year.</div> : null}
              {visibleItems.map((item) => {
                const inherited = Boolean(groupId && item.scope === "school");
                const readOnly = inherited || Boolean(!groupId && item.scope === "group");
                const scopeLabel = inherited
                  ? "Inherited school lock"
                  : item.scope === "school"
                    ? item.schoolName || "School-wide"
                    : `${item.groupName || "Group"} · Group only`;
                return <article key={item.id} className="flex flex-col gap-3 rounded-xl border border-foreground/10 bg-muted/25 p-3 sm:flex-row sm:items-center"><div className="flex min-w-0 flex-1 items-start gap-3"><span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-amber-100 text-amber-800"><CalendarDays className="h-4 w-4" /></span><div className="min-w-0"><p className="truncate text-sm font-black">{item.title}</p><p className="mt-0.5 text-xs text-muted-foreground">{formatDate(item.startDate)} – {formatDate(item.endDate)}</p><span className="mt-1 inline-flex rounded-full bg-background px-2 py-0.5 text-[10px] font-bold uppercase text-muted-foreground">{scopeLabel}</span></div></div>{readOnly ? <LockKeyhole className="h-4 w-4 shrink-0 text-muted-foreground" aria-label="Read-only calendar lock" /> : <button type="button" onClick={() => { setUnlockTarget(item); setRebuildFuture(false); }} className="inline-flex min-h-11 items-center justify-center gap-1.5 rounded-lg border border-foreground/10 bg-background px-3 text-xs font-bold text-muted-foreground hover:bg-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"><Unlock className="h-3.5 w-3.5" />Unlock</button>}</article>;
              })}
            </div>
          </section>

          {unlockTarget ? <section className="rounded-xl border border-amber-200 bg-amber-50 p-3" aria-labelledby="unlock-title"><div className="flex items-start justify-between gap-3"><div><h4 id="unlock-title" className="text-sm font-black text-amber-950">Unlock {unlockTarget.title}?</h4><p className="mt-1 text-xs text-amber-900">Unlocking does not change moved dates unless you explicitly rebuild future lessons.</p></div><button type="button" onClick={() => setUnlockTarget(null)} className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg text-amber-950 hover:bg-amber-100" aria-label="Cancel unlock"><X className="h-4 w-4" /></button></div><label className="mt-3 flex cursor-pointer items-start gap-2 rounded-lg border border-amber-300 bg-white/70 p-3"><input type="checkbox" checked={rebuildFuture} onChange={(event) => setRebuildFuture(event.target.checked)} className="mt-0.5 accent-amber-700" /><span><strong className="block text-xs text-amber-950">Rebuild future timetable</strong><span className="mt-0.5 block text-[11px] leading-4 text-amber-800">Pull future unrecorded lessons into the reopened teaching dates. Recorded history remains fixed.</span></span></label><button type="button" disabled={saving} onClick={() => void unlockClosure()} className="mt-3 inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-lg bg-amber-700 px-4 text-sm font-bold text-white disabled:opacity-50"><RotateCcw className="h-4 w-4" />{saving ? "Unlocking…" : rebuildFuture ? "Unlock and rebuild" : "Unlock only"}</button></section> : null}
        </ModalBody>
        <ModalFooter className="flex justify-end gap-2">
          <button type="button" onClick={close} disabled={saving} className="min-h-11 rounded-lg bg-muted px-4 text-sm font-bold text-muted-foreground disabled:opacity-50">Cancel</button>
          {!preview ? <button type="button" onClick={() => void reviewClosure()} disabled={saving || !selectedSchoolId || !startDate || !endDate || !title.trim() || Boolean(dateError)} className="min-h-11 rounded-lg bg-primary px-5 text-sm font-bold text-primary-foreground disabled:opacity-50">{saving ? "Reviewing…" : "Review lock"}</button> : <button type="button" onClick={() => void createClosure()} disabled={saving || Boolean(preview.conflicts?.length)} className="min-h-11 rounded-lg bg-primary px-5 text-sm font-bold text-primary-foreground disabled:opacity-50">{saving ? "Creating…" : "Create holiday lock"}</button>}
        </ModalFooter>
      </div>
    </Modal>
  );
}
