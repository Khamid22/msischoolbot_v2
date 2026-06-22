import { useMemo, useState } from "react";
import {
  Archive,
  BookOpen,
  ExternalLink,
  FileText,
  FolderOpen,
  Link,
  Pencil,
  Plus,
  Search,
  Upload,
  X,
} from "lucide-react";
import { ChartCard } from "@/shared/ui/ChartCard";
import { routes } from "@/shared/lib/routes";
import { asNumber, asString, sortSubjectsMathFirst, submitConfirm } from "../shared";

type ResourceRow = Record<string, unknown>;

function resourceHref(resource: ResourceRow) {
  return asString(resource.resource_file_url) || asString(resource.resource_url);
}

function resourceKind(resource: ResourceRow) {
  if (asString(resource.resource_file_url)) return asString(resource.resource_file_kind) || "file";
  if (asString(resource.resource_url)) return "link";
  return "resource";
}

export default function ResourcesPanel({ state }: { state: any }) {
  const {
    props,
    resourceTypes,
    editingTypeId,
    setEditingTypeId,
    activeResourceTypes,
    uploadFormKey,
    submitResourceForm,
    resourceUploadState,
    isSubmittingResource,
    resourcesList,
    resourceSubjectFilter,
    setResourceSubjectFilter,
    setEditingResource,
    setEditError,
    lastResourceTypeId,
    setLastResourceTypeId,
  } = state;

  const [addOpen, setAddOpen] = useState(false);
  const [typeManagerOpen, setTypeManagerOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("all");
  const [folderFilter, setFolderFilter] = useState("all");

  const uploadSubjectOptions = sortSubjectsMathFirst(
    Array.isArray(props.adminResourceSubjectOptions) ? props.adminResourceSubjectOptions : [],
  );
  const defaultUploadSubject = uploadSubjectOptions[0] || "";

  const resourceSubjects: string[] = useMemo(
    () =>
      sortSubjectsMathFirst(
        Array.from(
          new Set(
            resourcesList
              .map((row: ResourceRow) => asString(row.subject_name))
              .filter(Boolean),
          ),
        ),
      ),
    [resourcesList],
  );

  const folderOptions = useMemo<string[]>(
    () =>
      Array.from<string>(
        new Set<string>(
          resourcesList
            .map((row: ResourceRow) => asString(row.folder_path) || "General")
            .filter(Boolean),
        ),
      ).sort((a: string, b: string) => a.localeCompare(b)),
    [resourcesList],
  );

  const filteredResources = useMemo(() => {
    const query = search.trim().toLowerCase();
    return resourcesList.filter((resource: ResourceRow) => {
      const subject = asString(resource.subject_name);
      const typeName = asString(resource.resource_type_name);
      const folderPath = asString(resource.folder_path) || "General";
      const haystack = [
        subject,
        typeName,
        folderPath,
        asString(resource.title),
        asString(resource.description),
        asString(resource.resource_url),
      ]
        .join(" ")
        .toLowerCase();
      return (
        (resourceSubjectFilter === "all" || subject === resourceSubjectFilter) &&
        (typeFilter === "all" || typeName === typeFilter) &&
        (folderFilter === "all" || folderPath === folderFilter) &&
        (!query || haystack.includes(query))
      );
    });
  }, [folderFilter, resourceSubjectFilter, resourcesList, search, typeFilter]);

  const totalFiles = resourcesList.filter((row: ResourceRow) => asString(row.resource_file_url)).length;
  const totalLinks = resourcesList.filter((row: ResourceRow) => asString(row.resource_url) && !asString(row.resource_file_url)).length;

  return (
    <div className="space-y-4">
      <ChartCard
        title="Resource Library"
        subtitle="Attach materials to subjects, topics, lessons, and resource types."
        icon={<BookOpen className="h-4 w-4 text-info" />}
      >
        <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div className="grid min-w-0 flex-1 gap-3 sm:grid-cols-3">
            <div className="rounded-xl border border-foreground/10 bg-muted/30 p-3">
              <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Resources</p>
              <p className="mt-1 text-2xl font-bold">{resourcesList.length}</p>
            </div>
            <div className="rounded-xl border border-foreground/10 bg-muted/30 p-3">
              <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Files</p>
              <p className="mt-1 text-2xl font-bold">{totalFiles}</p>
            </div>
            <div className="rounded-xl border border-foreground/10 bg-muted/30 p-3">
              <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Links</p>
              <p className="mt-1 text-2xl font-bold">{totalLinks}</p>
            </div>
          </div>
          <div className="flex shrink-0 flex-wrap gap-2">
            <button
              type="button"
              onClick={() => setAddOpen(true)}
              className="inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-sm font-bold text-primary-foreground shadow-neo"
            >
              <Plus className="h-4 w-4" />
              Add Resource
            </button>
          </div>
        </div>

      </ChartCard>

      <ChartCard title="Browse Resources" subtitle={`${filteredResources.length} shown · ${resourcesList.length} total`} icon={<Search className="h-4 w-4 text-info" />}>
        <div className="grid gap-3 xl:grid-cols-[minmax(0,1fr)_240px_220px_220px]">
          <label className="relative block">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search title, topic, description, or link"
              className="w-full rounded-xl border border-foreground/10 bg-surface py-2.5 pl-10 pr-3 text-sm outline-none focus:border-foreground/30"
            />
          </label>
          <select
            value={resourceSubjectFilter}
            onChange={(event) => setResourceSubjectFilter(event.target.value)}
            className="w-full rounded-xl border border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none focus:border-foreground/30"
          >
            <option value="all">All subjects</option>
            {resourceSubjects.map((subject) => (
              <option key={subject} value={subject}>
                {subject}
              </option>
            ))}
          </select>
          <select
            value={typeFilter}
            onChange={(event) => setTypeFilter(event.target.value)}
            className="w-full rounded-xl border border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none focus:border-foreground/30"
          >
            <option value="all">All resource types</option>
            {activeResourceTypes.map((typeRow: ResourceRow) => (
              <option key={asNumber(typeRow.id)} value={asString(typeRow.name)}>
                {asString(typeRow.name)}
              </option>
            ))}
          </select>
          <select
            value={folderFilter}
            onChange={(event) => setFolderFilter(event.target.value)}
            className="w-full rounded-xl border border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none focus:border-foreground/30"
          >
            <option value="all">All topics / folders</option>
            {folderOptions.map((folder) => (
              <option key={folder} value={folder}>
                {folder}
              </option>
            ))}
          </select>
        </div>

        <div className="mt-4 overflow-hidden rounded-xl border border-foreground/10">
          <div className="max-h-[58dvh] overflow-auto">
            <table className="w-full min-w-[920px] text-left">
              <thead className="sticky top-0 z-20 bg-muted shadow-[0_1px_0_hsl(var(--foreground)/0.08)]">
                <tr>
                  {["Resource", "Subject", "Topic / Folder", "Type", "Source", "Actions"].map((heading) => (
                    <th key={heading} className="px-4 py-3 text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                      {heading}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filteredResources.length ? (
                  filteredResources.map((resource: ResourceRow) => {
                    const href = resourceHref(resource);
                    const kind = resourceKind(resource);
                    return (
                      <tr key={asNumber(resource.id)} className="border-t border-foreground/5 bg-surface align-top">
                        <td className="px-4 py-3">
                          <div className="max-w-[320px]">
                            <p className="truncate text-sm font-bold">{asString(resource.title) || "Untitled resource"}</p>
                            {asString(resource.description) ? (
                              <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">{asString(resource.description)}</p>
                            ) : null}
                          </div>
                        </td>
                        <td className="px-4 py-3 text-sm">{asString(resource.subject_name) || "-"}</td>
                        <td className="px-4 py-3 text-sm">{asString(resource.folder_path) || "General"}</td>
                        <td className="px-4 py-3">
                          <span className="rounded-full bg-muted px-2.5 py-1 text-xs font-bold text-muted-foreground">
                            {asString(resource.resource_type_name) || "Resource"}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          {href ? (
                            <a href={href} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1.5 rounded-lg bg-muted px-3 py-2 text-xs font-bold text-foreground hover:bg-foreground/10">
                              {kind === "link" ? <Link className="h-3.5 w-3.5" /> : <FileText className="h-3.5 w-3.5" />}
                              Open
                              <ExternalLink className="h-3 w-3" />
                            </a>
                          ) : (
                            <span className="text-xs text-muted-foreground">No source</span>
                          )}
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex gap-2">
                            <button
                              type="button"
                              onClick={() => {
                                setEditingResource({
                                  id: asNumber(resource.id),
                                  title: asString(resource.title),
                                  description: asString(resource.description),
                                  resourceFileKind: asString(resource.resource_file_kind),
                                  thumbnailUrl: asString(resource.thumbnail_url),
                                  resourceTypeId: asNumber(resource.resource_type_id),
                                });
                                setEditError("");
                              }}
                              className="inline-flex items-center gap-1 rounded-lg bg-muted px-3 py-2 text-xs font-bold text-foreground hover:bg-foreground/10"
                            >
                              <Pencil className="h-3 w-3" /> Edit
                            </button>
                            <form
                              action={routes.adminResourceDelete(asNumber(resource.id))}
                              method="post"
                              onSubmit={(event) => submitConfirm(event, "Archive this resource? Existing data will stay in the database.")}
                            >
                              <input type="hidden" name="csrf_token" value={props.csrfToken || ""} />
                              <button className="inline-flex items-center gap-1 rounded-lg bg-warning/15 px-3 py-2 text-xs font-bold text-warning-foreground">
                                <Archive className="h-3 w-3" /> Archive
                              </button>
                            </form>
                          </div>
                        </td>
                      </tr>
                    );
                  })
                ) : (
                  <tr>
                    <td colSpan={6} className="px-4 py-10 text-center text-sm text-muted-foreground">
                      No resources match these filters.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </ChartCard>

      {addOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/60 p-4" onClick={() => setAddOpen(false)}>
          <div className="flex max-h-[90dvh] w-full max-w-2xl flex-col overflow-hidden rounded-2xl bg-surface shadow-card-hover animate-in fade-in zoom-in-95 duration-150 motion-reduce:animate-none" onClick={(event) => event.stopPropagation()}>
            <div className="flex shrink-0 items-center justify-between border-b border-foreground/5 px-5 py-3">
              <div>
                <h3 className="text-sm font-bold">Add Resource</h3>
                <p className="text-xs text-muted-foreground">Use a file, an external URL, or both.</p>
              </div>
              <button type="button" onClick={() => setAddOpen(false)} className="flex h-8 w-8 items-center justify-center rounded-lg hover:bg-muted">
                <X className="h-4 w-4" />
              </button>
            </div>

            <form
              key={uploadFormKey}
              action={routes.adminResourceAdd}
              method="post"
              encType="multipart/form-data"
              className="min-h-0 flex-1 overflow-y-auto"
              onSubmit={submitResourceForm}
            >
              <input type="hidden" name="csrf_token" value={props.csrfToken || ""} />
              <input type="hidden" name="upload_id" value="" />
              <div className="grid gap-4 px-5 py-4 md:grid-cols-2">
                <label className="block">
                  <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Subject</span>
                  <select
                    name="resource_subject_name"
                    required
                    defaultValue={defaultUploadSubject}
                    className="w-full rounded-xl border border-foreground/10 bg-background px-4 py-2.5 text-sm outline-none focus:border-foreground/30"
                  >
                    {!defaultUploadSubject ? <option value="" disabled>Select subject</option> : null}
                    {uploadSubjectOptions.map((subjectName: string) => (
                      <option key={subjectName} value={subjectName}>
                        {subjectName}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="block">
                  <span className="mb-1.5 flex items-center justify-between gap-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    Resource Type
                    <button
                      type="button"
                      onClick={() => setTypeManagerOpen((value) => !value)}
                      className="inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-[10px] font-bold normal-case tracking-normal text-primary hover:bg-primary/10"
                    >
                      <FolderOpen className="h-3 w-3" />
                      Manage
                    </button>
                  </span>
                  <select
                    name="resource_type_id"
                    required
                    defaultValue={lastResourceTypeId}
                    onChange={(event) => setLastResourceTypeId(event.target.value)}
                    className="w-full rounded-xl border border-foreground/10 bg-background px-4 py-2.5 text-sm outline-none focus:border-foreground/30"
                  >
                    <option value="" disabled>Select type</option>
                    {activeResourceTypes.map((typeRow: ResourceRow) => (
                      <option key={asNumber(typeRow.id)} value={asNumber(typeRow.id)}>
                        {asString(typeRow.name)}
                      </option>
                    ))}
                  </select>
                </label>
                {typeManagerOpen ? (
                  <div className="rounded-2xl border border-foreground/10 bg-background p-4 md:col-span-2">
                    <div className="mb-3 flex items-start justify-between gap-3">
                      <div>
                        <h4 className="text-sm font-bold">Resource Types</h4>
                        <p className="text-xs text-muted-foreground">Create or rename labels used in this resource form.</p>
                      </div>
                      <button type="button" onClick={() => setTypeManagerOpen(false)} className="rounded-lg bg-muted px-3 py-1.5 text-xs font-bold text-muted-foreground">
                        Close
                      </button>
                    </div>
                    <form action={routes.adminResourceTypeAdd} method="post" className="grid gap-2 sm:grid-cols-[minmax(0,1fr)_auto]">
                      <input type="hidden" name="csrf_token" value={props.csrfToken || ""} />
                      <input
                        type="text"
                        name="resource_type_name"
                        placeholder="Video Lesson, Worksheet, Mark Scheme..."
                        required
                        className="w-full rounded-xl border border-foreground/10 bg-surface px-4 py-2.5 text-sm outline-none focus:border-foreground/30"
                      />
                      <button className="rounded-xl bg-primary px-4 py-2.5 text-sm font-bold text-primary-foreground">Add Type</button>
                    </form>

                    <div className="mt-3 grid gap-2 sm:grid-cols-2">
                      {resourceTypes.length ? (
                        resourceTypes.map((typeRow: ResourceRow) => {
                          const typeId = asNumber(typeRow.id);
                          const isEditing = editingTypeId === typeId;
                          return (
                            <div key={typeId} className="rounded-xl border border-foreground/10 bg-surface p-3">
                              {isEditing ? (
                                <form action={routes.adminResourceTypeRename(typeId)} method="post" className="space-y-2">
                                  <input type="hidden" name="csrf_token" value={props.csrfToken || ""} />
                                  <input
                                    type="text"
                                    name="resource_type_name"
                                    defaultValue={asString(typeRow.name)}
                                    required
                                    className="w-full rounded-lg border border-foreground/10 bg-background px-3 py-2 text-sm outline-none"
                                  />
                                  <div className="flex gap-2">
                                    <button className="rounded-lg bg-primary px-3 py-2 text-xs font-bold text-primary-foreground">Save</button>
                                    <button type="button" onClick={() => setEditingTypeId(null)} className="rounded-lg bg-muted px-3 py-2 text-xs font-bold text-muted-foreground">
                                      Cancel
                                    </button>
                                  </div>
                                </form>
                              ) : (
                                <div className="flex items-center justify-between gap-3">
                                  <strong className="min-w-0 truncate text-sm">{asString(typeRow.name)}</strong>
                                  <div className="flex shrink-0 gap-2">
                                    <button type="button" onClick={() => setEditingTypeId(typeId)} className="rounded-lg bg-muted px-3 py-2 text-xs font-bold text-muted-foreground">
                                      Rename
                                    </button>
                                    <form
                                      action={routes.adminResourceTypeDelete(typeId)}
                                      method="post"
                                      onSubmit={(event) => submitConfirm(event, "Archive this resource type? Existing data will stay in the database.")}
                                    >
                                      <input type="hidden" name="csrf_token" value={props.csrfToken || ""} />
                                      <button className="rounded-lg bg-warning/15 px-3 py-2 text-xs font-bold text-warning-foreground">Archive</button>
                                    </form>
                                  </div>
                                </div>
                              )}
                            </div>
                          );
                        })
                      ) : (
                        <p className="text-sm text-muted-foreground">No resource types yet.</p>
                      )}
                    </div>
                  </div>
                ) : null}
                <label className="block md:col-span-2">
                  <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Title</span>
                  <input
                    type="text"
                    name="resource_title"
                    required
                    placeholder="Lesson 12 worksheet, Quadratics video, Past paper set..."
                    className="w-full rounded-xl border border-foreground/10 bg-background px-4 py-2.5 text-sm outline-none focus:border-foreground/30"
                  />
                </label>
                <label className="block">
                  <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Topic / Lesson Folder</span>
                  <input
                    type="text"
                    name="resource_folder_path"
                    placeholder="Lesson 12 / Quadratic Equations"
                    className="w-full rounded-xl border border-foreground/10 bg-background px-4 py-2.5 text-sm outline-none focus:border-foreground/30"
                  />
                </label>
                <label className="block">
                  <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">External URL</span>
                  <input
                    type="url"
                    name="resource_url"
                    placeholder="https://..."
                    className="w-full rounded-xl border border-foreground/10 bg-background px-4 py-2.5 text-sm outline-none focus:border-foreground/30"
                  />
                </label>
                <label className="block">
                  <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Upload File</span>
                  <input
                    type="file"
                    name="resource_file"
                    disabled={!props.adminResourceUploadEnabled}
                    className="w-full rounded-xl border border-foreground/10 bg-background px-4 py-2.5 text-sm outline-none disabled:opacity-50"
                  />
                </label>
                <label className="block">
                  <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    Thumbnail <span className="font-normal normal-case text-muted-foreground/60">(optional, videos)</span>
                  </span>
                  <input
                    type="file"
                    name="thumbnail_file"
                    accept="image/jpeg,image/png,image/webp"
                    disabled={!props.adminResourceUploadEnabled}
                    className="w-full rounded-xl border border-foreground/10 bg-background px-4 py-2.5 text-sm outline-none disabled:opacity-50"
                  />
                </label>
                {!props.adminResourceUploadEnabled ? (
                  <p className="rounded-xl border border-warning/30 bg-warning/10 p-3 text-xs font-semibold text-warning-foreground md:col-span-2">
                    File upload is disabled here. You can still save resources as external links.
                  </p>
                ) : null}
                <label className="block md:col-span-2">
                  <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Description</span>
                  <textarea
                    name="resource_description"
                    rows={4}
                    placeholder="Short note for teachers/students about how to use this resource."
                    className="w-full rounded-xl border border-foreground/10 bg-background px-4 py-2.5 text-sm outline-none focus:border-foreground/30"
                  />
                </label>
                {resourceUploadState.active ? (
                  <div className="md:col-span-2">
                    <div className="overflow-hidden rounded-full bg-muted" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(resourceUploadState.percent)}>
                      <div
                        className={`h-2 rounded-full transition-[width] duration-200 ${resourceUploadState.error ? "bg-destructive" : "bg-primary"}`}
                        style={{ width: `${Math.max(0, Math.min(100, resourceUploadState.percent))}%` }}
                      />
                    </div>
                    <p className={`mt-2 text-xs font-semibold uppercase tracking-wide ${resourceUploadState.error ? "text-destructive" : "text-muted-foreground"}`}>
                      {resourceUploadState.message}
                    </p>
                  </div>
                ) : null}
              </div>
              <div className="flex shrink-0 justify-end gap-2 border-t border-foreground/5 px-5 py-3">
                <button type="button" onClick={() => setAddOpen(false)} className="rounded-xl bg-muted px-4 py-2.5 text-sm font-bold text-muted-foreground">
                  Cancel
                </button>
                <button disabled={isSubmittingResource} className="inline-flex items-center gap-2 rounded-xl bg-primary px-5 py-2.5 text-sm font-bold text-primary-foreground shadow-neo disabled:opacity-50">
                  <Upload className="h-4 w-4" />
                  {isSubmittingResource ? "Saving..." : "Save Resource"}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </div>
  );
}
