import { Link, Navigate, useSearchParams } from "react-router-dom";

import { ApiClientError } from "../../../api/client.js";
import { Card, CardHeader } from "../../../components/Card.js";
import { PageHeader } from "../../../components/PageHeader.js";
import { formatMonths } from "../../../utils/format-duration.js";
import { useCandidateProfile } from "../hooks/useCandidateProfile.js";

export function ProfilePage() {
  const [searchParams] = useSearchParams();
  const profileId = searchParams.get("profileId") ?? undefined;
  const { data: profile, isLoading, isError, error } = useCandidateProfile(profileId);

  if (!profileId) {
    return (
      <div className="jl-fade-up mx-auto max-w-xl py-16 text-center">
        <img src="/joblik-logo.png" alt="" className="mx-auto h-12 w-auto opacity-90" />
        <p className="mt-4 text-sm text-slate-500">No profile to show yet.</p>
        <Link
          to="/onboarding/upload-cv"
          className="mt-4 inline-flex text-sm font-semibold text-brand-600 underline"
        >
          Build your profile
        </Link>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="py-16 text-center text-sm text-slate-500" role="status">
        Loading your profile…
      </div>
    );
  }

  if (isError || !profile) {
    const message = error instanceof ApiClientError ? error.message : "This profile could not be loaded.";
    return <div className="py-16 text-center text-sm text-danger-600">{message}</div>;
  }

  if (!profile.preferencesCompletedAt) {
    return <Navigate to={`/profile/survey?profileId=${profileId}`} replace />;
  }

  const locationLabel = profile.country ?? "";
  const contactLabel = [profile.email, profile.phone].filter(Boolean).join(" · ");

  return (
    <div className="jl-fade-up mx-auto max-w-3xl space-y-6">
      <PageHeader title="Your profile" description="Confirmed details from your CV and preferences." />

      <div className="flex items-start gap-3 rounded-2xl border border-accent-100 bg-accent-50 px-4 py-3 text-sm text-accent-600">
        <span className="mt-0.5 inline-flex size-5 shrink-0 items-center justify-center rounded-full bg-accent-500 text-[10px] font-bold text-white">
          ✓
        </span>
        Your profile has been saved.
      </div>

      <Card>
        <CardHeader
          title={profile.fullName}
          description={[contactLabel, locationLabel].filter(Boolean).join(" · ") || profile.email}
        />
        {profile.target.positions.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {profile.target.positions.map((p) => (
              <span
                key={p}
                className="rounded-full bg-brand-50 px-3 py-1 text-sm font-medium text-brand-700 ring-1 ring-brand-100"
              >
                {p}
              </span>
            ))}
          </div>
        ) : null}
      </Card>

      <Card>
        <CardHeader title="Job preferences" />
        <dl className="grid gap-3 text-sm sm:grid-cols-2">
          <div className="rounded-xl border border-slate-100 bg-slate-50/80 p-3">
            <dt className="text-xs font-semibold uppercase tracking-wide text-slate-400">Contract types</dt>
            <dd className="mt-1 font-medium text-slate-800">{profile.target.contractTypes.join(", ") || "—"}</dd>
          </div>
          <div className="rounded-xl border border-slate-100 bg-slate-50/80 p-3">
            <dt className="text-xs font-semibold uppercase tracking-wide text-slate-400">Work modes</dt>
            <dd className="mt-1 font-medium text-slate-800">{profile.target.workModes.join(", ") || "—"}</dd>
          </div>
          <div className="rounded-xl border border-slate-100 bg-slate-50/80 p-3">
            <dt className="text-xs font-semibold uppercase tracking-wide text-slate-400">Mobility</dt>
            <dd className="mt-1 font-medium text-slate-800">{profile.target.mobilityPreferences.join(", ") || "—"}</dd>
          </div>
          <div className="rounded-xl border border-slate-100 bg-slate-50/80 p-3">
            <dt className="text-xs font-semibold uppercase tracking-wide text-slate-400">Preferred countries</dt>
            <dd className="mt-1 font-medium text-slate-800">{profile.target.preferredCountries.join(", ") || "—"}</dd>
          </div>
        </dl>
      </Card>

      <Card>
        <CardHeader title="Experience" />
        <dl className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
          {(
            [
              ["Professional", profile.experience.professionalMonths],
              ["Internships", profile.experience.internshipMonths],
              ["Alternance", profile.experience.alternanceMonths],
              ["Freelance", profile.experience.freelanceMonths],
            ] as const
          ).map(([label, months]) => (
            <div key={label} className="rounded-xl border border-slate-100 bg-slate-50/80 p-3">
              <dt className="text-xs font-semibold uppercase tracking-wide text-slate-400">{label}</dt>
              <dd className="mt-1 font-semibold text-slate-800">{formatMonths(months)}</dd>
            </div>
          ))}
        </dl>
      </Card>

      <Card>
        <CardHeader title="Skills" />
        <div className="flex flex-wrap gap-2">
          {profile.skills.map((skill) => (
            <span key={skill.id} className="rounded-full bg-accent-50 px-3 py-1 text-sm font-medium text-accent-600">
              {skill.name}
            </span>
          ))}
          {profile.customSkills.map((name) => (
            <span key={name} className="rounded-full bg-slate-100 px-3 py-1 text-sm text-slate-700">
              {name}
            </span>
          ))}
        </div>
      </Card>

      <Card>
        <CardHeader title="Languages" />
        <ul className="space-y-2 text-sm text-slate-700">
          {profile.languages.map((l) => (
            <li key={l.id} className="flex items-center justify-between rounded-lg border border-slate-100 px-3 py-2">
              <span className="font-medium">{l.language}</span>
              <span className="text-slate-500">{l.level}</span>
            </li>
          ))}
        </ul>
      </Card>

      <Card>
        <CardHeader title="Certifications" />
        <ul className="space-y-2 text-sm text-slate-700">
          {profile.certifications.map((c) => (
            <li key={c.id} className="rounded-lg border border-slate-100 px-3 py-2">
              <span className="font-medium">{c.name}</span>
              {c.issuer ? <span className="text-slate-500"> — {c.issuer}</span> : null}
              {c.year ? <span className="text-slate-400"> ({c.year})</span> : null}
            </li>
          ))}
          {profile.certifications.length === 0 ? <li className="text-slate-400">None</li> : null}
        </ul>
      </Card>
    </div>
  );
}
