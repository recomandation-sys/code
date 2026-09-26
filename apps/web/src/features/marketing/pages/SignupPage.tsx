import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { Button } from "../../../components/Button.js";
import { fieldClass } from "../../candidate-profile/components/OnboardingChrome.js";

function strengthLabel(password: string) {
  if (password.length === 0) return null;
  if (password.length < 8) return { label: "Too short", className: "text-danger-600" };
  if (!/[A-Z]/.test(password) || !/[0-9]/.test(password))
    return { label: "Fair — add a number and uppercase", className: "text-warn-500" };
  return { label: "Strong", className: "text-accent-600" };
}

export function SignupPage() {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const strength = strengthLabel(password);

  function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const data = new FormData(e.currentTarget);
    const email = String(data.get("email") ?? "").trim();
    const name = username.trim();

    if (name.length < 3) {
      setError("Username must be at least 3 characters.");
      return;
    }
    if (!email.includes("@")) {
      setError("Enter a valid email.");
      return;
    }
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    if (password !== confirm) {
      setError("Passwords do not match.");
      return;
    }

    setError(null);
    // ponytail: UI-only auth until real auth service exists
    sessionStorage.setItem("joblik:username", name);
    navigate("/onboarding/upload-cv");
  }

  return (
    <div className="jl-mesh relative flex min-h-[calc(100vh-8rem)] items-center justify-center px-4 py-12 sm:px-6">
      <div className="jl-fade-up w-full max-w-md">
        <div className="mb-6 text-center">
          <img src="/joblik-logo.png" alt="JOBLIK AI" className="mx-auto h-12 w-auto" />
          <h1 className="mt-5 text-2xl font-bold tracking-tight text-slate-900">Create your account</h1>
          <p className="mt-1.5 text-sm text-slate-500">Then upload your CV — profile details come next.</p>
        </div>

        <form onSubmit={onSubmit} className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-7" noValidate>
          <label className="block text-sm">
            <span className="mb-1.5 block font-medium text-slate-700">Username</span>
            <input
              required
              name="username"
              type="text"
              autoComplete="username"
              minLength={3}
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className={fieldClass}
              placeholder="e.g. hazem.douzi"
            />
          </label>
          <label className="mt-4 block text-sm">
            <span className="mb-1.5 block font-medium text-slate-700">Email</span>
            <input required name="email" type="email" autoComplete="email" className={fieldClass} />
          </label>
          <label className="mt-4 block text-sm">
            <span className="mb-1.5 block font-medium text-slate-700">Password</span>
            <input
              required
              name="password"
              type="password"
              autoComplete="new-password"
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className={fieldClass}
            />
            {strength ? <p className={`mt-1.5 text-xs ${strength.className}`}>{strength.label}</p> : null}
          </label>
          <label className="mt-4 block text-sm">
            <span className="mb-1.5 block font-medium text-slate-700">Confirm password</span>
            <input
              required
              name="confirmPassword"
              type="password"
              autoComplete="new-password"
              minLength={8}
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              className={fieldClass}
            />
          </label>
          {error ? <p className="mt-3 text-sm text-danger-600">{error}</p> : null}
          <Button type="submit" className="mt-5 w-full py-2.5 font-semibold shadow-sm shadow-brand-600/20">
            Sign up
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <path d="M6 3l5 5-5 5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
            </svg>
          </Button>
        </form>

        <p className="mt-5 text-center text-sm text-slate-500">
          Already have an account?{" "}
          <Link to="/login" className="font-semibold text-brand-600 hover:underline">
            Log in
          </Link>
        </p>
      </div>
    </div>
  );
}
