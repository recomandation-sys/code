// ponytail: static demo data until recommendation / admin APIs exist

export type WorkMode = "remote" | "hybrid" | "onsite";
export type ContractType = "CDI" | "CDD" | "freelance" | "internship";

export interface MockJob {
  id: string;
  title: string;
  company: string;
  location: string;
  workMode: WorkMode;
  contract: ContractType;
  summary: string;
  skills: string[];
  seniority: string;
  salary?: string;
  description: string;
  scrapedAt: string;
}

export interface MockPosition {
  id: string;
  title: string;
  matchPercent: number;
  matchingSkills: string[];
  matchingExperience: string[];
  jobCount: number;
}

export interface MockSkillGap {
  skill: string;
  demandPercent: number;
  context: string;
}

export const MOCK_TESTIMONIALS = [
  { name: "Sara", role: "Data Analyst", quote: "The skills gap list told me exactly what to learn next — I landed interviews in two weeks." },
  { name: "Karim", role: "Frontend Developer", quote: "Finally a matcher that explains why a role fits, not just a mysterious score." },
  { name: "Elena", role: "Product Designer", quote: "Upload, review, done. The CV extraction saved me from rewriting my whole profile." },
];

export const MOCK_STATS = {
  jobsIndexed: "12,480",
  matchesThisWeek: "3,210",
  activeCandidates: "1,840",
};

export const MOCK_JOBS: MockJob[] = [
  {
    id: "j1",
    title: "Senior Data Analyst",
    company: "Northwind Analytics",
    location: "Paris, FR",
    workMode: "hybrid",
    contract: "CDI",
    summary: "Own reporting pipelines, partner with product, and turn messy warehouse data into decisions.",
    skills: ["SQL", "Python", "dbt", "Tableau"],
    seniority: "Senior",
    salary: "55–68k €",
    description:
      "We are looking for a Senior Data Analyst to join our insights team. You will design dashboards, build trustworthy metrics, and coach junior analysts. Experience with modern data stacks (dbt, warehouse SQL) is essential.",
    scrapedAt: "2026-09-02",
  },
  {
    id: "j2",
    title: "Full-Stack Engineer",
    company: "Bridge Labs",
    location: "Remote (EU)",
    workMode: "remote",
    contract: "CDI",
    summary: "Ship candidate-facing features end to end in React and Node, with strong product taste.",
    skills: ["TypeScript", "React", "Node.js", "PostgreSQL"],
    seniority: "Mid",
    salary: "50–62k €",
    description:
      "Build and maintain the JobMatch web app. You will work closely with design and ML on recommendation UX, auth, and profile flows.",
    scrapedAt: "2026-09-01",
  },
  {
    id: "j3",
    title: "ML Engineer — Skills Matching",
    company: "Horizon AI",
    location: "Lyon, FR",
    workMode: "onsite",
    contract: "CDD",
    summary: "Improve skill extraction quality and evaluate ranking models against real CV/job pairs.",
    skills: ["Python", "PyTorch", "NLP", "FastAPI"],
    seniority: "Mid–Senior",
    description:
      "Join a small applied ML team focused on skill span extraction and job ranking. You will own evaluation harnesses and iterate with product on explainability.",
    scrapedAt: "2026-08-30",
  },
  {
    id: "j4",
    title: "Product Designer (Internship)",
    company: "Studio Forma",
    location: "Casablanca, MA",
    workMode: "hybrid",
    contract: "internship",
    summary: "Help redesign career tools for first-job seekers — research, wireframes, and hi-fi UI.",
    skills: ["Figma", "User research", "Prototyping"],
    seniority: "Intern",
    description:
      "6-month internship supporting the design system and candidate onboarding. Portfolio required; career-tech experience is a plus.",
    scrapedAt: "2026-08-28",
  },
];

export const MOCK_POSITIONS: MockPosition[] = [
  {
    id: "p1",
    title: "Data Analyst",
    matchPercent: 92,
    matchingSkills: ["SQL", "Python", "Tableau", "Excel"],
    matchingExperience: ["2 years analytics internship", "Dashboard projects"],
    jobCount: 48,
  },
  {
    id: "p2",
    title: "Business Intelligence Analyst",
    matchPercent: 81,
    matchingSkills: ["SQL", "Power BI", "Data modeling"],
    matchingExperience: ["Reporting for ops stakeholders"],
    jobCount: 22,
  },
  {
    id: "p3",
    title: "Junior Data Engineer",
    matchPercent: 64,
    matchingSkills: ["Python", "SQL"],
    matchingExperience: ["ETL scripts in academic projects"],
    jobCount: 15,
  },
  {
    id: "p4",
    title: "Machine Learning Engineer",
    matchPercent: 41,
    matchingSkills: ["Python"],
    matchingExperience: ["Coursework in ML fundamentals"],
    jobCount: 9,
  },
];

export const MOCK_SKILL_GAPS: MockSkillGap[] = [
  {
    skill: "dbt",
    demandPercent: 68,
    context: "Required in 68% of Data Analyst postings, mainly for ETL and reporting.",
  },
  {
    skill: "Airflow",
    demandPercent: 54,
    context: "Common in data engineering tracks and senior analyst roles with pipeline ownership.",
  },
  {
    skill: "Spark",
    demandPercent: 47,
    context: "Appears in large-scale analytics roles and junior data engineer openings.",
  },
  {
    skill: "Looker",
    demandPercent: 39,
    context: "Used for self-serve BI in product-led companies hiring analysts.",
  },
  {
    skill: "Docker",
    demandPercent: 33,
    context: "Nice-to-have for analysts who collaborate with engineering on reproducible jobs.",
  },
];

export const MOCK_ACTIVITY = [
  { id: "a1", text: "3 new job matches today", time: "2h ago" },
  { id: "a2", text: "You liked Full-Stack Engineer at Bridge Labs", time: "Yesterday" },
  { id: "a3", text: "Profile strength reached 78%", time: "2 days ago" },
];

export const MOCK_ADMIN_KPIS = {
  jobsScrapedWeek: 1842,
  activeUsers: 1840,
  pendingReports: 12,
  newComments: 37,
};

export const MOCK_SCRAPE_SOURCES = [
  { source: "LinkedIn", lastRun: "2026-09-03 08:10", jobsAdded: 620, errors: 3 },
  { source: "Indeed", lastRun: "2026-09-03 07:40", jobsAdded: 510, errors: 1 },
  { source: "Welcome to the Jungle", lastRun: "2026-09-03 06:55", jobsAdded: 412, errors: 0 },
  { source: "Company career pages", lastRun: "2026-09-02 22:15", jobsAdded: 300, errors: 5 },
];

export const MOCK_FEEDBACK = [
  {
    id: "f1",
    sentiment: "negative" as const,
    comment: "Match scores feel off for remote-only roles.",
    confidence: 0.91,
    date: "2026-09-02",
    role: "Backend Engineer",
  },
  {
    id: "f2",
    sentiment: "negative" as const,
    comment: "CV upload failed twice on mobile Safari.",
    confidence: 0.87,
    date: "2026-09-01",
    role: "Designer",
  },
  {
    id: "f3",
    sentiment: "positive" as const,
    comment: "Love the explainable position matches.",
    confidence: 0.94,
    date: "2026-09-01",
    role: "Data Analyst",
  },
  {
    id: "f4",
    sentiment: "positive" as const,
    comment: "Onboarding was surprisingly fast.",
    confidence: 0.88,
    date: "2026-08-30",
    role: "Student",
  },
];

export const MOCK_REPORTS = [
  {
    id: "r1",
    job: "Senior Data Analyst — Northwind",
    field: "Required skills",
    note: "Listed Excel but posting asks for advanced SQL only.",
    date: "2026-09-02",
    status: "New" as const,
  },
  {
    id: "r2",
    job: "Full-Stack Engineer — Bridge Labs",
    field: "Contract type",
    note: "Extracted as CDD, posting says CDI.",
    date: "2026-09-01",
    status: "In Review" as const,
  },
  {
    id: "r3",
    job: "ML Engineer — Horizon AI",
    field: "Location",
    note: "Marked remote; description says Lyon onsite.",
    date: "2026-08-29",
    status: "Fixed" as const,
  },
];

export const MOCK_USERS = [
  { id: "u1", name: "Sara Benali", email: "sara.b@example.com", signup: "2026-08-12", completion: 92, status: "Active" },
  { id: "u2", name: "Karim Diallo", email: "karim.d@example.com", signup: "2026-08-20", completion: 64, status: "Active" },
  { id: "u3", name: "Elena Rossi", email: "elena.r@example.com", signup: "2026-08-28", completion: 41, status: "Active" },
  { id: "u4", name: "Omar Haddad", email: "omar.h@example.com", signup: "2026-07-03", completion: 100, status: "Suspended" },
];

export const WORK_MODE_LABEL: Record<WorkMode, string> = {
  remote: "Remote",
  hybrid: "Hybrid",
  onsite: "On-site",
};
