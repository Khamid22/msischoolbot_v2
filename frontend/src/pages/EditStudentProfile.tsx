import { ChangeEvent, useState } from "react";
import { Camera, Trash2, User } from "lucide-react";
import { TelegramLayout, Topbar } from "@/components/TelegramLayout";
import { ChartCard } from "@/components/ChartCard";
import { UserAvatar } from "@/components/Avatar";
import { FormAlert } from "@/components/PortalCard";

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
  viewDashboardUrl?: string;
  backUrl?: string;
}

export default function EditStudentProfile(props: EditStudentProfileProps) {
  const student = props.student || { id: 0 };
  const [photoPreviewUrl, setPhotoPreviewUrl] = useState(student.photo_url || "");
  const initials = `${String(student.surname || "").slice(0, 1)}${String(student.name || "").slice(0, 1)}`.trim() || "ST";

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

  return (
    <TelegramLayout
      topbar={
        <Topbar
          backUrl={props.backUrl}
          title="Edit Student Profile"
          subtitle={student.full_name || ""}
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
      <div className="space-y-4 animate-in">
        {props.authError ? <FormAlert kind="error">{props.authError}</FormAlert> : null}
        {props.adminNotice ? <FormAlert kind="notice">{props.adminNotice}</FormAlert> : null}

        <form action={props.saveUrl} method="post" encType="multipart/form-data" className="space-y-4">
          <input type="hidden" name="csrf_token" value={props.csrfToken || ""} />
          <input type="hidden" name="photo_url" value={student.photo_url || ""} />
          <input type="hidden" id="removePhotoInput" name="remove_photo" value="0" />

          <ChartCard title="Student Info" icon={<User className="h-4 w-4 text-info" />}>
            <div className="flex flex-col gap-6 sm:flex-row">
              <div className="flex flex-col items-center gap-3">
                <span className="text-[10px] font-bold uppercase tracking-wide text-muted-foreground">Profile Picture</span>
                <label htmlFor="photoFileInput" className="group relative cursor-pointer">
                  <UserAvatar initials={initials} src={photoPreviewUrl || undefined} size="lg" />
                  <div className="absolute inset-0 flex items-center justify-center rounded-full bg-foreground/30 opacity-0 transition-opacity group-hover:opacity-100">
                    <Camera className="h-5 w-5 text-primary-foreground" />
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
                <button type="button" onClick={handleDeletePhoto} className="flex items-center gap-1 text-xs text-destructive hover:underline">
                  <Trash2 className="h-3 w-3" />
                  Delete photo
                </button>
              </div>

              <div className="grid flex-1 grid-cols-1 gap-3 sm:grid-cols-2">
                {[
                  { label: "Surname and Name", value: `${student.surname || ""} ${student.name || ""}`.trim() || "-" },
                  { label: "Username", value: student.student_id || "-" },
                  { label: "Password", value: student.password || "-" },
                  { label: "Group", value: student.group || "-" },
                ].map((item) => (
                  <div key={item.label}>
                    <span className="text-[10px] font-bold uppercase tracking-wide text-muted-foreground">{item.label}</span>
                    <p className="mt-0.5 text-sm font-medium">{item.value}</p>
                  </div>
                ))}
                <div className="sm:col-span-2">
                  <label className="block">
                    <span className="mb-1.5 block text-[10px] font-bold uppercase tracking-wide text-muted-foreground">Teacher</span>
                    <select
                      name="teacher_name"
                      defaultValue={student.teacher_name || "__none__"}
                      className="w-full rounded-xl border-2 border-foreground/10 bg-surface px-4 py-2.5 text-sm outline-none focus:border-foreground/30"
                    >
                      <option value="__none__">No teacher</option>
                      {(props.teacherNameOptions || []).map((teacherName) => (
                        <option key={teacherName} value={teacherName}>
                          {teacherName}
                        </option>
                      ))}
                    </select>
                  </label>
                </div>
              </div>
            </div>
          </ChartCard>

          <ChartCard title="Classmates" icon={<User className="h-4 w-4 text-muted-foreground" />}>
            {student.classmates?.length ? (
              <div className="flex flex-wrap gap-2">
                {student.classmates.map((classmate) => (
                  <span key={classmate} className="rounded-full bg-muted px-3 py-1 text-xs font-medium">
                    {classmate}
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-xs text-muted-foreground">No classmates data.</p>
            )}
          </ChartCard>

          <ChartCard title="Description" icon={<User className="h-4 w-4 text-muted-foreground" />}>
            <textarea
              name="profile_description"
              defaultValue={student.profile_description || ""}
              rows={4}
              placeholder="Enter student profile description..."
              className="w-full resize-none rounded-xl border-2 border-foreground/10 bg-surface px-4 py-3 text-sm outline-none focus:border-foreground/30"
            />
          </ChartCard>

          <button className="w-full rounded-xl bg-primary px-6 py-3.5 text-sm font-bold text-primary-foreground shadow-neo transition-all active:translate-x-[1px] active:translate-y-[1px] active:shadow-none">
            Save changes
          </button>
        </form>
      </div>
    </TelegramLayout>
  );
}
