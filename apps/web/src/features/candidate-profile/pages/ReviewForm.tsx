import { zodResolver } from "@hookform/resolvers/zod";
import { FormProvider, useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import type {
  CandidateDraft,
  ContractType,
  MobilityPreference,
  WorkMode,
} from "@job-recommender/contracts";

import { Button } from "../../../components/Button.js";
import { reviewFormSchema, type ReviewFormValues } from "../../../schemas/review-form.schema.js";
import { draftToFormValues, formValuesToProfileInput } from "../../../utils/draft-mappers.js";
import { CertificationsSection } from "../components/CertificationsSection.js";
import { ExperienceSection } from "../components/ExperienceSection.js";
import { IdentitySection } from "../components/IdentitySection.js";
import { LanguagesSection } from "../components/LanguagesSection.js";
import { ParseQualityBanner } from "../components/ParseQualityBanner.js";
import { SkillsSection } from "../components/SkillsSection.js";
import { TargetPositionsSection } from "../components/TargetPositionsSection.js";
import { useConfirmProfile } from "../hooks/useConfirmProfile.js";
import { useSubmitPreferenceSurvey } from "../hooks/useSubmitPreferenceSurvey.js";
import { clearPreferences, loadPreferences } from "../utils/wizard-storage.js";
import { ApiClientError } from "../../../api/client.js";

function toMobility(where: "LOCAL" | "FOREIGN" | "BOTH"): MobilityPreference[] {
  if (where === "LOCAL") return ["LOCAL"];
  if (where === "FOREIGN") return ["FOREIGN"];
  return ["LOCAL", "FOREIGN"];
}

export function ReviewForm({ draft }: { draft: CandidateDraft }) {
  const navigate = useNavigate();
  const confirmProfile = useConfirmProfile();
  const submitSurvey = useSubmitPreferenceSurvey();
  const savedPrefs = loadPreferences(draft.id);

  const methods = useForm<ReviewFormValues>({
    resolver: zodResolver(reviewFormSchema),
    defaultValues: draftToFormValues(draft),
    mode: "onBlur",
  });

  function onSubmit(values: ReviewFormValues) {
    const input = formValuesToProfileInput(values, draft.id, draft);
    confirmProfile.mutate(input, {
      onSuccess: (profile) => {
        const prefs = loadPreferences(draft.id);
        if (!prefs) {
          navigate(`/onboarding/survey?profileId=${profile.id}`);
          return;
        }
        submitSurvey.mutate(
          {
            profileId: profile.id,
            contractTypes: prefs.contractTypes as ContractType[],
            workModes: prefs.workModes as WorkMode[],
            mobilityPreferences: toMobility(prefs.whereToWork),
            preferredCountries: [],
          },
          {
            onSuccess: () => {
              clearPreferences(draft.id);
              navigate("/onboarding/privacy");
            },
            onError: () => navigate(`/onboarding/survey?profileId=${profile.id}`),
          },
        );
      },
    });
  }

  const confirmErrorMessage =
    confirmProfile.error instanceof ApiClientError
      ? confirmProfile.error.message
      : "We couldn't save your profile. Please try again.";

  const busy = confirmProfile.isPending || submitSurvey.isPending;

  return (
    <FormProvider {...methods}>
      <form onSubmit={methods.handleSubmit(onSubmit)} className="mx-auto max-w-3xl space-y-6 px-6 py-10">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Review your profile</h1>
          {savedPrefs ? (
            <p className="mt-1 text-sm text-slate-500">Confirm the details below to finish your profile.</p>
          ) : null}
        </div>

        <ParseQualityBanner status={draft.quality.status} warnings={draft.quality.warnings} />

        <IdentitySection draft={draft} />
        <TargetPositionsSection />
        <ExperienceSection draft={draft} />
        <SkillsSection draft={draft} />
        <LanguagesSection />
        <CertificationsSection />

        {confirmProfile.isError ? <p className="text-sm text-red-600">{confirmErrorMessage}</p> : null}

        <div className="flex justify-end pb-10">
          <Button type="submit" disabled={busy}>
            {busy
              ? "Saving…"
              : savedPrefs
                ? "Confirm and finish"
                : "Save and continue to preferences"}
          </Button>
        </div>
      </form>
    </FormProvider>
  );
}
