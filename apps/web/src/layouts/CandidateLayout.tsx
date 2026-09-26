import { NavLink, Outlet } from "react-router-dom";

import { SiteFooter } from "../components/SiteFooter.js";

const nav = [
  { to: "/dashboard", label: "Home" },
  { to: "/jobs", label: "Jobs" },
  { to: "/positions", label: "Positions" },
  { to: "/skills-gap", label: "Skills gap" },
  { to: "/my-jobs", label: "My jobs" },
  { to: "/feedback", label: "Feedback" },
  { to: "/settings", label: "Settings" },
];

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `shrink-0 whitespace-nowrap rounded-lg px-2.5 py-1.5 text-sm font-medium transition-all duration-200 ${
    isActive
      ? "bg-brand-600 text-white shadow-sm shadow-brand-600/25"
      : "text-slate-600 hover:bg-brand-50 hover:text-brand-700"
  }`;

export function CandidateLayout() {
  const username = typeof sessionStorage !== "undefined" ? sessionStorage.getItem("joblik:username") : null;
  const trimmed = username?.trim() || "";
  const parts = trimmed.split(/[\s._-]+/).filter(Boolean);
  const initials =
    parts.length >= 2
      ? `${parts[0]![0]}${parts[1]![0]}`.toUpperCase()
      : trimmed.slice(0, 2).toUpperCase() || "JL";

  return (
    <div className="flex min-h-screen flex-col bg-surface">
      <header className="sticky top-0 z-40 border-b border-slate-200/80 bg-white/95 backdrop-blur-md">
        <div className="mx-auto flex h-14 w-full max-w-[1440px] items-center gap-3 px-4 sm:h-16 sm:gap-4 sm:px-6 lg:px-10">
          <NavLink to="/dashboard" className="shrink-0 transition-opacity hover:opacity-90">
            <img src="/joblik-logo-header.png" alt="JOBLIK AI" className="h-8 w-auto sm:h-9" />
          </NavLink>

          <nav
            className="flex min-w-0 flex-1 items-center gap-0.5 overflow-x-auto py-1 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
            aria-label="Candidate"
          >
            {nav.map((item) => (
              <NavLink key={item.to} to={item.to} className={linkClass} end={item.to === "/dashboard"}>
                {item.label}
              </NavLink>
            ))}
          </nav>

          <div className="flex shrink-0 items-center gap-2 sm:gap-3">
            <NavLink
              to="/profile"
              className="hidden text-sm font-medium text-slate-500 transition-colors hover:text-brand-600 md:inline"
            >
              Profile
            </NavLink>
            <NavLink
              to="/settings"
              className="inline-flex size-9 items-center justify-center rounded-full bg-gradient-to-br from-brand-500 to-brand-700 text-xs font-semibold text-white shadow-sm shadow-brand-600/30 transition-transform duration-200 hover:scale-105"
              aria-label="Account settings"
            >
              {initials}
            </NavLink>
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-[1440px] flex-1 px-4 py-6 sm:px-6 sm:py-8 lg:px-10">
        <Outlet />
      </main>

      <SiteFooter />
    </div>
  );
}
