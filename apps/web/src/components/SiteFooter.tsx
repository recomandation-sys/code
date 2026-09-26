import { Link } from "react-router-dom";

/** Slim site footer — contact + legal, shared by public + candidate shells */
export function SiteFooter() {
  return (
    <footer className="mt-auto border-t border-slate-200/90 bg-white">
      <div className="mx-auto flex w-full max-w-[1440px] flex-col gap-4 px-4 py-5 sm:flex-row sm:items-center sm:justify-between sm:px-6 lg:px-10">
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
          <Link to="/" className="flex items-center">
            <img src="/joblik-logo-header.png" alt="JOBLIK AI" className="h-7 w-auto" />
          </Link>
          <span className="hidden h-4 w-px bg-slate-200 sm:block" aria-hidden="true" />
          <p className="text-xs text-slate-500">Careers, matched with care</p>
        </div>

        <nav className="flex flex-wrap items-center gap-x-5 gap-y-2 text-xs font-medium text-slate-600" aria-label="Footer">
          <a href="mailto:contact@joblik.ai" className="transition-colors hover:text-brand-600">
            Contact us
          </a>
          <Link to="/onboarding/privacy" className="transition-colors hover:text-brand-600">
            Privacy
          </Link>
          <Link to="/onboarding/upload-cv" className="transition-colors hover:text-brand-600">
            Upload CV
          </Link>
          <a href="mailto:support@joblik.ai" className="transition-colors hover:text-brand-600">
            Support
          </a>
        </nav>
      </div>
    </footer>
  );
}
