import { NavLink, Outlet } from "react-router-dom";

import { SiteFooter } from "../components/SiteFooter.js";

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `rounded-xl px-3 py-2 text-sm font-medium transition-colors duration-200 ${
    isActive ? "bg-brand-50 text-brand-700" : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
  }`;

export function PublicLayout() {
  return (
    <div className="flex min-h-screen flex-col bg-surface">
      <header className="sticky top-0 z-40 border-b border-slate-200/80 bg-white/95 backdrop-blur-md">
        <div className="mx-auto flex h-14 w-full max-w-[1440px] items-center justify-between px-4 sm:h-16 sm:px-6 lg:px-10">
          <NavLink to="/" className="flex items-center transition-opacity hover:opacity-90">
            <img src="/joblik-logo-header.png" alt="JOBLIK AI" className="h-8 w-auto sm:h-9" />
          </NavLink>
          <nav className="flex items-center gap-1.5 sm:gap-2">
            <NavLink to="/login" className={linkClass}>
              Log in
            </NavLink>
            <NavLink
              to="/signup"
              className="rounded-xl bg-brand-600 px-3.5 py-2 text-sm font-semibold text-white shadow-sm shadow-brand-600/20 transition-all duration-200 hover:bg-brand-700 hover:shadow-md hover:shadow-brand-600/25"
            >
              Sign up
            </NavLink>
          </nav>
        </div>
      </header>
      <main className="flex-1">
        <Outlet />
      </main>
      <SiteFooter />
    </div>
  );
}
