import { Link, Outlet } from "react-router-dom";

export function OnboardingLayout() {
  return (
    <div className="flex min-h-screen flex-col bg-surface">
      <header className="border-b border-slate-200/80 bg-white">
        <div className="flex w-full items-center justify-between px-4 py-2.5 sm:px-6 lg:px-8">
          <Link to="/" className="flex items-center">
            <img src="/joblik-logo.png" alt="JOBLIK AI" className="h-9 w-auto sm:h-10" />
          </Link>

          <div className="flex items-center gap-4 sm:gap-6">
            <button
              type="button"
              className="inline-flex cursor-pointer items-center gap-1.5 text-sm font-medium text-slate-500 hover:text-brand-600"
            >
              <span className="inline-flex size-5 items-center justify-center rounded-full border border-slate-300 text-xs">
                ?
              </span>
              <span className="hidden sm:inline">Need help?</span>
            </button>

            <button
              type="button"
              className="inline-flex cursor-pointer items-center gap-2 rounded-full py-1 pl-1 pr-2 hover:bg-slate-50"
            >
              <span className="inline-flex size-8 items-center justify-center rounded-full bg-brand-600 text-xs font-semibold text-white">
                AM
              </span>
              <span className="hidden text-sm font-medium text-slate-700 sm:inline">Alex Morgan</span>
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true" className="text-slate-400">
                <path d="M3 4.5L6 7.5L9 4.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
              </svg>
            </button>
          </div>
        </div>
      </header>

      <main className="flex min-h-0 flex-1 flex-col">
        <Outlet />
      </main>
    </div>
  );
}
