import { FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { Button } from "../../../components/Button.js";
import { fieldClass } from "../../candidate-profile/components/OnboardingChrome.js";

export function AdminLoginPage() {
  const navigate = useNavigate();

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    // ponytail: UI-only admin gate until real auth + 2FA
    navigate("/admin");
  }

  return (
    <div className="jl-mesh flex min-h-screen items-center justify-center px-4 py-12 sm:px-6">
      <div className="jl-fade-up w-full max-w-md">
        <div className="mb-6 text-center">
          <img src="/joblik-logo.png" alt="JOBLIK AI" className="mx-auto h-12 w-auto" />
          <p className="mt-2 text-[10px] font-semibold uppercase tracking-widest text-brand-600">Admin</p>
          <h1 className="mt-3 text-2xl font-bold tracking-tight text-slate-900">Staff sign in</h1>
          <p className="mt-1.5 text-sm text-slate-500">Staff access only. No public signup.</p>
        </div>

        <form
          onSubmit={onSubmit}
          className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-7"
        >
          <label className="block text-sm">
            <span className="mb-1.5 block font-medium text-slate-700">Work email</span>
            <input required type="email" className={fieldClass} autoComplete="username" />
          </label>
          <label className="mt-4 block text-sm">
            <span className="mb-1.5 block font-medium text-slate-700">Password</span>
            <input required type="password" className={fieldClass} autoComplete="current-password" />
          </label>
          <Button type="submit" className="mt-5 w-full py-2.5 font-semibold shadow-sm shadow-brand-600/20">
            Sign in
          </Button>
        </form>

        <p className="mt-5 text-center text-sm text-slate-500">
          <Link to="/" className="font-semibold text-brand-600 hover:underline">
            ← Back to site
          </Link>
        </p>
      </div>
    </div>
  );
}
