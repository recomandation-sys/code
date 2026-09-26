import { type FormEvent, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { ApiClientError } from "../../../api/client.js";
import {
  OnboardingFrame,
  OnboardingNav,
  OnboardingSecurityNote,
  OnboardingSidebar,
  OnboardingStepper,
  PROFILE_FLOW_STEPS,
  fieldClass,
} from "../components/OnboardingChrome.js";
import { useCandidateDraft } from "../hooks/useCandidateDraft.js";
import {
  loadPersonalInfo,
  personalInfoFromDraft,
  savePersonalInfo,
  type PersonalInfoDraft,
} from "../utils/wizard-storage.js";

const GENDERS = ["Male", "Female", "Prefer not to say", "Other"] as const;

const COUNTRIES = ["Tunisia", "France", "Morocco", "Algeria", "Belgium", "Canada", "Germany", "Other"] as const;

const TUNISIA_GOVERNORATES = [
  "Ariana",
  "Béja",
  "Ben Arous",
  "Bizerte",
  "Gabès",
  "Gafsa",
  "Jendouba",
  "Kairouan",
  "Kasserine",
  "Kébili",
  "Kef",
  "Mahdia",
  "Manouba",
  "Médenine",
  "Monastir",
  "Nabeul",
  "Sfax",
  "Sidi Bouzid",
  "Siliana",
  "Sousse",
  "Tataouine",
  "Tozeur",
  "Tunis",
  "Zaghouan",
] as const;

function RequiredMark() {
  return <span className="text-danger-500">*</span>;
}

export function PersonalInfoPage() {
  const navigate = useNavigate();
  const { draftId } = useParams<{ draftId: string }>();
  const { data: draft, isLoading, isError, error } = useCandidateDraft(draftId);

  const defaults = useMemo((): PersonalInfoDraft => {
    if (!draftId) {
      return {
        firstName: "",
        lastName: "",
        gender: "",
        dateOfBirth: "",
        country: "Tunisia",
        phoneCode: "+216",
        phone: "",
        governorate: "",
      };
    }
    const saved = loadPersonalInfo(draftId);
    if (saved) return saved;
    if (draft) return personalInfoFromDraft(draft);
    return {
      firstName: "",
      lastName: "",
      gender: "",
      dateOfBirth: "",
      country: "Tunisia",
      phoneCode: "+216",
      phone: "",
      governorate: "",
    };
  }, [draft, draftId]);

  const [form, setForm] = useState<PersonalInfoDraft | null>(null);
  const values = form ?? defaults;
  const [errors, setErrors] = useState<Partial<Record<keyof PersonalInfoDraft, string>>>({});

  function setField<K extends keyof PersonalInfoDraft>(key: K, value: PersonalInfoDraft[K]) {
    setForm((prev) => ({ ...(prev ?? defaults), [key]: value }));
  }

  function validate(data: PersonalInfoDraft): boolean {
    const next: typeof errors = {};
    if (!data.firstName.trim()) next.firstName = "Required";
    if (!data.lastName.trim()) next.lastName = "Required";
    if (!data.gender) next.gender = "Required";
    if (!data.dateOfBirth) next.dateOfBirth = "Required";
    if (!data.country) next.country = "Required";
    if (!data.phone.trim()) next.phone = "Required";
    setErrors(next);
    return Object.keys(next).length === 0;
  }

  function onContinue(e?: FormEvent) {
    e?.preventDefault();
    if (!draftId) return;
    if (!validate(values)) return;
    savePersonalInfo(draftId, values);
    navigate(`/onboarding/education/${draftId}`);
  }

  if (!draftId) {
    return (
      <div className="flex flex-1 items-center justify-center p-8 text-sm text-slate-500">
        Missing draft.{" "}
        <button type="button" className="ml-1 text-brand-600 underline" onClick={() => navigate("/onboarding/upload-cv")}>
          Upload a CV
        </button>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex flex-1 items-center justify-center text-sm text-slate-500" role="status">
        Loading your draft…
      </div>
    );
  }

  if (isError || !draft) {
    const message = error instanceof ApiClientError ? error.message : "This draft could not be loaded.";
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-3 p-8 text-center">
        <p className="text-sm text-danger-600">{message}</p>
        <button type="button" className="text-sm text-brand-600 underline" onClick={() => navigate("/onboarding/upload-cv")}>
          Upload a CV
        </button>
      </div>
    );
  }

  return (
    <OnboardingFrame
      sidebar={
        <OnboardingSidebar
          heroSrc="/personal-info-hero.png"
          tip="Adding your details helps our AI match you with opportunities that fit your background and goals."
          progressPercent={20}
          completedThrough={0}
          steps={PROFILE_FLOW_STEPS}
          title="You're off to a great start!"
          subtitle="Complete your profile to unlock better job matches."
        />
      }
    >
      <OnboardingStepper activeIndex={0} steps={PROFILE_FLOW_STEPS} />

      <form className="mt-5 flex flex-1 flex-col" onSubmit={onContinue}>
        <h1 className="text-xl font-bold tracking-tight text-slate-900 sm:text-2xl">Tell us who you are</h1>
        <p className="mt-1 text-sm text-slate-500">Just the essentials to personalize your experience.</p>

        <div className="mt-5 grid gap-4 sm:grid-cols-2">
          <label className="block text-sm">
            <span className="mb-1.5 block font-medium text-slate-700">
              First name <RequiredMark />
            </span>
            <input
              className={fieldClass}
              value={values.firstName}
              onChange={(e) => setField("firstName", e.target.value)}
              autoComplete="given-name"
            />
            {errors.firstName ? <p className="mt-1 text-xs text-danger-600">{errors.firstName}</p> : null}
          </label>

          <label className="block text-sm">
            <span className="mb-1.5 block font-medium text-slate-700">
              Last name <RequiredMark />
            </span>
            <input
              className={fieldClass}
              value={values.lastName}
              onChange={(e) => setField("lastName", e.target.value)}
              autoComplete="family-name"
            />
            {errors.lastName ? <p className="mt-1 text-xs text-danger-600">{errors.lastName}</p> : null}
          </label>

          <label className="block text-sm">
            <span className="mb-1.5 block font-medium text-slate-700">
              Gender <RequiredMark />
            </span>
            <select className={fieldClass} value={values.gender} onChange={(e) => setField("gender", e.target.value)}>
              <option value="">Select</option>
              {GENDERS.map((g) => (
                <option key={g} value={g}>
                  {g}
                </option>
              ))}
            </select>
            {errors.gender ? <p className="mt-1 text-xs text-danger-600">{errors.gender}</p> : null}
          </label>

          <label className="block text-sm">
            <span className="mb-1.5 block font-medium text-slate-700">
              Date of birth <RequiredMark />
            </span>
            <input
              type="date"
              className={fieldClass}
              value={values.dateOfBirth}
              onChange={(e) => setField("dateOfBirth", e.target.value)}
            />
            {errors.dateOfBirth ? <p className="mt-1 text-xs text-danger-600">{errors.dateOfBirth}</p> : null}
          </label>

          <label className="block text-sm">
            <span className="mb-1.5 block font-medium text-slate-700">
              Country of residence <RequiredMark />
            </span>
            <select className={fieldClass} value={values.country} onChange={(e) => setField("country", e.target.value)}>
              {COUNTRIES.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
            {errors.country ? <p className="mt-1 text-xs text-danger-600">{errors.country}</p> : null}
          </label>

          <label className="block text-sm">
            <span className="mb-1.5 block font-medium text-slate-700">
              Phone <RequiredMark />
            </span>
            <div className="flex gap-2">
              <select
                className={`${fieldClass} w-[7.5rem] shrink-0`}
                value={values.phoneCode}
                onChange={(e) => setField("phoneCode", e.target.value)}
                aria-label="Country code"
              >
                <option value="+216">+216</option>
                <option value="+33">+33</option>
                <option value="+212">+212</option>
                <option value="+213">+213</option>
                <option value="+32">+32</option>
                <option value="+1">+1</option>
              </select>
              <input
                className={fieldClass}
                value={values.phone}
                onChange={(e) => setField("phone", e.target.value)}
                inputMode="tel"
                autoComplete="tel-national"
                placeholder="22 123 456"
              />
            </div>
            {errors.phone ? <p className="mt-1 text-xs text-danger-600">{errors.phone}</p> : null}
          </label>

          <label className="block text-sm sm:col-span-2">
            <span className="mb-1.5 block font-medium text-slate-700">Governorate</span>
            <select
              className={fieldClass}
              value={values.governorate}
              onChange={(e) => setField("governorate", e.target.value)}
            >
              <option value="">Select your governorate</option>
              {TUNISIA_GOVERNORATES.map((g) => (
                <option key={g} value={g}>
                  {g}
                </option>
              ))}
            </select>
          </label>
        </div>

        <div className="mt-auto pt-6">
          <OnboardingNav
            onBack={() => navigate(`/onboarding/cv-check/${draftId}`)}
            onContinue={() => onContinue()}
          />
          <OnboardingSecurityNote />
        </div>
      </form>
    </OnboardingFrame>
  );
}
