import { BookOpen, Pencil, Plus, Upload } from "lucide-react";
import { ChartCard } from "@/components/ChartCard";
import { routes } from "@/lib/routes";
import { asNumber, asString, sortSubjectsMathFirst, submitConfirm } from "../shared";

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
  } = state;
  const uploadSubjectOptions = sortSubjectsMathFirst(
    Array.isArray(props.adminResourceSubjectOptions)
      ? props.adminResourceSubjectOptions
      : []
  );
  const defaultUploadSubject = uploadSubjectOptions[0] || "";

  return (
    <div className="grid gap-4 xl:grid-cols-[320px_minmax(0,1fr)]">
      <div className="space-y-4">
        <ChartCard title="Resource Types" icon={<Plus className="h-4 w-4 text-info" />}>
          <form action={routes.adminResourceTypeAdd} method="post" className="space-y-3">
            <input type="hidden" name="csrf_token" value={props.csrfToken || ""} />
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Type Name</span>
              <input
                type="text"
                name="resource_type_name"
                placeholder="Video, Definitions, Worksheet..."
                required
                className="w-full rounded-xl border-2 border-foreground/10 bg-surface px-4 py-2.5 text-sm outline-none"
              />
            </label>
            <button className="rounded-xl bg-primary px-4 py-2.5 text-sm font-bold text-primary-foreground">Add Type</button>
          </form>

          <div className="mt-4 space-y-2">
            {resourceTypes.length ? (
              resourceTypes.map((typeRow: Record<string, unknown>) => {
                const typeId = asNumber(typeRow.id);
                const isEditing = editingTypeId === typeId;
                return (
                  <div key={typeId} className="rounded-lg border border-foreground/5 p-3">
                    {isEditing ? (
                      <form action={routes.adminResourceTypeRename(typeId)} method="post" className="space-y-2">
                        <input type="hidden" name="csrf_token" value={props.csrfToken || ""} />
                        <input
                          type="text"
                          name="resource_type_name"
                          defaultValue={asString(typeRow.name)}
                          required
                          className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2 text-sm outline-none"
                        />
                        <div className="flex gap-2">
                          <button className="rounded-lg bg-primary px-3 py-2 text-xs font-bold text-primary-foreground">Done</button>
                          <button type="button" onClick={() => setEditingTypeId(null)} className="rounded-lg bg-muted px-3 py-2 text-xs font-bold text-muted-foreground">
                            Cancel
                          </button>
                        </div>
                      </form>
                    ) : (
                      <div className="flex items-center justify-between gap-3">
                        <strong className="text-sm">{asString(typeRow.name)}</strong>
                        <div className="flex gap-2">
                          <button type="button" onClick={() => setEditingTypeId(typeId)} className="rounded-lg bg-muted px-3 py-2 text-xs font-bold text-muted-foreground">
                            Rename
                          </button>
                          <form
                            action={routes.adminResourceTypeDelete(typeId)}
                            method="post"
                            onSubmit={(event) => submitConfirm(event, "Delete this resource type?")}
                          >
                            <input type="hidden" name="csrf_token" value={props.csrfToken || ""} />
                            <button className="rounded-lg bg-destructive/10 px-3 py-2 text-xs font-bold text-destructive">Delete</button>
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
        </ChartCard>
      </div>

      <div className="space-y-4">
        <ChartCard title="Add Resource" icon={<Upload className="h-4 w-4 text-info" />}>
          <form
            key={uploadFormKey}
            action={routes.adminResourceAdd}
            method="post"
            encType="multipart/form-data"
            className="grid gap-3 md:grid-cols-2"
            onSubmit={submitResourceForm}
          >
            <input type="hidden" name="csrf_token" value={props.csrfToken || ""} />
            <input type="hidden" name="upload_id" value="" />
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Subject</span>
              <select
                name="resource_subject_name"
                required
                defaultValue={defaultUploadSubject}
                className="w-full rounded-xl border-2 border-foreground/10 bg-surface px-4 py-2.5 text-sm outline-none"
              >
                {!defaultUploadSubject ? (
                  <option value="" disabled>
                    Select subject
                  </option>
                ) : null}
                {uploadSubjectOptions.map((subjectName: string) => (
                  <option key={subjectName} value={subjectName}>
                    {subjectName}
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Resource Type</span>
              <select name="resource_type_id" required className="w-full rounded-xl border-2 border-foreground/10 bg-surface px-4 py-2.5 text-sm outline-none">
                <option value="" disabled>
                  Select type
                </option>
                {activeResourceTypes.map((typeRow: Record<string, unknown>) => (
                  <option key={asNumber(typeRow.id)} value={asNumber(typeRow.id)}>
                    {asString(typeRow.name)}
                  </option>
                ))}
              </select>
            </label>
            <label className="block md:col-span-2">
              <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Title</span>
              <input type="text" name="resource_title" required className="w-full rounded-xl border-2 border-foreground/10 bg-surface px-4 py-2.5 text-sm outline-none" />
            </label>
            <div className="grid gap-3 md:col-span-2 md:grid-cols-2">
              <label className="block">
                <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Upload File</span>
                <input
                  type="file"
                  name="resource_file"
                  required
                  disabled={!props.adminResourceUploadEnabled}
                  className="w-full rounded-xl border-2 border-foreground/10 bg-surface px-4 py-2.5 text-sm outline-none disabled:opacity-50"
                />
              </label>
              <label className="block">
                <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Thumbnail Image <span className="font-normal normal-case text-muted-foreground/60">(optional, for videos)</span>
                </span>
                <input
                  type="file"
                  name="thumbnail_file"
                  accept="image/jpeg,image/png,image/webp"
                  disabled={!props.adminResourceUploadEnabled}
                  className="w-full rounded-xl border-2 border-foreground/10 bg-surface px-4 py-2.5 text-sm outline-none disabled:opacity-50"
                />
              </label>
            </div>
            {!props.adminResourceUploadEnabled ? (
              <p className="md:col-span-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Resource upload is disabled in this environment.
              </p>
            ) : null}
            <label className="block md:col-span-2">
              <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Description</span>
              <textarea name="resource_description" rows={4} className="w-full rounded-xl border-2 border-foreground/10 bg-surface px-4 py-2.5 text-sm outline-none" />
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
            <div className="md:col-span-2">
              <button
                disabled={isSubmittingResource || !props.adminResourceUploadEnabled}
                className="rounded-xl bg-primary px-6 py-3 text-sm font-bold text-primary-foreground shadow-neo disabled:opacity-50"
              >
                {isSubmittingResource ? "Uploading..." : props.adminResourceUploadEnabled ? "Save Resource" : "Upload Disabled"}
              </button>
            </div>
          </form>
        </ChartCard>

        {(() => {
          const resourceSubjects: string[] = sortSubjectsMathFirst(
            Array.from(
              new Set(
                resourcesList
                  .map((r: Record<string, unknown>) => asString(r.subject_name))
                  .filter(Boolean)
              )
            )
          );
          const filteredResources =
            resourceSubjectFilter === "all"
              ? resourcesList
              : resourcesList.filter((r: Record<string, unknown>) => asString(r.subject_name) === resourceSubjectFilter);
          return (
            <ChartCard title="Resources" subtitle={`${resourcesList.length} total`} icon={<BookOpen className="h-4 w-4 text-info" />}>
              {resourceSubjects.length > 1 ? (
                <div className="mb-3 flex snap-x snap-mandatory gap-2 overflow-x-auto pb-0.5">
                  <button
                    type="button"
                    onClick={() => setResourceSubjectFilter("all")}
                    className={`inline-flex shrink-0 snap-start items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-semibold transition-colors ${
                      resourceSubjectFilter === "all" ? "bg-foreground text-background" : "bg-muted text-foreground hover:bg-foreground/10"
                    }`}
                  >
                    All <span className="opacity-60">{resourcesList.length}</span>
                  </button>
                  {resourceSubjects.map((subject) => {
                    const count = resourcesList.filter((r: Record<string, unknown>) => asString(r.subject_name) === subject).length;
                    return (
                      <button
                        key={subject}
                        type="button"
                        onClick={() => setResourceSubjectFilter(subject)}
                        className={`inline-flex shrink-0 snap-start items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-semibold transition-colors ${
                          resourceSubjectFilter === subject ? "bg-foreground text-background" : "bg-muted text-foreground hover:bg-foreground/10"
                        }`}
                      >
                        {subject} <span className="opacity-60">{count}</span>
                      </button>
                    );
                  })}
                </div>
              ) : null}

              <div className="overflow-x-auto">
                <div className={filteredResources.length > 5 ? "max-h-80 overflow-y-auto rounded-lg" : ""}>
                  <table className="w-full min-w-[800px] text-left">
                    <thead className="sticky top-0 bg-surface">
                      <tr className="border-b border-foreground/5">
                        {["ID", "Subject", "Type", "Title", "Action"].map((heading) => (
                          <th key={heading} className="px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                            {heading}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {filteredResources.length ? (
                        filteredResources.map((resource: Record<string, unknown>) => (
                          <tr key={asNumber(resource.id)} className="border-b border-foreground/5">
                            <td className="px-3 py-2.5 text-xs">{asNumber(resource.id)}</td>
                            <td className="px-3 py-2.5 text-xs">{asString(resource.subject_name)}</td>
                            <td className="px-3 py-2.5 text-xs">{asString(resource.resource_type_name)}</td>
                            <td className="px-3 py-2.5 text-xs">
                              {asString(resource.resource_file_url) ? (
                                <a href={asString(resource.resource_file_url)} target="_blank" rel="noopener noreferrer" className="block max-w-[260px] truncate hover:underline">
                                  {asString(resource.title) || "Open file"}
                                </a>
                              ) : asString(resource.title) ? (
                                <span className="block max-w-[260px] truncate">{asString(resource.title)}</span>
                              ) : (
                                "-"
                              )}
                            </td>
                            <td className="px-3 py-2.5">
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
                                    });
                                    setEditError("");
                                  }}
                                  className="flex items-center gap-1 rounded-lg bg-muted px-3 py-2 text-xs font-bold text-foreground hover:bg-foreground/10"
                                >
                                  <Pencil className="h-3 w-3" /> Edit
                                </button>
                                <form
                                  action={routes.adminResourceDelete(asNumber(resource.id))}
                                  method="post"
                                  onSubmit={(event) => submitConfirm(event, "Delete this resource?")}
                                >
                                  <input type="hidden" name="csrf_token" value={props.csrfToken || ""} />
                                  <button className="rounded-lg bg-destructive/10 px-3 py-2 text-xs font-bold text-destructive">Delete</button>
                                </form>
                              </div>
                            </td>
                          </tr>
                        ))
                      ) : (
                        <tr>
                          <td colSpan={5} className="px-3 py-4 text-sm text-muted-foreground">
                            No resources yet.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </ChartCard>
          );
        })()}
      </div>
    </div>
  );
}
