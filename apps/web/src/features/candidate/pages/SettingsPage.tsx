import { useState } from "react";
import { Link } from "react-router-dom";

import { Button } from "../../../components/Button.js";
import { Card, CardHeader } from "../../../components/Card.js";
import { PageHeader } from "../../../components/PageHeader.js";
import { useToast } from "../../../components/Toast.js";
import { fieldClass } from "../../candidate-profile/components/OnboardingChrome.js";

const TABS = ["Profile", "Preferences", "CV", "Account"] as const;

export function SettingsPage() {
  const [tab, setTab] = useState<(typeof TABS)[number]>("Profile");
  const toast = useToast();

  return (
    <div className="jl-fade-up">
      <PageHeader title="Settings" description="Keep your profile and preferences accurate as things change." />

      <div className="mb-6 flex flex-wrap gap-2" role="tablist">
        {TABS.map((t) => (
          <button
            key={t}
            type="button"
            role="tab"
            aria-selected={tab === t}
            onClick={() => setTab(t)}
            className={`cursor-pointer rounded-xl px-4 py-2 text-sm font-medium transition-all duration-200 ${
              tab === t
                ? "bg-brand-600 text-white shadow-sm shadow-brand-600/25"
                : "bg-white text-slate-600 ring-1 ring-slate-200 hover:bg-brand-50 hover:text-brand-700"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === "Profile" ? (
        <Card>
          <CardHeader title="Personal info" description="Same fields as onboarding — edit anytime." />
          <div className="grid gap-4 sm:grid-cols-2">
            {["First name", "Last name", "Email", "Phone", "City", "Country"].map((label) => (
              <label key={label} className="block text-sm">
                <span className="mb-1.5 block font-medium text-slate-700">{label}</span>
                <input
                  className={fieldClass}
                  defaultValue={label === "Email" ? "you@example.com" : ""}
                />
              </label>
            ))}
          </div>
          <Button className="mt-6 font-semibold" onClick={() => toast("Profile saved")}>
            Save changes
          </Button>
        </Card>
      ) : null}

      {tab === "Preferences" ? (
        <Card>
          <CardHeader title="Job preferences" description="Work mode, contract type, and target roles." />
          <p className="text-sm text-slate-500">
            For the full preference survey used after CV review, open{" "}
            <Link to="/onboarding/upload-cv" className="font-medium text-brand-600 hover:underline">
              onboarding
            </Link>{" "}
            or re-run the survey from your confirmed profile.
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            {["Remote", "Hybrid", "On-site", "CDI", "CDD", "Freelance"].map((chip) => (
              <button
                key={chip}
                type="button"
                className="cursor-pointer rounded-full bg-brand-50 px-3 py-1 text-sm font-medium text-brand-700 ring-1 ring-brand-100 transition-colors hover:bg-brand-100"
              >
                {chip}
              </button>
            ))}
          </div>
          <Button className="mt-6 font-semibold" onClick={() => toast("Preferences saved")}>
            Save preferences
          </Button>
        </Card>
      ) : null}

      {tab === "CV" ? (
        <Card>
          <CardHeader title="CV" description="Re-upload to refresh extracted skills and experience." />
          <Link to="/onboarding/upload-cv">
            <Button className="font-semibold">Re-upload CV</Button>
          </Link>
        </Card>
      ) : null}

      {tab === "Account" ? (
        <Card>
          <CardHeader title="Account & security" />
          <div className="space-y-3">
            <Button variant="secondary" onClick={() => toast("Password change coming soon")}>
              Change password
            </Button>
            <label className="flex items-center gap-3 text-sm text-slate-700">
              <input
                type="checkbox"
                defaultChecked
                className="size-4 rounded border-slate-300 text-brand-600 focus:ring-brand-600"
              />
              Email me a weekly digest of new matches
            </label>
            <Button variant="danger" onClick={() => toast("Account deletion requires confirmation — coming soon")}>
              Delete account
            </Button>
          </div>
        </Card>
      ) : null}
    </div>
  );
}
