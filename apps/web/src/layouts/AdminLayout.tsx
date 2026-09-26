import { NavLink, Outlet } from "react-router-dom";

const nav = [
  { to: "/admin", label: "Overview", end: true },
  { to: "/admin/scraping", label: "Scraping" },
  { to: "/admin/feedback", label: "Feedback" },
  { to: "/admin/reports", label: "Reports" },
  { to: "/admin/users", label: "Users" },
  { to: "/admin/analytics", label: "Analytics" },
];

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `rounded-xl px-3 py-2 text-sm font-medium transition-all duration-200 ${
    isActive
      ? "bg-brand-600 text-white shadow-sm shadow-brand-600/30"
      : "text-slate-300 hover:bg-white/10 hover:text-white"
  }`;

export function AdminLayout() {
  return (
    <div className="flex min-h-screen bg-surface">
      <aside className="hidden w-60 shrink-0 flex-col bg-brand-900 p-4 text-white md:flex">
        <NavLink to="/admin" className="mb-6 flex items-center px-2">
          <img src="/joblik-logo-header.png" alt="JOBLIK AI" className="h-9 w-auto brightness-0 invert" />
        </NavLink>
        <p className="mb-3 px-3 text-[10px] font-semibold uppercase tracking-widest text-brand-200">Admin</p>
        <nav className="flex flex-col gap-1">
          {nav.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.end} className={linkClass}>
              {item.label}
            </NavLink>
          ))}
        </nav>
        <NavLink
          to="/"
          className="mt-auto px-3 pt-8 text-xs text-brand-200 transition-colors hover:text-white"
        >
          ← Back to site
        </NavLink>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="border-b border-slate-200/80 bg-white/90 px-4 py-3 backdrop-blur-md md:hidden">
          <div className="flex items-center gap-2">
            <img src="/joblik-logo-header.png" alt="JOBLIK AI" className="h-8 w-auto" />
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-400">Admin</span>
          </div>
          <nav className="mt-2 flex gap-1 overflow-x-auto pb-1">
            {nav.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  `whitespace-nowrap rounded-xl px-2.5 py-1.5 text-xs font-medium transition-colors ${
                    isActive ? "bg-brand-600 text-white" : "bg-slate-100 text-slate-600"
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
        </header>
        <main className="flex-1 p-4 sm:p-8">
          <div className="jl-fade-up mx-auto max-w-[1440px]">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
