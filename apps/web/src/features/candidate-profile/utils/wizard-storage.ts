// ponytail: wizard draft lives in sessionStorage until profile confirm API accepts these fields

import type { CandidateDraft } from "@job-recommender/contracts";

export type PersonalInfoDraft = {
  firstName: string;
  lastName: string;
  gender: string;
  dateOfBirth: string;
  country: string;
  phoneCode: string;
  phone: string;
  governorate: string;
};

export type EducationEntry = {
  id: string;
  degree: string;
  institution: string;
  field: string;
  startDate: string;
  endDate: string;
  isCurrent: boolean;
};

export type ExperienceEntry = {
  id: string;
  jobTitle: string;
  company: string;
  startDate: string;
  endDate: string;
  isCurrent: boolean;
  description: string;
  skillsUsed: string;
};

export type CertificationEntry = {
  id: string;
  name: string;
  issuer: string;
  issueDate: string;
  expirationDate: string;
  doesNotExpire: boolean;
  credentialId: string;
  credentialUrl: string;
};

export type SkillsDraft = {
  skills: string[];
};

export type LanguageEntry = {
  id: string;
  language: string;
  level: string;
};

export type PreferencesDraft = {
  whereToWork: "LOCAL" | "FOREIGN" | "BOTH";
  workModes: string[];
  contractTypes: string[];
  goals: Array<"FIND_JOB" | "OPTIMIZE_PROFILE">;
};

function loadJson<T>(key: string): T | null {
  try {
    const raw = sessionStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : null;
  } catch {
    return null;
  }
}

const personalKey = (draftId: string) => `joblik:personal-info:${draftId}`;
const educationKey = (draftId: string) => `joblik:education:${draftId}`;
const experienceKey = (draftId: string) => `joblik:experience:${draftId}`;
const skillsKey = (draftId: string) => `joblik:skills:${draftId}`;
const certificationsKey = (draftId: string) => `joblik:certifications:${draftId}`;
const languagesKey = (draftId: string) => `joblik:languages:${draftId}`;
const preferencesKey = (draftId: string) => `joblik:preferences:${draftId}`;

export function loadPersonalInfo(draftId: string): PersonalInfoDraft | null {
  return loadJson(personalKey(draftId));
}

export function savePersonalInfo(draftId: string, data: PersonalInfoDraft): void {
  sessionStorage.setItem(personalKey(draftId), JSON.stringify(data));
}

export function loadEducation(draftId: string): EducationEntry[] | null {
  return loadJson(educationKey(draftId));
}

export function saveEducation(draftId: string, data: EducationEntry[]): void {
  sessionStorage.setItem(educationKey(draftId), JSON.stringify(data));
}

export function loadExperience(draftId: string): ExperienceEntry[] | null {
  return loadJson(experienceKey(draftId));
}

export function saveExperience(draftId: string, data: ExperienceEntry[]): void {
  sessionStorage.setItem(experienceKey(draftId), JSON.stringify(data));
}

export function loadSkills(draftId: string): SkillsDraft | null {
  return loadJson(skillsKey(draftId));
}

export function saveSkills(draftId: string, data: SkillsDraft): void {
  sessionStorage.setItem(skillsKey(draftId), JSON.stringify(data));
}

export function loadCertifications(draftId: string): CertificationEntry[] | null {
  return loadJson(certificationsKey(draftId));
}

export function saveCertifications(draftId: string, data: CertificationEntry[]): void {
  sessionStorage.setItem(certificationsKey(draftId), JSON.stringify(data));
}

export function loadLanguages(draftId: string): LanguageEntry[] | null {
  return loadJson(languagesKey(draftId));
}

export function saveLanguages(draftId: string, data: LanguageEntry[]): void {
  sessionStorage.setItem(languagesKey(draftId), JSON.stringify(data));
}

export function loadPreferences(draftId: string): PreferencesDraft | null {
  return loadJson(preferencesKey(draftId));
}

export function savePreferences(draftId: string, data: PreferencesDraft): void {
  sessionStorage.setItem(preferencesKey(draftId), JSON.stringify(data));
}

export function clearPreferences(draftId: string): void {
  sessionStorage.removeItem(preferencesKey(draftId));
}

export function splitFullName(fullName: string): { firstName: string; lastName: string } {
  const parts = fullName.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return { firstName: "", lastName: "" };
  if (parts.length === 1) return { firstName: parts[0]!, lastName: "" };
  return { firstName: parts[0]!, lastName: parts.slice(1).join(" ") };
}

export function emptyEducation(): EducationEntry {
  return {
    id: crypto.randomUUID(),
    degree: "",
    institution: "",
    field: "",
    startDate: "",
    endDate: "",
    isCurrent: false,
  };
}

export function emptyExperience(): ExperienceEntry {
  return {
    id: crypto.randomUUID(),
    jobTitle: "",
    company: "",
    startDate: "",
    endDate: "",
    isCurrent: false,
    description: "",
    skillsUsed: "",
  };
}

export function emptyCertification(): CertificationEntry {
  return {
    id: crypto.randomUUID(),
    name: "",
    issuer: "",
    issueDate: "",
    expirationDate: "",
    doesNotExpire: false,
    credentialId: "",
    credentialUrl: "",
  };
}

export function emptyLanguage(): LanguageEntry {
  return {
    id: crypto.randomUUID(),
    language: "",
    level: "",
  };
}

function toMonthInput(year: number | null | undefined, month: number | null | undefined): string {
  if (!year) return "";
  return `${year}-${String(month ?? 1).padStart(2, "0")}`;
}

const COUNTRY_ALIASES: Record<string, string> = {
  tunisie: "Tunisia",
  tunisia: "Tunisia",
  france: "France",
  maroc: "Morocco",
  morocco: "Morocco",
  algerie: "Algeria",
  algérie: "Algeria",
  algeria: "Algeria",
  belgique: "Belgium",
  belgium: "Belgium",
  canada: "Canada",
  allemagne: "Germany",
  germany: "Germany",
};

export function normalizeCountry(raw: string): string {
  const key = raw.trim().toLowerCase();
  if (COUNTRY_ALIASES[key]) return COUNTRY_ALIASES[key]!;
  const known = ["Tunisia", "France", "Morocco", "Algeria", "Belgium", "Canada", "Germany", "Other"];
  const hit = known.find((c) => c.toLowerCase() === key);
  if (hit) return hit;
  return raw.trim() ? "Other" : "Tunisia";
}

export function splitPhone(raw: string): { phoneCode: string; phone: string } {
  const cleaned = raw.trim();
  const m = cleaned.match(/^(\+\d{1,3})\s*(.*)$/);
  if (m) return { phoneCode: m[1]!, phone: m[2]!.replace(/^0+/, "").trim() };
  return { phoneCode: "+216", phone: cleaned };
}

function mapLanguageLevel(level: string): string {
  const upper = level.toUpperCase();
  if (["NATIVE", "FLUENT", "ADVANCED", "INTERMEDIATE", "BASIC"].includes(upper)) return upper;
  if (upper === "C2" || upper === "C1") return "FLUENT";
  if (upper === "B2") return "ADVANCED";
  if (upper === "B1") return "INTERMEDIATE";
  if (upper === "A1" || upper === "A2") return "BASIC";
  return "";
}

export function personalInfoFromDraft(draft: CandidateDraft): PersonalInfoDraft {
  const name = splitFullName(draft.identity.fullName.value ?? "");
  const { phoneCode, phone } = splitPhone(draft.identity.phone.value ?? "");
  return {
    firstName: name.firstName,
    lastName: name.lastName,
    gender: "",
    dateOfBirth: "",
    country: normalizeCountry(draft.identity.country.value || "Tunisia"),
    phoneCode,
    phone,
    governorate: "",
  };
}

export function experienceFromDraft(draft: CandidateDraft): ExperienceEntry[] {
  const records = draft.experience.records;
  if (!records.length) return [emptyExperience()];
  return records.map((r) => ({
    id: r.id || crypto.randomUUID(),
    jobTitle: r.title ?? "",
    company: "",
    startDate: toMonthInput(r.startYear, r.startMonth),
    endDate: r.isCurrent ? "" : toMonthInput(r.endYear, r.endMonth),
    isCurrent: r.isCurrent,
    description: "",
    skillsUsed: (r.technologies ?? []).join(", "),
  }));
}

export function skillsFromDraft(draft: CandidateDraft): SkillsDraft {
  return { skills: draft.skills.detected.map((s) => s.name) };
}

export function certificationsFromDraft(draft: CandidateDraft): CertificationEntry[] {
  if (!draft.certifications.length) return [emptyCertification()];
  return draft.certifications.map((c) => ({
    id: c.id || crypto.randomUUID(),
    name: c.name,
    issuer: c.issuer ?? "",
    issueDate: toMonthInput(c.year, 1),
    expirationDate: "",
    doesNotExpire: true,
    credentialId: "",
    credentialUrl: "",
  }));
}

export function languagesFromDraft(draft: CandidateDraft): LanguageEntry[] {
  if (!draft.languages.length) return [emptyLanguage()];
  return draft.languages.map((lang) => ({
    id: lang.id || crypto.randomUUID(),
    language: lang.language,
    level: mapLanguageLevel(lang.level),
  }));
}

export function preferencesFromDraft(draft: CandidateDraft): PreferencesDraft {
  return {
    whereToWork: "BOTH",
    workModes: [...draft.target.workModes],
    contractTypes: [...draft.target.contractTypes],
    goals: [],
  };
}

/** Write parsed CV fields into wizard sessionStorage (once per section). */
export function seedWizardFromDraft(draft: CandidateDraft): void {
  const id = draft.id;
  if (!loadPersonalInfo(id)) savePersonalInfo(id, personalInfoFromDraft(draft));
  if (!loadExperience(id)?.length && draft.experience.records.length) {
    saveExperience(id, experienceFromDraft(draft));
  }
  if (!loadSkills(id)?.skills.length && draft.skills.detected.length) {
    saveSkills(id, skillsFromDraft(draft));
  }
  if (!loadCertifications(id)?.length && draft.certifications.length) {
    saveCertifications(id, certificationsFromDraft(draft));
  }
  if (!loadLanguages(id)?.length && draft.languages.length) {
    saveLanguages(id, languagesFromDraft(draft));
  }
  if (!loadPreferences(id)) {
    const prefs = preferencesFromDraft(draft);
    if (prefs.workModes.length || prefs.contractTypes.length) savePreferences(id, prefs);
  }
}
