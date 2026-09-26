import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { Button } from "../../../components/Button.js";
import { fieldClass } from "../../candidate-profile/components/OnboardingChrome.js";

export function LoginPage() {
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);

  function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const data = new FormData(e.currentTarget);
    const email = String(data.get("email") ?? "");
    const password = String(data.get("password") ?? "");
    if (!email.includes("@") || password.length < 8) {
      setError("Check your email and password (8+ characters).");
      return;
    }
    setError(null);
    // ponytail: UI-only auth until real auth service exists
    navigate("/dashboard");
  }

  return (
    <div className="jl-mesh relative flex min-h-[calc(100vh-8rem)] items-center justify-center px-4 py-12 sm:px-6">
      <div className="jl-fade-up w-full max-w-md">
        <div className="mb-6 text-center">
          <img src="/joblik-logo.png" alt="JOBLIK AI" className="mx-auto h-12 w-auto" />
          <h1 className="mt-5 text-2xl font-bold tracking-tight text-slate-900">Welcome back</h1>
          <p className="mt-1.5 text-sm text-slate-500">Check your latest matches in a few seconds.</p>
        </div>

        <form
          onSubmit={onSubmit}
          noValidate
          className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-7"
        >
          <label className="block text-sm">
            <span className="mb-1.5 block font-medium text-slate-700">Email</span>
            <input name="email" type="email" autoComplete="email" required className={fieldClass} />
          </label>
          <label className="mt-4 block text-sm">
            <span className="mb-1.5 block font-medium text-slate-700">Password</span>
            <input
              name="password"
              type="password"
              autoComplete="current-password"
              required
              className={fieldClass}
            />
          </label>
          {error ? <p className="mt-3 text-sm text-danger-600">{error}</p> : null}
          <Button type="submit" className="mt-5 w-full py-2.5 font-semibold shadow-sm shadow-brand-600/20">
            Log in
          </Button>
          <p className="mt-3 text-center text-sm">
            <button
              type="button"
              className="cursor-pointer text-slate-400 transition-colors hover:text-brand-600"
              onClick={() => setError("Password reset coming soon.")}
            >
              Forgot password?
            </button>
          </p>
        </form>

        <p className="mt-5 text-center text-sm text-slate-500">
          New here?{" "}
          <Link to="/signup" className="font-semibold text-brand-600 hover:underline">
            Sign up
          </Link>
        </p>
      </div>
    </div>
  );
}
