import { Link } from "react-router-dom";

import { Button } from "../../../components/Button.js";

const STEPS = [
  {
    step: "1",
    title: "Upload your CV",
    body: "We extract experience and skills so you don’t retype everything.",
  },
  {
    step: "2",
    title: "Refine your profile",
    body: "Review personal info, education, and preferences in a guided flow.",
  },
  {
    step: "3",
    title: "Get matched",
    body: "See roles that fit — and the skills that close the gap.",
  },
] as const;

export function LandingPage() {
  return (
    <div>
      {/* Hero — one composition: brand + headline + CTA + visual */}
      <section className="jl-mesh relative overflow-hidden border-b border-slate-200/80">
        <div
          className="pointer-events-none absolute inset-0 opacity-[0.35]"
          style={{
            backgroundImage:
              "linear-gradient(to right, rgb(148 163 184 / 0.12) 1px, transparent 1px), linear-gradient(to bottom, rgb(148 163 184 / 0.12) 1px, transparent 1px)",
            backgroundSize: "48px 48px",
            maskImage: "radial-gradient(ellipse 70% 60% at 50% 40%, black, transparent)",
          }}
          aria-hidden="true"
        />

        <div className="relative mx-auto grid w-full max-w-[1440px] items-center gap-10 px-4 pb-16 pt-12 sm:px-6 sm:pb-20 sm:pt-16 lg:grid-cols-2 lg:gap-12 lg:px-10 lg:pb-24 lg:pt-20">
          <div className="text-center lg:text-left">
            <img
              src="/joblik-logo.png"
              alt="JOBLIK AI"
              className="jl-fade-up mx-auto h-14 w-auto sm:h-16 lg:mx-0 lg:h-[4.5rem]"
            />
            <h1 className="jl-fade-up jl-delay-1 mt-6 text-3xl font-bold tracking-tight text-slate-900 sm:text-4xl lg:text-[2.75rem] lg:leading-tight">
              Upload your CV.
              <span className="block text-brand-600">Get matched.</span>
            </h1>
            <p className="jl-fade-up jl-delay-2 mx-auto mt-4 max-w-md text-base text-slate-600 sm:text-lg lg:mx-0">
              AI-assisted profile building and job matching — built for Tunisian and regional talent.
            </p>
            <div className="jl-fade-up jl-delay-3 mt-8 flex flex-wrap items-center justify-center gap-3 lg:justify-start">
              <Link to="/signup">
                <Button className="px-6 py-2.5 text-base shadow-lg shadow-brand-600/25 transition-transform duration-200 hover:-translate-y-0.5">
                  Get started
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
                    <path d="M6 3l5 5-5 5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
                  </svg>
                </Button>
              </Link>
              <Link to="/login">
                <Button
                  variant="secondary"
                  className="border-brand-600 px-6 py-2.5 text-base font-semibold text-brand-600 hover:bg-brand-50"
                >
                  Log in
                </Button>
              </Link>
            </div>
          </div>

          <div className="jl-fade-in jl-delay-2 relative mx-auto w-full max-w-md lg:max-w-none">
            <div
              className="absolute -inset-6 rounded-[2rem] bg-gradient-to-br from-brand-200/40 via-transparent to-accent-100/30 blur-2xl"
              aria-hidden="true"
            />
            <img
              src="/cv-upload-hero.png"
              alt=""
              className="jl-float relative mx-auto h-auto w-full max-w-[320px] object-contain drop-shadow-xl sm:max-w-[380px] lg:max-w-[420px]"
            />
          </div>
        </div>
      </section>

      <section className="mx-auto w-full max-w-[1440px] px-4 py-16 sm:px-6 sm:py-20 lg:px-10">
        <h2 className="text-center text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">How it works</h2>
        <p className="mx-auto mt-2 max-w-lg text-center text-sm text-slate-500">
          The same guided flow you see after uploading a CV — clear steps, secure data.
        </p>
        <ol className="mt-12 grid gap-6 sm:grid-cols-3">
          {STEPS.map((item, i) => (
            <li
              key={item.step}
              className="group relative overflow-hidden rounded-2xl border border-slate-200 bg-white p-6 text-center shadow-sm transition-all duration-300 hover:-translate-y-1 hover:border-brand-200 hover:shadow-md hover:shadow-brand-600/10"
              style={{ animationDelay: `${0.08 * (i + 1)}s` }}
            >
              <span className="inline-flex size-10 items-center justify-center rounded-full bg-brand-600 text-sm font-bold text-white shadow-sm shadow-brand-600/30 transition-transform duration-300 group-hover:scale-110">
                {item.step}
              </span>
              <h3 className="mt-4 font-semibold text-slate-900">{item.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-slate-500">{item.body}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="border-t border-slate-200 bg-brand-600 px-4 py-14 text-center text-white sm:px-6">
        <img src="/joblik-logo-header.png" alt="" className="mx-auto mb-4 h-10 w-auto brightness-0 invert" />
        <h2 className="text-2xl font-bold tracking-tight sm:text-3xl">Ready to see your matches?</h2>
        <p className="mx-auto mt-2 max-w-md text-brand-100">
          Create an account and build your profile in a few guided steps.
        </p>
        <Link to="/signup" className="mt-8 inline-block">
          <Button
            variant="secondary"
            className="border-0 bg-white px-6 py-2.5 text-base font-semibold text-brand-700 shadow-lg transition-transform duration-200 hover:-translate-y-0.5 hover:bg-brand-50"
          >
            Upload your CV, get matched
          </Button>
        </Link>
      </section>
    </div>
  );
}
