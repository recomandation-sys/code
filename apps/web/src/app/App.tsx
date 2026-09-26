import { Navigate, Route, Routes, useParams, useSearchParams } from "react-router-dom";

import { AdminLayout } from "../layouts/AdminLayout.js";
import { CandidateLayout } from "../layouts/CandidateLayout.js";
import { OnboardingLayout } from "../layouts/OnboardingLayout.js";
import { PublicLayout } from "../layouts/PublicLayout.js";

import { AdminAnalyticsPage } from "../features/admin/pages/AdminAnalyticsPage.js";
import { AdminFeedbackPage } from "../features/admin/pages/AdminFeedbackPage.js";
import { AdminLoginPage } from "../features/admin/pages/AdminLoginPage.js";
import { AdminOverviewPage } from "../features/admin/pages/AdminOverviewPage.js";
import { AdminReportsPage } from "../features/admin/pages/AdminReportsPage.js";
import { AdminScrapingPage } from "../features/admin/pages/AdminScrapingPage.js";
import { AdminUsersPage } from "../features/admin/pages/AdminUsersPage.js";

import { DashboardPage } from "../features/candidate/pages/DashboardPage.js";
import { FeedbackPage } from "../features/candidate/pages/FeedbackPage.js";
import { JobDetailPage } from "../features/candidate/pages/JobDetailPage.js";
import { JobsPage } from "../features/candidate/pages/JobsPage.js";
import { MyJobsPage } from "../features/candidate/pages/MyJobsPage.js";
import { PositionsPage } from "../features/candidate/pages/PositionsPage.js";
import { SettingsPage } from "../features/candidate/pages/SettingsPage.js";
import { SkillsGapPage } from "../features/candidate/pages/SkillsGapPage.js";

import { LandingPage } from "../features/marketing/pages/LandingPage.js";
import { LoginPage } from "../features/marketing/pages/LoginPage.js";
import { SignupPage } from "../features/marketing/pages/SignupPage.js";

import { PrivacyPage } from "../features/onboarding/pages/PrivacyPage.js";
import { CvUploadPage } from "../features/candidate-profile/pages/CvUploadPage.js";
import { CvVerificationPage } from "../features/candidate-profile/pages/CvVerificationPage.js";
import { PersonalInfoPage } from "../features/candidate-profile/pages/PersonalInfoPage.js";
import { EducationPage } from "../features/candidate-profile/pages/EducationPage.js";
import { ExperiencePage } from "../features/candidate-profile/pages/ExperiencePage.js";
import { SkillsWizardPage } from "../features/candidate-profile/pages/SkillsWizardPage.js";
import { CertificationsPage } from "../features/candidate-profile/pages/CertificationsPage.js";
import { LanguagesWizardPage } from "../features/candidate-profile/pages/LanguagesWizardPage.js";
import { PreferenceSurveyPage } from "../features/candidate-profile/pages/PreferenceSurveyPage.js";
import { ProfilePage } from "../features/candidate-profile/pages/ProfilePage.js";

function LegacyReviewRedirect() {
  const { draftId } = useParams<{ draftId: string }>();
  return <Navigate to={`/onboarding/personal-info/${draftId}`} replace />;
}

function LegacySurveyRedirect() {
  const [params] = useSearchParams();
  const q = params.toString();
  return <Navigate to={`/onboarding/survey${q ? `?${q}` : ""}`} replace />;
}

export function App() {
  return (
    <Routes>
      <Route element={<PublicLayout />}>
        <Route path="/" element={<LandingPage />} />
        <Route path="/signup" element={<SignupPage />} />
        <Route path="/login" element={<LoginPage />} />
      </Route>

      <Route element={<OnboardingLayout />}>
        <Route path="/onboarding/upload-cv" element={<CvUploadPage />} />
        <Route path="/onboarding/cv-check/:draftId" element={<CvVerificationPage />} />
        <Route path="/onboarding/personal-info/:draftId" element={<PersonalInfoPage />} />
        <Route path="/onboarding/education/:draftId" element={<EducationPage />} />
        <Route path="/onboarding/experience/:draftId" element={<ExperiencePage />} />
        <Route path="/onboarding/skills/:draftId" element={<SkillsWizardPage />} />
        <Route path="/onboarding/certifications/:draftId" element={<CertificationsPage />} />
        <Route path="/onboarding/languages/:draftId" element={<LanguagesWizardPage />} />
        <Route
          path="/onboarding/profile/:draftId"
          element={<LegacyReviewRedirect />}
        />
        <Route path="/onboarding/survey" element={<PreferenceSurveyPage />} />
        <Route path="/onboarding/privacy" element={<PrivacyPage />} />
      </Route>

      <Route element={<CandidateLayout />}>
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/jobs" element={<JobsPage />} />
        <Route path="/jobs/:id" element={<JobDetailPage />} />
        <Route path="/positions" element={<PositionsPage />} />
        <Route path="/skills-gap" element={<SkillsGapPage />} />
        <Route path="/my-jobs" element={<MyJobsPage />} />
        <Route path="/feedback" element={<FeedbackPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/profile" element={<ProfilePage />} />
      </Route>

      <Route path="/admin/login" element={<AdminLoginPage />} />
      <Route path="/admin" element={<AdminLayout />}>
        <Route index element={<AdminOverviewPage />} />
        <Route path="scraping" element={<AdminScrapingPage />} />
        <Route path="feedback" element={<AdminFeedbackPage />} />
        <Route path="reports" element={<AdminReportsPage />} />
        <Route path="users" element={<AdminUsersPage />} />
        <Route path="analytics" element={<AdminAnalyticsPage />} />
      </Route>

      <Route path="/profile/upload" element={<Navigate to="/onboarding/upload-cv" replace />} />
      <Route path="/profile/review/:draftId" element={<LegacyReviewRedirect />} />
      <Route path="/profile/survey" element={<LegacySurveyRedirect />} />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
