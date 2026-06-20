import { ChangeEvent, useState } from "react";
import { Camera, FileText, KeyRound, Save, Trash2, User, Users } from "lucide-react";
import { AdminEmbedLayout, isAdminEmbedMode, withEmbedMode } from "@/shared/ui/AdminEmbedLayout";
import { TelegramLayout, Topbar } from "@/shared/ui/TelegramLayout";
import { UserAvatar } from "@/shared/ui/Avatar";
import { FormAlert } from "@/shared/ui/PortalCard";

interface StudentProfile {
  id: number;
  surname?: string;
  name?: string;
  full_name?: string;
  student_id?: string;
  password?: string;
  group?: string;
  teacher_name?: string;
  classmates?: string[];
  photo_url?: string;
  profile_description?: string;
}

interface EditStudentProfileProps {
  authLogin?: string;
  authError?: string;
  adminNotice?: string;
  student?: StudentProfile;
  teacherNameOptions?: string[];
  csrfToken?: string;
  saveUrl?: string;
  changePasswordUrl?: string;
  viewDashboardUrl?: string;
  backUrl?: string;
  embedMode?: string;
}

const modalInsetStyle = {
  paddingTop: "var(--app-top-inset)",
  paddingRight: "max(1rem, var(--app-right-inset))",
  paddingBottom: "var(--app-bottom-inset)",
  paddingLeft: "max(1rem, var(--app-left-inset))",
} as const;

export default function EditStudentProfile(props: EditStudentProfileProps) {
  const student = props.student || { id: 0 };
  const [photoPreviewUrl, setPhotoPreviewUrl] = useState(student.photo_url || "");
  const [passwordModalOpen, setPasswordModalOpen] = useState(false);
  const initials = `${String(student.surname || "").slice(0, 1)}${String(student.name || "").slice(0, 1)}`.trim() || "ST";
  const isAdminEmbed = isAdminEmbedMode(props.embedMode);
  const profileTitle = student.full_name || `${student.surname || ""} ${student.name || ""}`.trim() || "Student";
  const profileSubtitle = [student.group || "No group", student.student_id || "No username"].join(" · ");

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }
    setPhotoPreviewUrl(URL.createObjectURL(file));
    const removeInput = document.getElementById("removePhotoInput") as HTMLInputElement | null;
    if (removeInput) {
      removeInput.value = "0";
    }
  }

  function handleDeletePhoto() {
    setPhotoPreviewUrl("");
    const fileInput = document.getElementById("photoFileInput") as HTMLInputElement | null;
    const removeInput = document.getElementById("removePhotoInput") as HTMLInputElement | null;
    if (fileInput) {
      fileInput.value = "";
    }
    if (removeInput) {
      removeInput.value = "1";
    }
  }

  const pageContent = (
    <>
      <div className="space-y-4 animate-in">
        {isAdminEmbed && props.viewDashboardUrl ? (
          <div className="flex justify-end">
            <a
              href={withEmbedMode(props.viewDashboardUrl)}
              className="rounded-lg border border-foreground/10 bg-surface px-3 py-2 text-xs font-bold shadow-card hover:bg-muted"
            >
              View Dashboard
            </a>
          </div>
        ) : null}
        {props.authError ? <FormAlert kind="error">{props.authError}</FormAlert> : null}
        {props.adminNotice ? <FormAlert kind="notice">{props.adminNotice}</FormAlert> : null}

        <form action={props.saveUrl} method="post" encType="multipart/form-data" className="space-y-3">
          <input type="hidden" name="csrf_token" value={props.csrfToken || ""} />
          <input type="hidden" name="photo_url" value={student.photo_url || ""} />
          <input type="hidden" id="removePhotoInput" name="remove_photo" value="0" />

          <section className="overflow-hidden rounded-lg border border-foreground/10 bg-surface shadow-card">
            <div className="flex flex-col gap-4 border-b border-foreground/8 px-4 py-4 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex min-w-0 items-center gap-3">
                <label htmlFor="photoFileInput" className="group relative shrink-0 cursor-pointer">
                  <UserAvatar initials={initials} src={photoPreviewUrl || undefined} size="md" />
                  <div className="absolute inset-0 flex items-center justify-center rounded-full bg-foreground/35 opacity-0 transition-opacity group-hover:opacity-100">
                    <Camera className="h-4 w-4 text-primary-foreground" />
                  </div>
                </label>
                <input
                  id="photoFileInput"
                  type="file"
                  name="photo_file"
                  accept=".png,.jpg,.jpeg,.webp,.gif,image/png,image/jpeg,image/webp,image/gif"
                  hidden
                  onChange={handleFileChange}
                />
                <div className="min-w-0">
                  <h2 className="truncate font-display text-lg font-bold leading-tight">
                    {profileTitle}
                  </h2>
                  <p className="mt-1 truncate text-xs font-medium text-muted-foreground">
                    {profileSubtitle}
                  </p>
                </div>
              </div>
              <div className="flex shrink-0 flex-wrap gap-2">
                <button
                  type="button"
                  onClick={handleDeletePhoto}
                  className="inline-flex h-9 items-center gap-1.5 rounded-md border border-destructive/20 px-3 text-xs font-bold text-destructive hover:bg-destructive/5"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                  Delete photo
                </button>
                {props.changePasswordUrl ? (
                  <button
                    type="button"
                    onClick={() => setPasswordModalOpen(true)}
                    className="inline-flex h-9 items-center gap-1.5 rounded-md border border-foreground/10 px-3 text-xs font-bold hover:bg-muted"
                  >
                    <KeyRound className="h-3.5 w-3.5" />
                    Password
                  </button>
                ) : null}
              </div>
            </div>

            <div className="grid gap-4 px-4 py-4 lg:grid-cols-[minmax(0,1fr),minmax(18rem,0.45fr)]">
              <div className="space-y-4">
                <div>
                  <h3 className="flex items-center gap-2 text-sm font-bold">
                    <User className="h-4 w-4 text-info" />
                    Student Info
                  </h3>
                  <div className="mt-3 grid gap-2 sm:grid-cols-3">
                    <ReadOnlyField label="Surname and Name" value={`${student.surname || ""} ${student.name || ""}`.trim() || "-"} />
                    <ReadOnlyField label="Username" value={student.student_id || "-"} />
                    <ReadOnlyField label="Group" value={student.group || "-"} />
                  </div>
                </div>

                <label className="block">
                  <span className="mb-1.5 block text-[10px] font-bold uppercase tracking-wide text-muted-foreground">Teacher</span>
                  <select
                    name="teacher_name"
                    defaultValue={student.teacher_name || "__none__"}
                    className="h-10 w-full rounded-md border border-foreground/10 bg-background px-3 text-sm outline-none focus:border-foreground/30"
                  >
                    <option value="__none__">No teacher</option>
                    {(props.teacherNameOptions || []).map((teacherName) => (
                      <option key={teacherName} value={teacherName}>
                        {teacherName}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="block">
                  <span className="mb-1.5 flex items-center gap-2 text-[10px] font-bold uppercase tracking-wide text-muted-foreground">
                    <FileText className="h-3.5 w-3.5" />
                    Description
                  </span>
                  <textarea
                    name="profile_description"
                    defaultValue={student.profile_description || ""}
                    rows={5}
                    placeholder="Enter student profile description..."
                    className="w-full resize-none rounded-md border border-foreground/10 bg-background px-3 py-2.5 text-sm outline-none focus:border-foreground/30"
                  />
                </label>
              </div>

              <aside className="space-y-4 rounded-md border border-foreground/8 bg-background p-3">
                <div>
                  <h3 className="flex items-center gap-2 text-sm font-bold">
                    <Users className="h-4 w-4 text-muted-foreground" />
                    Classmates
                  </h3>
                  {student.classmates?.length ? (
                    <ul className="mt-3 flex flex-col gap-1.5">
                      {student.classmates.map((classmate) => (
                        <li key={classmate} className="rounded-md bg-muted px-3 py-2 text-xs font-semibold">
                          {classmate}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="mt-3 text-xs text-muted-foreground">No classmates data.</p>
                  )}
                </div>
              </aside>
            </div>
          </section>

          <div className="flex justify-end">
            <button className="inline-flex h-10 items-center gap-2 rounded-md bg-primary px-5 text-sm font-bold text-primary-foreground hover:opacity-90">
              <Save className="h-4 w-4" />
              Save Profile
            </button>
          </div>
        </form>
      </div>

      {passwordModalOpen && props.changePasswordUrl ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/50"
          style={modalInsetStyle}
          onClick={(event) => {
            if (event.target === event.currentTarget) {
              setPasswordModalOpen(false);
            }
          }}
        >
          <div className="max-h-full w-full max-w-sm overflow-y-auto rounded-2xl bg-surface p-5 shadow-card-hover">
            <h3 className="font-display text-base font-bold">Change Password</h3>
            <form action={props.changePasswordUrl} method="post" className="mt-4 space-y-3">
              <input type="hidden" name="csrf_token" value={props.csrfToken || ""} />
              <label className="block">
                <span className="mb-1.5 block text-[10px] font-bold uppercase tracking-wide text-muted-foreground">New Password</span>
                <input
                  type="password"
                  name="new_password"
                  autoComplete="new-password"
                  minLength={6}
                  required
                  placeholder="Enter new password"
                  className="w-full rounded-xl border-2 border-foreground/10 bg-surface px-4 py-2.5 text-sm outline-none focus:border-foreground/30"
                />
              </label>
              <label className="block">
                <span className="mb-1.5 block text-[10px] font-bold uppercase tracking-wide text-muted-foreground">Confirm Password</span>
                <input
                  type="password"
                  name="confirm_password"
                  autoComplete="new-password"
                  minLength={6}
                  required
                  placeholder="Confirm new password"
                  className="w-full rounded-xl border-2 border-foreground/10 bg-surface px-4 py-2.5 text-sm outline-none focus:border-foreground/30"
                />
              </label>
              <div className="mt-4 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setPasswordModalOpen(false)}
                  className="rounded-lg border-2 border-foreground/10 px-4 py-2 text-sm font-bold hover:bg-muted"
                >
                  Cancel
                </button>
                <button type="submit" className="rounded-lg bg-warning px-4 py-2 text-sm font-bold text-warning-foreground">
                  Save
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </>
  );

  if (isAdminEmbed) {
    return (
      <AdminEmbedLayout
        title="Edit Student Profile"
        subtitle={profileTitle}
        badge={student.group || "Profile"}
      >
        {pageContent}
      </AdminEmbedLayout>
    );
  }

  return (
    <TelegramLayout
      topbar={
        <Topbar
          backUrl={props.backUrl}
          title="Edit Student Profile"
          subtitle={profileTitle}
          rightContent={
            props.viewDashboardUrl ? (
              <a
                href={props.viewDashboardUrl}
                className="rounded-lg border-2 border-foreground/10 px-3 py-1.5 text-[11px] font-bold hover:bg-muted"
              >
                View Dashboard
              </a>
            ) : null
          }
        />
      }
    >
      {pageContent}
    </TelegramLayout>
  );
}

function ReadOnlyField({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-foreground/8 bg-background px-3 py-2.5">
      <span className="block text-[10px] font-bold uppercase tracking-wide text-muted-foreground">{label}</span>
      <p className="mt-1 truncate text-sm font-semibold">{value}</p>
    </div>
  );
}
