import { useEffect, useRef, useState, type FormEvent } from "react";
import { X } from "lucide-react";
import { type ParentRow } from "./types";
import { asString } from "../../shared";

export interface ParentProfilePayload {
  login?: string;
  password?: string;
  display_name: string;
  phone: string;
  email: string;
  telegram_username: string;
  notes: string;
}

const labelClass = "mb-1 block text-[11px] font-bold uppercase tracking-wide text-muted-foreground";
const inputClass =
  "h-10 w-full rounded-lg border border-foreground/10 bg-background px-3 text-sm outline-none focus:border-foreground/30";

export function ParentFormModal({
  mode,
  parent,
  saving,
  error,
  onClose,
  onSubmit,
}: {
  mode: "create" | "edit";
  parent?: ParentRow | null;
  saving: boolean;
  error: string;
  onClose: () => void;
  onSubmit: (payload: ParentProfilePayload) => void;
}) {
  const isEdit = mode === "edit";
  const [login, setLogin] = useState(isEdit ? asString(parent?.login) : "");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState(asString(parent?.display_name));
  const [phone, setPhone] = useState(asString(parent?.phone));
  const [email, setEmail] = useState(asString(parent?.email));
  const [telegram, setTelegram] = useState(asString(parent?.telegram_username));
  const [notes, setNotes] = useState(asString(parent?.notes));
  const firstRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    firstRef.current?.focus();
  }, []);

  const createInvalid = !isEdit && (login.trim().length < 3 || password.length < 6);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (saving || createInvalid) return;
    const payload: ParentProfilePayload = {
      display_name: displayName.trim(),
      phone: phone.trim(),
      email: email.trim(),
      telegram_username: telegram.trim().replace(/^@/, ""),
      notes: notes.trim(),
    };
    if (!isEdit) {
      payload.login = login.trim();
      payload.password = password;
    }
    onSubmit(payload);
  }

  return (
    <div className="fixed inset-0 z-[75] flex items-center justify-center bg-foreground/60 p-4" onClick={onClose}>
      <div
        className="flex max-h-[90dvh] w-full max-w-md flex-col overflow-hidden rounded-xl bg-surface shadow-card-hover"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex shrink-0 items-center justify-between border-b border-foreground/8 px-4 py-3">
          <div>
            <h3 className="text-sm font-bold">{isEdit ? "Edit parent" : "Add parent"}</h3>
            <p className="text-xs text-muted-foreground">
              {isEdit ? "Update contact details and notes." : "Create a parent account with a temporary password."}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="flex h-8 w-8 items-center justify-center rounded-lg hover:bg-muted"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="min-h-0 flex-1 overflow-y-auto">
          <div className="space-y-3 p-4">
            {error ? (
              <div className="rounded-lg border border-destructive/20 bg-destructive/10 px-3 py-2 text-sm font-semibold text-destructive">
                {error}
              </div>
            ) : null}

            {!isEdit ? (
              <div className="grid gap-3 sm:grid-cols-2">
                <label className="block">
                  <span className={labelClass}>Login *</span>
                  <input ref={firstRef} value={login} onChange={(e) => setLogin(e.target.value)} className={inputClass} placeholder="parent-login" />
                </label>
                <label className="block">
                  <span className={labelClass}>Temp password *</span>
                  <input value={password} onChange={(e) => setPassword(e.target.value)} type="text" className={inputClass} placeholder="At least 6 characters" />
                </label>
              </div>
            ) : null}

            <label className="block">
              <span className={labelClass}>Full name</span>
              <input
                ref={isEdit ? firstRef : undefined}
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                className={inputClass}
                placeholder="Parent / guardian name"
              />
            </label>

            <div className="grid gap-3 sm:grid-cols-2">
              <label className="block">
                <span className={labelClass}>Phone</span>
                <input value={phone} onChange={(e) => setPhone(e.target.value)} className={inputClass} placeholder="+998 ..." />
              </label>
              <label className="block">
                <span className={labelClass}>Telegram username</span>
                <input value={telegram} onChange={(e) => setTelegram(e.target.value)} className={inputClass} placeholder="username" />
              </label>
            </div>

            <label className="block">
              <span className={labelClass}>Email</span>
              <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" className={inputClass} placeholder="name@example.com" />
            </label>

            <label className="block">
              <span className={labelClass}>Notes</span>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={3}
                className="w-full resize-none rounded-lg border border-foreground/10 bg-background px-3 py-2 text-sm outline-none focus:border-foreground/30"
                placeholder="Internal notes (optional)"
              />
            </label>
          </div>

          <div className="flex shrink-0 gap-2 border-t border-foreground/8 px-4 py-3">
            <button type="button" onClick={onClose} className="h-10 flex-1 rounded-lg border border-foreground/10 text-sm font-bold hover:bg-muted">
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving || createInvalid}
              className="h-10 flex-1 rounded-lg bg-primary text-sm font-bold text-primary-foreground disabled:opacity-50"
            >
              {saving ? "Saving..." : isEdit ? "Save changes" : "Add parent"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
