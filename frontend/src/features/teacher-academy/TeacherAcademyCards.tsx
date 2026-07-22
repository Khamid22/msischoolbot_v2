import {
  ArrowDownWideNarrow,
  BookOpenCheck,
  Filter,
  RotateCcw,
  Search,
  UserCheck,
} from "lucide-react";
import type { ReactNode } from "react";

import { ActionMenu, type ActionMenuItem } from "@/shared/ui/ActionMenu";
import { ProgressBar } from "@/shared/ui/ProgressBar";
import { StatusBadge } from "@/shared/ui/StatusBadge";
import type { TeacherAcademySort } from "@/features/teacher-academy/model";

export interface TeacherAcademyCardModel {
  key: string;
  kind: "teacher_academy" | "active_teacher";
  fullName: string;
  position: string;
  subject: string;
  statusLabel: string;
  statusTone: "neutral" | "success" | "warning" | "danger" | "info";
  joinedLabel: string;
  passed?: number;
  target?: number;
  averageScore?: number | null;
  completed?: boolean;
  primaryLabel: string;
  onOpen: () => void;
  actions?: ActionMenuItem[];
}

interface SubjectOption {
  id: number | string;
  label: string;
}

interface TeacherRosterToolbarProps {
  search: string;
  subjectId: string;
  sort: TeacherAcademySort;
  subjects: SubjectOption[];
  showSort?: boolean;
  leading?: ReactNode;
  onSearchChange: (value: string) => void;
  onSubjectChange: (value: string) => void;
  onSortChange: (value: TeacherAcademySort) => void;
  onClear?: () => void;
}

const fieldClass =
  "min-h-14 w-full rounded-xl border border-input bg-card px-3 text-sm font-semibold text-foreground shadow-sm outline-none placeholder:text-muted-foreground focus:border-primary/40 focus:ring-2 focus:ring-primary/20";

const avatarTones = [
  "bg-primary text-primary-foreground",
  "bg-info text-info-foreground",
  "bg-success text-success-foreground",
  "bg-warning text-warning-foreground",
  "bg-accent text-accent-foreground",
];

function initials(name: string) {
  const value = name
    .split(/\s+/)
    .filter(Boolean)
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
  return value || "T";
}

function avatarTone(name: string) {
  const seed = Array.from(name).reduce((sum, character) => sum + character.charCodeAt(0), 0);
  return avatarTones[seed % avatarTones.length];
}

export function TeacherRosterToolbar({
  search,
  subjectId,
  sort,
  subjects,
  showSort = true,
  leading,
  onSearchChange,
  onSubjectChange,
  onSortChange,
  onClear,
}: TeacherRosterToolbarProps) {
  const hasFilters = Boolean(search || subjectId || (showSort && sort !== "average_score"));
  return (
    <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
      {leading ? <div className="min-w-0 flex-1">{leading}</div> : null}
      <div className={`grid w-full grid-cols-1 gap-2 md:grid-cols-2 ${showSort ? "lg:max-w-[74rem] lg:grid-cols-[minmax(16rem,1.35fr)_minmax(13rem,1fr)_minmax(12rem,0.9fr)_3.5rem]" : "lg:max-w-[52rem] lg:grid-cols-[minmax(16rem,1.35fr)_minmax(13rem,1fr)_3.5rem]"}`}>
        <label className="relative">
          <span className="sr-only">Search teachers</span>
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
          <input
            type="search"
            value={search}
            onChange={(event) => onSearchChange(event.target.value)}
            className={`${fieldClass} pl-9`}
            placeholder="Search teachers"
            autoComplete="off"
          />
        </label>
        <label className="relative">
          <span className="sr-only">Filter teachers by subject</span>
          <Filter className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
          <select
            value={subjectId}
            onChange={(event) => onSubjectChange(event.target.value)}
            className={`${fieldClass} pl-9`}
          >
            <option value="">All subjects</option>
            {subjects.map((subject) => (
              <option key={subject.id} value={subject.id}>{subject.label}</option>
            ))}
          </select>
        </label>
        {showSort ? (
          <label className="relative">
            <span className="sr-only">Sort Teacher Academy teachers</span>
            <ArrowDownWideNarrow className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
            <select
              value={sort}
              onChange={(event) => onSortChange(event.target.value as TeacherAcademySort)}
              className={`${fieldClass} pl-9`}
            >
              <option value="average_score">Average score</option>
              <option value="lessons">Lessons completed</option>
              <option value="date">Date added</option>
            </select>
          </label>
        ) : null}
        {onClear ? (
          <button
            type="button"
            onClick={onClear}
            disabled={!hasFilters}
            aria-label="Reset teacher filters and sorting"
            title="Reset filters and sorting"
            className="inline-flex h-14 w-14 items-center justify-center justify-self-start rounded-xl border border-border bg-card text-muted-foreground shadow-sm hover:bg-muted hover:text-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 disabled:cursor-not-allowed disabled:opacity-40"
          >
            <RotateCcw className="h-4 w-4" aria-hidden="true" />
          </button>
        ) : null}
      </div>
    </div>
  );
}

function CircularProgress({ passed = 0, target = 0, label }: { passed?: number; target?: number; label: string }) {
  const safeTarget = Math.max(0, target);
  const safePassed = safeTarget ? Math.min(safeTarget, Math.max(0, passed)) : 0;
  const percent = safeTarget ? Math.min(100, (safePassed / safeTarget) * 100) : 0;
  const radius = 24;
  const circumference = 2 * Math.PI * radius;
  return (
    <div
      role="progressbar"
      aria-label={`${label}: ${safePassed} of ${safeTarget} lessons completed`}
      aria-valuemin={0}
      aria-valuemax={Math.max(1, safeTarget)}
      aria-valuenow={safePassed}
      className="relative flex h-16 w-16 shrink-0 items-center justify-center"
    >
      <svg viewBox="0 0 56 56" className="h-16 w-16 -rotate-90" aria-hidden="true">
        <circle cx="28" cy="28" r={radius} fill="none" stroke="currentColor" strokeWidth="5" className="text-muted" />
        <circle
          cx="28"
          cy="28"
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth="5"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={circumference * (1 - percent / 100)}
          className="text-primary transition-[stroke-dashoffset] duration-300 motion-reduce:transition-none"
        />
      </svg>
      <span className="absolute text-xs font-black tabular-nums text-foreground">
        {safePassed}/{safeTarget}
      </span>
    </div>
  );
}

export function TeacherAcademyCard({ teacher }: { teacher: TeacherAcademyCardModel }) {
  const isAcademy = teacher.kind === "teacher_academy";
  const score = teacher.averageScore ?? null;
  return (
    <article className={`flex min-h-[18rem] flex-col rounded-2xl border bg-card p-4 shadow-card transition-[border-color,box-shadow] duration-200 hover:border-primary/25 hover:shadow-card-hover motion-reduce:transition-none sm:p-5 ${
      teacher.completed ? "border-success/35" : "border-border"
    }`}>
      <div className="flex min-w-0 items-start gap-3">
        <div className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-xl text-sm font-black shadow-sm ${avatarTone(teacher.fullName)}`} aria-hidden="true">
          {initials(teacher.fullName)}
        </div>
        <div className="min-w-0 flex-1">
          <h2 className="break-words font-display text-base font-black leading-tight text-foreground">
            {teacher.fullName}
          </h2>
          <p className="mt-1 break-words text-sm font-medium text-muted-foreground">
            {teacher.position}
          </p>
        </div>
        {isAcademy ? (
          <CircularProgress passed={teacher.passed} target={teacher.target} label={teacher.fullName} />
        ) : (
          <span className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-success/10 text-success" title="Active teacher">
            <UserCheck className="h-5 w-5" aria-hidden="true" />
          </span>
        )}
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <StatusBadge tone={teacher.statusTone} className="normal-case tracking-normal">
          {teacher.statusLabel}
        </StatusBadge>
        <span className="max-w-full truncate rounded-full bg-muted px-2.5 py-1 text-[0.6875rem] font-bold text-muted-foreground" title={teacher.subject}>
          {teacher.subject}
        </span>
      </div>

      <dl className="mt-4 grid grid-cols-2 gap-4 border-t border-border pt-4">
        {isAcademy ? (
          <div className="min-w-0">
            <dt className="text-[0.6875rem] font-black uppercase tracking-wide text-muted-foreground">Average score</dt>
            <dd className="mt-1.5 flex items-center gap-2">
              <span className="shrink-0 text-base font-black tabular-nums text-foreground">
                {score === null ? "—" : score.toFixed(1)}
              </span>
              <ProgressBar
                value={score ?? 0}
                max={10}
                label={`${teacher.fullName} average score`}
                className="h-1.5"
              />
            </dd>
          </div>
        ) : (
          <div>
            <dt className="text-[0.6875rem] font-black uppercase tracking-wide text-muted-foreground">Status</dt>
            <dd className="mt-1.5 text-sm font-black text-success">Active</dd>
          </div>
        )}
        <div className="min-w-0">
          <dt className="text-[0.6875rem] font-black uppercase tracking-wide text-muted-foreground">
            {isAcademy ? "Joined" : "Active since"}
          </dt>
          <dd className="mt-1.5 break-words text-sm font-black text-foreground">{teacher.joinedLabel}</dd>
        </div>
      </dl>

      <div className="mt-auto flex items-center justify-between gap-2 pt-5">
        <button
          type="button"
          onClick={teacher.onOpen}
          className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-primary/25 bg-primary/10 px-3 py-2 text-sm font-black text-primary hover:bg-primary/15 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/35"
        >
          <BookOpenCheck className="h-4 w-4" aria-hidden="true" />
          {teacher.primaryLabel}
        </button>
        {teacher.actions?.length ? (
          <ActionMenu
            label={`Actions for ${teacher.fullName}`}
            items={teacher.actions}
            trigger={<span className="text-lg leading-none" aria-hidden="true">•••</span>}
          />
        ) : null}
      </div>
    </article>
  );
}

export function TeacherCardGrid({ teachers }: { teachers: TeacherAcademyCardModel[] }) {
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
      {teachers.map((teacher) => <TeacherAcademyCard key={teacher.key} teacher={teacher} />)}
    </div>
  );
}

export function TeacherCardGridSkeleton({ count = 6 }: { count?: number }) {
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3" aria-label="Loading teachers" aria-busy="true">
      {Array.from({ length: count }, (_, index) => (
        <div key={index} className="min-h-[18rem] animate-pulse rounded-2xl border border-border bg-card p-5 shadow-card motion-reduce:animate-none">
          <div className="flex gap-3">
            <div className="h-12 w-12 rounded-xl bg-muted" />
            <div className="flex-1 space-y-2 pt-1">
              <div className="h-4 w-2/3 rounded bg-muted" />
              <div className="h-3 w-1/2 rounded bg-muted" />
            </div>
            <div className="h-16 w-16 rounded-full bg-muted" />
          </div>
          <div className="mt-5 h-7 w-2/3 rounded-full bg-muted" />
          <div className="mt-5 h-px bg-border" />
          <div className="mt-5 grid grid-cols-2 gap-4">
            <div className="h-10 rounded bg-muted" />
            <div className="h-10 rounded bg-muted" />
          </div>
          <div className="mt-6 h-11 w-32 rounded-xl bg-muted" />
        </div>
      ))}
    </div>
  );
}

export function TeacherGridEmptyState({
  filtered,
  onClear,
}: {
  filtered: boolean;
  onClear?: () => void;
}) {
  return (
    <div className="rounded-2xl border border-dashed border-border bg-card px-5 py-12 text-center">
      <BookOpenCheck className="mx-auto h-8 w-8 text-muted-foreground" aria-hidden="true" />
      <h2 className="mt-3 font-display text-base font-black text-foreground">
        {filtered ? "No teachers match these filters" : "No teachers in this view"}
      </h2>
      <p className="mx-auto mt-1 max-w-md text-sm leading-6 text-muted-foreground">
        {filtered
          ? "Try a different name or subject, or clear the current filters."
          : "Teachers will appear here when they enter this stage."}
      </p>
      {filtered && onClear ? (
        <button
          type="button"
          onClick={onClear}
          className="mt-4 inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-border bg-background px-4 text-sm font-black text-foreground hover:bg-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30"
        >
          <RotateCcw className="h-4 w-4" aria-hidden="true" />
          Clear filters
        </button>
      ) : null}
    </div>
  );
}
