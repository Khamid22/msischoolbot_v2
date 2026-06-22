import { Lock, User } from "lucide-react";
import { CenteredPage, FormAlert } from "@/shared/ui/PortalCard";

interface LoginPageProps {
  authError?: string;
  authLoginInput?: string;
  submitUrl?: string;
  csrfToken?: string;
}

export default function LoginPage(props: LoginPageProps) {
  return (
    <CenteredPage title="MSI School Portal" subtitle="Login to continue">
      {props.authError ? <FormAlert kind="error">{props.authError}</FormAlert> : null}

      <form action={props.submitUrl || "/login"} method="post" className="space-y-4">
        <input type="hidden" name="csrf_token" value={props.csrfToken || ""} />
        <input type="hidden" id="loginTelegramInitData" name="init_data" defaultValue="" />

        <label className="block">
          <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Login
          </span>
          <div className="relative">
            <User className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <input
              type="text"
              name="login"
              defaultValue={props.authLoginInput || ""}
              placeholder="Staff login or student code"
              autoComplete="username"
              required
              className="w-full rounded-xl border-2 border-foreground/10 bg-surface py-3 pl-10 pr-4 text-sm font-medium outline-none transition-colors focus:border-foreground/30"
            />
          </div>
        </label>

        <label className="block">
          <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Password
          </span>
          <div className="relative">
            <Lock className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <input
              type="password"
              name="password"
              placeholder="Enter password"
              autoComplete="current-password"
              required
              className="w-full rounded-xl border-2 border-foreground/10 bg-surface py-3 pl-10 pr-4 text-sm font-medium outline-none transition-colors focus:border-foreground/30"
            />
          </div>
        </label>

        <button
          type="submit"
          className="w-full rounded-xl bg-primary px-6 py-3.5 text-sm font-bold text-primary-foreground shadow-neo transition-all active:translate-x-[1px] active:translate-y-[1px] active:shadow-none"
        >
          Sign In
        </button>
      </form>
    </CenteredPage>
  );
}
