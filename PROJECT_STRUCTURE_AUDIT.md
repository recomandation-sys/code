# Internship project structure audit

Sequential audit. Each section is written only after that folder's files were opened. Status words used below:

- **Active** — imported or run by the current CV app, job extraction, or the frozen leaf path
- **Supporting** — config, env, or tooling the active path needs
- **Experiment** — research or an earlier approach
- **Artifact** — generated output or a dataset, not source
- **Test** — a check
- **Documentation** — explains the project
- **Legacy** — superseded or leftover
- **Unknown** — purpose not settled from the file alone

Recommendation is one of: keep, review, archive, remove.

## How to resume

Last folder fully documented: `job-nlpv2`. Next folder not yet opened: `tests`. Skipped at request: `node_modules`, `readme`. Still unread: `job_nlp/artifacts` file by file. The root `recommendation/` directory is no longer on disk; `app/main.py` still imports `recommendation.api`.

`.git/objects` (3366 files) and `.venv/Lib` (installed third-party packages) were not opened file by file. Their role is recorded in those sections.

---

## internship/ (root files)

```text
internship/
├── .env.example
├── .gitignore
├── README.md
├── requirements.txt
├── package.json
├── package-lock.json
├── tsconfig.base.json
├── _task_source_aware.txt
├── debug-22064d.log
├── debug-cd613c.log
├── datasets_clean_annotation.xlsx
├── datasets_clean_annotation_EN_v2.xlsx
├── it_titles_master_taxonomy_no_seniority.csv
├── leaf_profiles_compact_118_24_8_enriched.json
├── it_knowledge.sqlite.pre_taxonomy_correction_v2.bak
└── job_nlp.rar
```

Root folders are listed in later sections as each one is finished. They are not described here.

### Root file notes

`.env.example` — **Supporting, keep.** Documents the three process env vars: API port 3000, web origin, PostgreSQL `job_recommender`, CV parser URL `localhost:8000`, and the Vite API base. Real `.env` files are gitignored. The apps copy their own examples under `apps/api` and `apps/web`.

`.gitignore` — **Supporting, keep.** Ignores Python caches, `.venv`, Node `node_modules` and build output, local env files, trained weights, the whole `archive/` tree, and large formats (`*.sqlite`, `*.bak`, `*.rar`, `*.bin`). It also ignores `.cursor/`. A later section will check whether ignored paths are still on disk.

`README.md` — **Documentation, keep, review.** Describes the CV upload product: Python parser on port 8000, Express API on 3000, React web on 5173. It also states the frozen job-extraction milestone `occupation_decision_v2_1` (8 families, 24 parents, 118 leaves) and points at `job_nlp/docs/REPOSITORY_LAYOUT.md`. It does not mention `job-nlpv2`, the Rekrute scrape, or this audit. Update it when the layout section of this audit is finished.

`requirements.txt` — **Supporting, keep.** Python deps for the CV parser and later embedding work: FastAPI, PyMuPDF, RapidFuzz, pyahocorasick, pandas, sentence-transformers 5.x, transformers pinned below 4.46, SQLAlchemy, psycopg, pgvector, numpy below 2. The web app does not use this file; Node uses `package.json`.

`package.json` — **Active, keep.** npm workspace root named `job-recommender-web` 0.1.0. Workspaces are `apps/*` and `packages/*`. Scripts run the web, the API, tests, typecheck, and Prisma. Node 20 or newer. Depends on the packages under `apps/` and `packages/`, not on `job_nlp`.

`package-lock.json` — **Supporting, keep.** Lockfile for that workspace install (about 230 KB, dated 25 Aug 2026). Required for a reproducible `npm install`.

`tsconfig.base.json` — **Supporting, keep.** Shared TypeScript options: ES2022, NodeNext, strict, `noUncheckedIndexedAccess`. App tsconfigs are expected to extend it; confirm when `apps/` is audited.

`_task_source_aware.txt` — **Legacy, archive.** A pasted agent task from 4 Sep 2026. It specifies a source-first pipeline for education, ESCO occupation, experience, languages, work mode, and contract type, with skills already done and no new model training. The file ends mid-diagram and is not imported by any module. It is a prompt, not code.

`debug-22064d.log` — **Artifact, remove.** Three JSON lines from a debug session `stages7525` in `stages_75.py`: catalog of 5259 titles, 118 leaves, 2011 evidence lines, 100 offers, and a Test Lead sample score. The script that wrote it is gone. Gitignore already ignores `*.log`.

`debug-cd613c.log` — **Artifact, remove.** One JSON line from `_correct_en_v2.py`: workbook corrections (91 multilabel education rows, 7 work-mode relabels, 9 moved unlabeled, 169 full-time labels set to unknown). The script is gone. Same class of leftover as the other log.

`datasets_clean_annotation.xlsx` — **Artifact, review.** About 6.3 MB. Sheets: Education, Work_Mode, Contract_Type, Seniority, Min_Experience, Quarantine, Data_Dictionary. Each label sheet has title, description, the label, and evidence offsets. `job_nlp/scripts/evaluate_rule_alignment.py` reads this path. It is the earlier annotation workbook, not the English v2 file.

`datasets_clean_annotation_EN_v2.xlsx` — **Artifact, review.** About 5.9 MB. Sheets: Education, Work_Mode, Work_Mode_Unlabeled, Contract_Type, Min_Experience (extra `label_source` column), Data_Dictionary. No Seniority sheet and no Quarantine sheet. The older workbook `datasets_clean_annotation_EN.xlsx` is not at the repo root. It is `exp-fn/datasets_clean_annotation_EN.xlsx`, and that is the file Phase A trained against. This v2 workbook is the later English annotation set.

`it_titles_master_taxonomy_no_seniority.csv` — **Active input, keep.** Header `Title,Parents,Leafs,Families`. 5259 data rows. This is the title catalog the frozen leaf experiments score against. A copy lives under `job-nlpv2/leaf/inputs/` with a `_best` suffix. The root file is the one the debug log counted as 5259 titles. Do not delete until the leaf loader's path is confirmed in the `job-nlpv2` section.

`leaf_profiles_compact_118_24_8_enriched.json` — **Active input, keep.** Schema `leaf_profiles_comprehensive_v1`, taxonomy `IT_KB_2.7.0_REMOVE_GENERIC_LEAVES`. Counts: 8 families, 24 parents, 118 leaves, 1805 related titles, 472 tasks, 721 professional skills, 818 technologies. Each leaf has definition, related titles, tasks, professional skills, and technologies. `job_nlp/taxonomy/semantic_resolver.py` sets `ENRICHED_PROFILE_FILE` to this root path. A second copy is in `job-nlpv2/leaf/inputs/`. Review later which copy the live resolver and the frozen leaf script each load; both files should not drift.

`it_knowledge.sqlite.pre_taxonomy_correction_v2.bak` — **Legacy artifact, archive.** 140 MB SQLite backup from before a taxonomy correction (10 Sep 2026). Gitignore covers `*.bak`. Nothing in the imports searched so far opens this filename. Not a runtime database.

`job_nlp.rar` — **Legacy archive, archive.** 98 MB compressed snapshot of `job_nlp` (11 Sep 2026). Gitignore covers `*.rar`. The live tree is the `job_nlp/` folder. The archive is a backup, not a dependency.

---

## .agents/

Agent skills for Cursor. Not imported by the CV app, the API, or the job pipeline. They change how the coding agent behaves. **Supporting tooling, keep** if you still use these skills. They are not production runtime.

```text
.agents/
└── skills/
    ├── ponytail/SKILL.md
    ├── ponytail-audit/SKILL.md
    ├── ponytail-debt/SKILL.md
    ├── ponytail-gain/SKILL.md
    ├── ponytail-help/SKILL.md
    ├── ponytail-review/SKILL.md
    └── ui-ux-pro-max/
        ├── SKILL.md
        ├── data/
        │   ├── charts.csv
        │   ├── colors.csv
        │   ├── icons.csv
        │   ├── landing.csv
        │   ├── products.csv
        │   ├── react-performance.csv
        │   ├── styles.csv
        │   ├── typography.csv
        │   ├── ui-reasoning.csv
        │   ├── ux-guidelines.csv
        │   ├── web-interface.csv
        │   └── stacks/
        │       ├── astro.csv
        │       ├── flutter.csv
        │       ├── html-tailwind.csv
        │       ├── jetpack-compose.csv
        │       ├── nextjs.csv
        │       ├── nuxt-ui.csv
        │       ├── nuxtjs.csv
        │       ├── react-native.csv
        │       ├── react.csv
        │       ├── shadcn.csv
        │       ├── svelte.csv
        │       ├── swiftui.csv
        │       └── vue.csv
        └── scripts/
            ├── core.py
            ├── design_system.py
            ├── search.py
            └── __pycache__/   (compiled copies of the three scripts; remove)
```

### What the folder does

`ponytail/SKILL.md` tells the agent to prefer the smallest change that works (YAGNI, stdlib, no new dependency). A workspace rule also points at this mode, so this file is the one the agent is instructed to follow on coding tasks.

`ponytail-audit/SKILL.md` is a one-shot whole-repo over-engineering report. It does not edit code.

`ponytail-debt/SKILL.md` greps for `ponytail:` comments and lists deferred shortcuts. It does not edit code.

`ponytail-gain/SKILL.md` prints a fixed benchmark scoreboard. The numbers are not computed from this repo.

`ponytail-help/SKILL.md` is the command card for lite, full, and ultra.

`ponytail-review/SKILL.md` reviews a diff for code to delete. It does not edit unless asked.

`ui-ux-pro-max/SKILL.md` is a design-guide skill: search style, color, type, and stack CSVs, then recommend a design system. It is unrelated to job extraction. Keep only if UI work in `apps/web` should use it.

`scripts/core.py` is a BM25 search over the CSVs. `DATA_DIR` is the sibling `data/` folder. Domains are style, color, chart, landing, product, and the other files named in `CSV_CONFIG`.

`scripts/search.py` is the CLI. It imports `core` and `design_system`. Flags select a domain, a stack, or `--design-system`.

`scripts/design_system.py` aggregates those searches using `ui-reasoning.csv` and can write a design-system markdown file when `persist=True`. About 1000 lines. Depends on `core.py` and the CSVs. Nothing in `apps/` imports it.

`scripts/__pycache__/*.pyc` — **Artifact, remove.** Bytecode for Python 3.12 and 3.14. Gitignore already ignores `__pycache__`.

### Data files

Each CSV is a lookup table for the search script. Headers were read; row counts below are the trailing line counts from the files as opened (header plus rows).

| File | Role |
|---|---|
| `charts.csv` | Chart type by data type, with library and accessibility notes |
| `colors.csv` | Hex palettes by product type |
| `icons.csv` | Lucide-style icon names, import snippets, and when to use them |
| `landing.csv` | Landing-page section order and CTA placement |
| `products.csv` | Product type to recommended style, landing pattern, and palette |
| `styles.csv` | Visual styles (minimalism and others) with CSS keywords and checklists |
| `typography.csv` | Font pairings, Google Fonts URLs, Tailwind config snippets |
| `ui-reasoning.csv` | Decision rules that pick pattern, color mood, and effects per UI category |
| `ux-guidelines.csv` | UX issues with do/don't and code examples |
| `web-interface.csv` | Web interface rules, including accessibility severity |
| `react-performance.csv` | React/Next performance rules with good and bad snippets |
| `stacks/*.csv` | Same shape as `react.csv`: category, guideline, do/don't, code, docs URL. One file per stack: astro, flutter, html-tailwind, jetpack-compose, nextjs, nuxt-ui, nuxtjs, react, react-native, shadcn, svelte, swiftui, vue |

`search.py` documents stacks `html-tailwind`, `react`, and `nextjs` in its usage line, while `core.py` exposes `AVAILABLE_STACKS` for the files that exist. The extra stack CSVs are still inputs to that search, not dead files, as long as `AVAILABLE_STACKS` lists them. Confirm that list when a later pass needs it; the three scripts and the CSV headers are enough to classify the folder.

### Depends on

Nothing in the job or CV code imports `.agents`. The agent runtime reads `SKILL.md` files when a skill is triggered. `search.py` depends on `core.py` and `design_system.py`. `design_system.py` depends on `core.py` and `data/ui-reasoning.csv`. `core.py` depends on every CSV named in `CSV_CONFIG` plus the stack files.

---

## .cursor/

Gitignored local Cursor config. The agent loads this tree. It is not imported by the CV app or the job pipeline.

```text
.cursor/
├── design-system-state-bridge-ds-2026-001.json
├── rules/ponytail.mdc
└── skills/
    ├── ponytail/SKILL.md
    ├── ponytail-audit/SKILL.md
    ├── ponytail-debt/SKILL.md
    ├── ponytail-gain/SKILL.md
    ├── ponytail-help/SKILL.md
    ├── ponytail-review/SKILL.md
    └── ui-ux-pro-max/   (same layout as .agents/skills/ui-ux-pro-max, plus __pycache__)
```

`rules/ponytail.mdc` — **Supporting, keep.** `alwaysApply: true`. This is the rule the agent follows on every coding turn: smallest change, reuse what is already in the repo, one check for non-trivial logic. It does not run at application runtime.

`design-system-state-bridge-ds-2026-001.json` — **Artifact, review.** A paused Figma sync (`phase3-paused-rate-limit`, file `ZVw2RMN1uUYqj9U04UBoIO`). It records variable collections (Primitives, Color, Spacing), pages (Design System, Candidate, Admin), and components already created (Button, Input, Badge, LikeDislike, JobCard, PositionCard, SkillGapCard, Modal, Toast). Blocked and not built: Auth, CV Upload, Onboarding, Dashboard, Admin screens. Nothing in the app imports this JSON. It is a checkpoint for a design-tool run, not source.

`skills/` — **Duplicate, review.** The relative file list matches `.agents/skills`, but 20 files differ by hash: all six ponytail `SKILL.md` files, `ui-ux-pro-max/SKILL.md`, `core.py`, `design_system.py`, and several CSVs (`icons`, `landing`, `react-performance`, `typography`, `ui-reasoning`, `web-interface`, and the astro, jetpack-compose, nuxt-ui, nuxtjs, and shadcn stacks). `styles.csv` matches. Both copies are visible to the agent, so a skill can follow one text or the other depending on which path is loaded. Keep one tree. The `__pycache__` bytecode under `.cursor` is the same class of leftover as under `.agents`: **remove**.

---

## .git/

The repository database for https://github.com/recomandation-sys/recommandation-system.git, branch `main`. HEAD and `refs/heads/main` both point at `56d688f0a37aed1d4db751000f596fb6e4d7892b`. `FETCH_HEAD` and `refs/remotes/origin/main` record that same commit as the last fetch. `ORIG_HEAD` is an older commit `c2a70144`. Last commit message in `COMMIT_EDITMSG`: `chore: update ingestion repository pointer`. `config` enables Git LFS metadata but this audit has not yet checked whether LFS objects are present. `description` is still the default "Unnamed repository" text. `info/exclude` is the stock Git template; the real ignore rules are the root `.gitignore`.

```text
.git/
├── COMMIT_EDITMSG, config, description, FETCH_HEAD, HEAD, index, ORIG_HEAD
├── hooks/            14 *.sample scripts; no active hook (no file without .sample)
├── info/exclude
├── logs/HEAD, logs/refs/heads/main, logs/refs/remotes/origin/
├── refs/heads/main, refs/remotes/origin/, refs/codex/turn-diffs/captures/  (two capture ids, each a 41-byte base pointer)
├── cursor/crepe/<sha>/index.bin, postings.bin, metadata.json   (Cursor code index, version 4; not project source)
└── objects/          3366 files — pack and loose objects, not opened one by one
```

**Supporting, keep the folder.** Do not hand-edit it. The sample hooks and the crepe index are not application code. The Codex turn-diff refs are editor scratch inside the git dir.

---

## .pytest_cache/

Pytest's cache from a run that included archived tests. Gitignored. **Artifact, remove** (pytest recreates it).

```text
.pytest_cache/
├── .gitignore          ignores everything under the cache
├── CACHEDIR.TAG        cache-directory signature
├── README.md           stock pytest warning not to commit this directory
└── v/cache/
    ├── lastfailed      map of node ids to true
    └── nodeids         list of tests pytest last collected
```

`lastfailed` starts with paths under `archive/job_extraction/legacy_v2/tests/` (`test_phase_h.py`, `test_phase_i.py`, skill NER, span datasets, and others). Those tests are from an older extraction stack. The cache is evidence a full pytest run treated archive tests as part of the suite and recorded them as failed. It is not a source of truth for the current suite.

---

## .venv/

Local Python 3.12.10 virtualenv. `pyvenv.cfg` says it was created from `Python312` and does not include system site packages. Gitignored. **Supporting, keep the environment; do not commit it.**

`Lib/`, `Include/`, `Scripts/`, and `share/` are the installed interpreter and third-party packages from `requirements.txt`. Those files were not opened one by one. They are the dependency install, not project source.

`.venv/tmp_en_skillner/en_skillner-0.0.1-py3-none-any.whl` — **Legacy artifact, review.** A 588 MB wheel for a local package `en_skillner` 0.0.1, parked inside the venv rather than installed as a normal requirement. Nothing in the root `requirements.txt` names `en_skillner`. It matches the archived skill-NER tests named in `.pytest_cache`. Do not treat it as part of the current parser until `cv_parser` is audited and shown to import it.

---

## app/

**Active, keep.** Thin FastAPI process on port 8000. The root README starts it with `uvicorn app.main:app`. It does not parse CVs itself.

```text
app/
├── __init__.py          empty package marker
├── main.py              builds the FastAPI app, CORS, and routers
├── api/
│   ├── __init__.py      empty
│   ├── routes.py        /health, /api/cv/parse, /api/cv/profile
│   └── schemas.py       response models
└── __pycache__/         bytecode for the modules above — artifact, remove
```

`main.py` creates the app titled "CV Extraction + Skill Recommendation Service", allows every CORS origin, mounts `app.api.routes.router`, and mounts `recommendation.api.router` at `/api`. Version string comes from `cv_parser.config.settings.parser_version`. Depends on `cv_parser` and `recommendation`.

`api/routes.py` reads the upload, calls `cv_parser.pipeline.extract_profile` for `/api/cv/parse` and `extract_candidate_profile` for `/api/cv/profile`. Validation errors become HTTP 400 via `CVParserError`. Any other exception becomes 422. `/health` returns status and parser version. The file comments that PDF rules live in `cv_parser.ingestion.validator`, not here.

`api/schemas.py` subclasses `ParserDraftResponse` as `ExtractResponse` and `CandidateKnowledgeProfile` as `CandidateProfileResponse`, so the HTTP models stay aligned with the parser schemas. `ErrorResponse` and `HealthResponse` are local. Depends on `cv_parser.schemas`.

`__pycache__/*.cpython-312.pyc` — compiled copies of these modules. **Artifact, remove.** Gitignore already ignores them.

---

## apps/

The Node workspace for the CV product. Two packages: `apps/api` (Express + Prisma + PostgreSQL) and `apps/web` (React + Vite). The root `package.json` runs them. They talk to the Python parser in `app/` over HTTP. They do not import `job_nlp` or `job-nlpv2`.

```text
apps/
├── api/     Express API, Prisma schema, tests
└── web/     React UI, onboarding wizard, mock admin and jobs screens
```

### apps/api — active, keep

**Active.** Public HTTP API on port 3000. Forwards PDFs to `http://localhost:8000/api/cv/parse`, stores a draft, and writes a confirmed profile.

```text
apps/api/
├── .env.example          same keys as the root example; local password placeholder
├── .env                  local copy of those keys — do not commit (gitignored)
├── package.json          @job-recommender/api; scripts dev/build/test/prisma
├── tsconfig.json         extends the root TypeScript base
├── tsconfig.tsbuildinfo  generated typecheck cache — artifact, remove from any commit
├── prisma/
│   ├── schema.prisma
│   ├── seed.ts
│   └── migrations/
│       ├── migration_lock.toml
│       ├── 20260825110400_init/migration.sql
│       └── 20260904120000_wizard_profile_fields/migration.sql
├── src/
│   ├── server.ts, app.ts, config/env.ts
│   ├── routes/          cv, profile, skills
│   ├── controllers/     same three areas
│   ├── services/        draft, parser orchestration, profile confirm
│   ├── repositories/    Prisma access
│   ├── adapters/        parser JSON to UI draft
│   ├── clients/cv-parser.client.ts
│   ├── schemas/         Zod bodies
│   ├── middleware/      upload, validate, errors, request id
│   ├── lib/             prisma, logger, slug, durations, empty draft
│   └── errors/app-error.ts
└── tests/
    ├── fixtures/parser/   v3-good, v3-poor, v3-unknown-skills JSON
    ├── integration/       cv upload and confirm validation
    └── unit/              schema, duration math, parser adapter
```

`prisma/schema.prisma` is the database. Two layers: `CvParseDraft` holds the raw parser JSON and the editable UI draft. `CandidateProfile` and its child tables (education, experience, skills, languages, certifications, preferences, desired positions) are written only after a person confirms. `Skill` is the global lexicon. `userId` on the profile is nullable because login is not real yet. Enums here are the web product's words: contract `CDI` / `CDD` / `INTERNSHIP` / `ALTERNANCE` / `FREELANCE` / `OTHER`, work mode `REMOTE` / `HYBRID` / `ONSITE`. Those contract names are not the job-extraction enums `PERMANENT` / `FIXED_TERM`.

`prisma/seed.ts` upserts skills from `cv_parser/resources/skills/it_lexicon.json`. Depends on that lexicon file.

`src/server.ts` connects Prisma and listens. `src/app.ts` mounts `/health` and `/api/v1` with the three routers. CORS origin is `WEB_ORIGIN` only. Request logs omit bodies so CV text is not written to the log.

`src/config/env.ts` validates `DATABASE_URL`, parser URL, timeout, and max upload size with Zod. Every other API module reads `env` from here.

`src/clients/cv-parser.client.ts` POSTs the PDF as field `file` to the Python `/api/cv/parse` route. Timeout comes from env.

`src/routes` plus `src/controllers`: parse a CV, create a manual draft, get or discard a draft, confirm a profile, save the preference survey, fetch the profile, search skills. `src/services/profile.service.ts` is the confirm transaction (about 9 KB). `src/services/cv-parser.service.ts` calls the client and stores the draft. `src/adapters/parser-to-draft.adapter.ts` turns parser JSON into the UI draft and resolves skill ids. `src/lib/experience-duration.ts` recomputes durations on confirm instead of trusting stored totals. `src/lib/empty-parser-response.ts` builds a blank draft when the user skips upload.

`src/middleware/upload.ts` limits the PDF. `validate.ts` runs Zod. `error-handler.ts` and `request-id.ts` are the shared HTTP edge. `errors/app-error.ts` is the typed error the handlers return.

Tests use Vitest and Supertest. Fixtures are three parser payloads: a good CV, a poor parse, and unknown skills. **Tests, keep.**

`tsconfig.tsbuildinfo` — **Artifact, remove** from the tree if it is tracked. It is a compiler cache.

### apps/web — active UI, with mock screens

**Active** for onboarding and profile review. **Prototype** for jobs, admin, and login: those screens do not call the API.

```text
apps/web/
├── .env.example, .env          VITE_API_BASE_URL only
├── index.html, package.json, tsconfig.json, vite.config.ts
├── tsconfig.tsbuildinfo        generated cache — artifact
├── public/                     hero PNGs and two JOBLIK logos
├── src/
│   ├── main.tsx, vite-env.d.ts, styles/index.css
│   ├── app/App.tsx             route table
│   ├── api/                    client, cv, profile
│   ├── components/             Button, Card, JobCard, MatchRing, Toast, and the rest of the shared UI
│   ├── data/mock.ts            static jobs, users, scrape stats, feedback
│   ├── layouts/                Public, Onboarding, Candidate, Admin
│   ├── schemas/                review form and preference survey, plus a schema test
│   ├── utils/                  draft mappers and duration formatting, plus a mapper test
│   └── features/
│       ├── marketing/          landing, login, signup
│       ├── onboarding/         privacy page
│       ├── candidate-profile/  the real wizard and review flow
│       ├── candidate/          dashboard and empty job pages
│       └── admin/              mock admin pages
└── tests/                      CvUploadPage test and vitest setup
```

`src/app/App.tsx` is the route table. Onboarding is `/onboarding/upload-cv` through languages, then a preference survey and privacy page. Old paths `/profile/upload`, `/profile/review/:draftId`, and `/profile/survey` redirect into that wizard. Candidate routes are dashboard, jobs, positions, skills gap, my jobs, feedback, settings, and profile. Admin routes are login, overview, scraping, feedback, reports, users, and analytics.

`src/api/client.ts` is the only `fetch` wrapper. Base URL defaults to `http://localhost:3000/api/v1`. `cv.api.ts` and `profile.api.ts` call parse, draft, confirm, and skill search. The wizard hooks (`useParseCv`, `useCandidateDraft`, `useConfirmProfile`, `useSkillSearch`, `useSubmitPreferenceSurvey`) use those functions. That path is **active** and depends on `apps/api` and `@job-recommender/contracts`.

`src/features/candidate-profile/` is the working product UI: upload, verification, personal info, education, experience, skills, certifications, languages, preference survey, and profile. `utils/wizard-storage.ts` keeps wizard progress in the browser. `wizard-storage.selfcheck.ts` is a small runnable check for that storage. Section components edit the draft. **Active, keep.**

`src/features/marketing/pages/LoginPage.tsx` and `SignupPage.tsx` check the form locally and then navigate to the dashboard. A comment in the login page says UI-only auth until a real auth service exists. **Prototype, review.** There is no user table behind them. The Prisma comment that `userId` stays nullable matches this.

`src/features/candidate/pages/JobsPage.tsx`, `JobDetailPage.tsx`, `PositionsPage.tsx`, `SkillsGapPage.tsx`, and `MyJobsPage.tsx` are empty states that send the user back to CV upload. They do not list scraped jobs. `DashboardPage.tsx`, `FeedbackPage.tsx`, and `SettingsPage.tsx` are the logged-in shell around that. **Prototype, keep as UI** until a recommendation API exists. Do not treat them as the Rekrute pipeline.

`src/data/mock.ts` is static demo data. Its own comment says it stands in until recommendation and admin APIs exist. Jobs, positions, skill gaps, testimonials, admin KPIs, users, feedback, reports, and scrape-source counts live here. **Prototype, keep** only while those screens are demos.

`src/features/admin/` reads that mock file. `AdminScrapingPage.tsx` draws a bar chart from hardcoded weekly counts and `MOCK_SCRAPE_SOURCES`. It does not call `job_nlp` or the Rekrute scraper. `AdminLoginPage.tsx` is the same kind of local form as the public login. **Prototype, review.** The scraping page can be mistaken for the real ingestion pipeline. It is not.

`public/*.png` — marketing images for the wizard steps and the JOBLIK logo. **Supporting, keep** with the web app.

`src/components/` — shared visual pieces. `JobCard` and `MatchRing` are for the demo job screens. **Active UI, keep.**

Tests: `tests/CvUploadPage.test.tsx`, `src/schemas/review-form.schema.test.ts`, `src/utils/draft-mappers.test.ts`. **Tests, keep.**

`tsconfig.tsbuildinfo` — **Artifact.** Same as the API cache.

---

## archive/

**Legacy.** Gitignore already ignores the whole tree. Nothing under it is imported by `app/`, `apps/`, `job_nlp`, or `job-nlpv2`. A search for `archive/` in source and docs only finds comments and READMEs that point at older paths. Those older paths are not on disk: `archive/job_extraction/`, `archive/pre_recommender_cleanup/`, `archive/experiments/`, and `archive/job_nlp/taxonomy_migrations/` are named in READMEs and in old report JSON, and they are absent. What is on disk is seven extractor snapshots, 197 files.

```text
archive/
├── contract/
├── education/
├── exp-fn/
├── experience/
├── leaf/
├── technologies/
└── work_mode/
```

The Python files are copies of an earlier numbered investigation (`02_contract`, `03_work_mode`, `04_experience`, `07_education`, `09_seniority`, `10_job_family_parent_leaf`). They still import `job_nlp.pipeline.schemas` and `job_nlp.rules.base`. The leaf scripts still import `job_nlp.taxonomy.it_leaf_pipeline_best`, which was moved out of that package. Running them as-is would fail or would score the old pipeline, not the frozen 70/15/15 path. **Keep the folder as history. Do not wire it back in.**

Every `__pycache__` directory beside these modules is a compiled copy. **Artifact, remove.**

### archive/contract

`investigation/02_contract/base.py` — shared fold, first-regex, and `RuleHit` helper. **Legacy.**

`investigation/02_contract/contract.py` — regex contract rules. Labels are `CDI`, `CDD`, `INTERNSHIP`, `FREELANCE`, then `OTHER`. Priority prefers internship over freelance over CDD over CDI. This is the old French-label rule set, not the current `PERMANENT` / `FIXED_TERM` extractor. **Legacy.**

`reports/contract_type_english_test_set.json` — 75 attached English sentences, expected `PERMANENT` and the same family of labels, 75 passed. **Artifact.**

`reports/contract_type_real_world_it_12.json` — 12 hand-written IT descriptions, 12 passed. **Artifact.**

`reports/contract_type_random_30_all_websites.json` — seed 20260909, 30 offers drawn from arbeitnow, himalayas, itjobs_pt, keejob, rekrute, remoteok, and remotive. **Artifact.**

`reports/manual_review_contract_type_500.jsonl` — 500 review rows (`annotation_id`, title, description, `contract_type`, evidence). **Artifact.** This is a labeled set, not a live extractor.

### archive/education

`investigation/07_education/education.py` — first-match education rules. Labels include `MASTER_OR_HIGHER`, `BACHELOR`, `ASSOCIATE`, `UNKNOWN`, plus a required/preferred strength check. Patterns still include French cues (`bac+5`, `licence`, `bts`). **Legacy.** The live extractor is `job-nlpv2/education`.

`tests/education/test_fixture_regressions.py` — loads `education_extraction_given_examples.json` and compares it to `job_nlp.extraction.education.EducationExtractor`, mapping a retired seven-label ontology onto the four live levels. **Test, review.** It still points at the live extractor, so a pytest collection that walks `archive/` would run it. The root `.gitignore` ignores `archive/`, but pytest does not.

`reports/education_extraction_given_examples.json` — the fixture that test reads (`total`, `passed_expected_fields`, `results`). **Artifact, keep** only if that test is kept.

`reports/education_extraction_random_30.json` — seed sample, websites, pipeline, results. **Artifact.**

`reports/education_extraction_random_20.json` — meant to be a 20-offer sample from `job_nlp/data/v2/active/english/rekrute_en.jsonl` (seed 20260909, country US). The file is not valid JSON: the first offer object starts with `{ù`. **Artifact, review.** Do not parse it as a result set.

`reports/manual_review_education_500.jsonl` — 500 review rows with an `education` field. **Artifact.**

Associate-degree spreadsheets, all the same columns `title, full_description, education_degree, education_evidence, url` unless noted:

- `associate_offers_20_plus_54_evidence.csv`
- `merged_associate_vocational_education_offers.csv`
- `merged_associate_vocational_education_offers_corrected.csv`
- `merged_associate_vocational_education_offers_manually_verified.csv`
- `merged_education_offers_32_manually_verified.csv`
- `merged_education_offers_32_without_description_evidence.csv`

URL-retrieval batches add `row_number`, `retrieval_status`, and `http_status`. Each CSV has a small JSON report with record counts and degree counts. The first report says its source was `C:\Users\Hzdou\Videos\new_associate_degree_offers (1).csv` and its original output path was under `job_nlp/artifacts/reports/`.

- `new_associate_degree_offers_1_enriched.csv` and `_report.json` — 16 records, 5 descriptions recovered
- `new_associate_degree_offers_batch2_enriched.csv` and `_report.json`
- `new_associate_degree_offers_batch3_enriched.csv` and `_report.json`
- `new_associate_degree_offers_batch3_checked_enriched.csv` and `_report.json`
- `url_offers_171_education.csv` and `url_offers_171_education_report.json`

**Artifact, keep** as the associate-degree review trail. The three “merged” and “corrected” copies are successive edits of one sheet, so only the manually verified files are the ones to open if someone returns to this work.

### archive/experience

`investigation/04_experience/experience.py` — minimum months from year ranges, “at least N years”, and beginner phrases. Returns null when there is no evidence. **Legacy.**

`investigation/09_seniority/seniority.py` — explicit title rules with provenance. Resolves only when a single label wins (`EXPLICIT_SINGLE`). **Legacy.**

`investigation/09_seniority/seniority_resolver.py` — explicit rules first, then a TF-IDF or XLM-R model, else `UNKNOWN`. **Legacy.**

`investigation/09_seniority/seniority_rules_v1.json` — version `seniority_rules_v1`. Priority `INTERN`, `MANAGER`, `LEAD`, `SENIOR`, `JUNIOR`, `MID`. The live experience brackets (`0_YEARS`, `1_2_YEARS`, …) do not read this file. **Legacy.**

`investigation/09_seniority/title_rules.py` — high-precision title rules for family and seniority. **Legacy.**

`investigation/09_seniority/train_tfidf.py` — TF-IDF plus LinearSVC seniority baseline. **Experiment.**

`scripts/evaluate_rules_benchmark.py` — scores production rule extractors against grounded workbooks. **Legacy script.**

`scripts/evaluate_seniority_experience_gold.py` — scores the English seniority extractor against a reviewed workbook. **Legacy script.**

`tests/test_seniority_experience_extractor.py` — imports `job_nlp.extraction.seniority_experience_extractor`. **Test, review**, same pytest-collection warning as the education test.

`reports/rules_grounded_evaluation.json` — status `BLOCKED_MISSING_GROUNDED_DATASET`. It names two workbooks under `exp-fn/data/processed/` that are not in this archive. **Artifact.**

`reports/seniority_experience_attached_examples.json` and `_retest.json` — 134 attached examples each, with passed/failed counts. **Artifact.**

`reports/seniority_experience_50_dataset_retest.json`, `seniority_experience_100_dataset.json`, `seniorities_experience_200_dataset.json` — sampled evaluation sets of 50, 100, and 200. **Artifact.**

`reports/manual_review_minimum_experience_months_500.jsonl` and `manual_review_seniority_500.jsonl` — 500 review rows each. **Artifact.**

`reports/it_english_job_offers_2486_patched_seniority_experience.csv` — 2,486 English offers with pipeline seniority and minimum months. About 9.6 MB. **Artifact.**

`reports/it_english_job_offers_2486_patched_vs_corrected_seniority_experience.csv` — the same offers with `pipeline_*` and `correct_*` columns plus evidence. About 10 MB. **Artifact.** This is the comparison sheet, not a gold file the live extractor loads.

### archive/work_mode

`investigation/03_work_mode/work_mode.py` — regex for remote, hybrid, and onsite, with negative patterns for temporary or COVID remote. Returns a `RuleHit` through the old pipeline schema. **Legacy.** The live three-mode extractor is `job-nlpv2/work_mode`.

`reports/manual_review_work_mode_500.jsonl` — 500 review rows with a `work_mode` field. **Artifact.**

### archive/exp-fn

A scoring dump of the deterministic extractors on the clean-annotation workbooks. The only script is `scripts/apply_rule_extraction_clean_annotation.py`. Its docstring says it runs the extractors on `datasets_clean_annotation_EN.xlsx`. The code imports `job_nlp.extraction` contract, education, seniority, and work-mode classes. **Legacy script.** Those imports are the thin re-exports, so a rerun would hit whatever those re-exports point at today, and it would write under this archive tree.

`artifacts/rules/rule_adapter_manifest.json` — pins `job_nlp.contracts.adapters.extract_rule_fields` and stores sha256 hashes of `adapters.py`, `business_policy.py`, and `ontology.py`. **Artifact.** The hashes are a snapshot. They are not checked at runtime.

`artifacts/rules/rules_only_validation.json` and `.md` — 546 canonical rows. The markdown table reports field accuracy for education, work mode, contract, minimum experience, and seniority. **Artifact.** Those numbers belong to that run. They are not a current score of `job-nlpv2`.

Six result generations follow. Each has per-field JSON lists, one combined `rule_extraction_results.json`, one `summary.json`, an xlsx, a large `.xlsx.inspect.ndjson` (about 39–41 MB), and a `summary_preview.png`.

| Folder | What changed versus the one before it |
|---|---|
| `rule_extraction_clean_annotation` and `rule_extraction_binary_workmode` | Same row counts: contract 1045, education 1118, min experience 868, seniority 837, work mode 799. The clean-annotation xlsx is named `datasets_clean_annotation_EN_rule_results.xlsx`. The binary one is `..._binary.xlsx`. |
| `..._v2`, `..._v3`, `..._v4` | Seniority sheet dropped. Min experience grows to 1383. Work mode splits into 600 labeled and 199 unlabeled. Input named in the v5 summary is `datasets_clean_annotation_EN_v2.xlsx`. |
| `..._v5` | Work mode 591 labeled and 208 unlabeled. Latest of this series. |

**Artifact.** Keep `v5` if one generation is enough. The earlier five generations and every `.inspect.ndjson` are repeated score dumps. **Review for deletion** of v1–v4 and the ndjson inspect files. They are the bulk of this folder.

### archive/leaf

Two superseded scorers at the top:

`it_leaf_pipeline_best.py` — five-stage leaf choice. The emitted leaf is still 75% title and 25% job-chunk. A comment says beta 0.15 and a 0.03 parent gap were uncalibrated, and that `mix_enriched` should not replace `mix_baseline` until a gold split exists. Paths point at `job_nlp/best_leaf_extraction`, which is not the frozen `job-nlpv2` layout. **Legacy.**

`it_leaf_pipeline_tech25.py` — imports that best module. Baseline 0.75 title + 0.25 technology cosine. Enriched averages technology, definition, and main tasks into the 25%. **Legacy.** The frozen formula is 0.70 / 0.15 / 0.15 and lives in `job-nlpv2`.

`investigation/10_job_family_parent_leaf/` — the older classifier stack:

- `collision_rules.py` — versioned leaf precedence
- `engine.py` — taxonomy candidates; regex is evidence only
- `job_family_consistency.py` — parent/leaf validator
- `job_family_resolver.py` — parent then leaf
- `job_family_taxonomy_v1_1.json` — version 1.1, **510 leaves and 35 parents**. The live registry is 118 leaves, 24 parents, 8 families. This file is an older, larger taxonomy.
- `leaf_resolver.py` — taxonomy match, then a model, then abstain
- `loader.py` — parent to allowed leaves
- `losses.py` — class weights for parent-model training
- `parent_resolver.py` — frozen parent resolver
- `registry.py` — leaf model registry
- `train_tfidf_leaf.py`, `train_tfidf_svm.py` — TF-IDF baselines
- `train_xlmr.py` — XLM-R fine-tune for 25 parent classes, marked validation only

**Experiment.** Do not load this taxonomy beside the 118-leaf registry.

`job_nlp_archived/` — earlier 100-offer writeups, one README (or markdown note) per approach. `it_titles_master_taxonomy_old.csv` is an older title catalog (`Title, Parents, Leafs, Families`). `rekrute_it_100_classifier.json` and `rekrute_it_100_closest_titles.json` are 100-row score dumps. `rekrute_it_100_closest_titles.md` and `rekrute_it_100_profile_extraction.md` are the prose versions.

| File | What that pass did |
|---|---|
| `rekrute_it_100_final_5259/README.md` | Final family, parent, and leaf on the 5259-title catalog |
| `rekrute_it_100_final_leaf/README.md` | Final leaf only |
| `rekrute_it_100_four_stages_5259/README.md` | Non-model titles, title model, job chunks, 50/50 mix |
| `rekrute_it_100_stages_75_25/README.md` | Same stages with a 75/25 mix |
| `rekrute_it_100_job_span/README.md` | Job section instead of cleaned NESTA text |
| `rekrute_it_100_leaf_relations/README.md` | Leaf from definition, main tasks, and technologies |
| `rekrute_it_100_leaves/README.md` | Titles, descriptions, and leaf scores |
| `rekrute_it_100_technologies/README.md` | Technologies found in the 100 |
| `rekrute_it_100_title_master/README.md` | Title match on the master taxonomy |
| `rekrute_it_100_title_no_seniority/README.md` | Title match after seniority words are removed |
| `rekrute_it_100_title_no_seniority_similarity/README.md` | Semantic similarity on those titles |
| `rekrute_it_100_top5/README.md` | Five closest titles and the leaf stored on each |
| `rekrute_it_100_weighted/README.md` | Exact title, then weighted similarity |
| `rekrute_it_100_weighted_5259/README.md` | Weighted match on the 5259-title taxonomy |
| `rekrute_it_43_family_refused/README.md` | 43 offers the family gate refused |
| `rekrute_it_43_family_refused/CHUNKS.md` | Cleaned NESTA, then chunking |
| `rekrute_it_43_family_refused/STAGES.md` | Four stages on those 43 |
| `rekrute_it_43_no_leaf/README.md` | 43 offers with no leaf |

**Artifact.** The frozen 70/15/15 report is under `job-nlpv2/leaf/reports`, not here. These READMEs are the trail that led there.

`reports/rekrute_it_100_leaf_pipeline_best.json` and `reports/rekrute_it_100_leaf_pipeline_best/README.md` — the 75/25 baseline run. The README says 98 `FINAL_LEAF`, 0 `REVIEW_AMBIGUOUS`, 2 `OUT_OF_IT_DOMAIN`, and 24 offers where the enriched leaf differs. **Artifact.** Superseded by the frozen formula.

`reports/rekrute_it_100_tech25/README.md` — title 75, technologies 25. `rekrute_it_100_tech50/README.md` — title 50, technologies 25, role text 25. `rekrute_it_100_tech60/README.md` — title 60, technologies 25, role text 15. `rekrute_it_100_title60_tech15/README.md` — title 60, technology 15, role text 25. **Artifact.** None of these is the frozen 70/15/15 mix.

`reports/family_leaf_hybrid_100.json` — schema, dataset, taxonomy, model, and modes for a 100-offer hybrid. **Artifact.**

`reports/leaf_confusion_matrix.csv` — `gold_leaf, predicted_leaf, count`. `leaf_hard_negative_pairs.csv` — `leaf_a, leaf_b, count`. **Artifact.**

`reports/leaf_error_analysis.json` and `.md`, plus `leaf_error_analysis_after_proposal.json` and `.md` — the same analysis shape before and after a proposal (records, slices, parent metrics, hard negatives, review queue). The two JSON files are the same size. **Artifact.**

`reports/manual_review_family_parent_leaf_500.jsonl` — 500 review rows with family, parent, leaf, and evidence. **Artifact.**

### archive/technologies

No extractor source. Only reports.

`reports/manual_review_technologies_500.jsonl` — 500 review rows with a `technologies` field. **Artifact.**

`reports/final_nesta_tech_v2/` — the close-out of Nesta skills plus technology taxonomy v2:

- `FINAL_STATUS.md` — states production imports from archive are zero, ESCO mapping is disabled, and generic rules only. It also says “recommendation ready” and “NLP extraction phase closed”. That is the status of that cleanup, not a claim that the current occupation pipeline is production-ready.
- `07_final_architecture.md` — English gate, Nesta spans, v2 technology recovery, then a semantic family fallback. The live family path has since moved on (the 0.55 / 0.015 gates and the frozen leaf formula are not described here).
- `01_final_20_job_output.csv` — 20 jobs, columns `job_number, title, category, name, canonical_id, requirement, sources, surface`.
- `02_regression_summary.json` — focus-token hits and generic-tech leak count.
- `03_generic_matcher_tests.md` — matcher cases.
- `04_repo_cleanup_inventory.csv` — path, classification, reason, destination.
- `05_archive_manifest.csv` — from/to moves from that cleanup. Several destinations named there are the missing `archive/job_extraction` paths.
- `05_technology_recall_final.csv` — token presence in sets A, D, and FINAL.
- `06_active_dependency_check.txt` — import check for the production skill path.

**Documentation and artifact.** Keep `FINAL_STATUS.md` and `07_final_architecture.md` as the record of that cleanup. The CSVs are the evidence for that record.

---

## artifacts/

Generated outputs at the internship root. The README says these are extraction reports and frozen audits, not taxonomy source. What is actually here is broader: balanced training sheets, DeBERTa checkpoints, a contract-type comparison, two spreadsheet-authoring workspaces, one recommendation eval for a named candidate, and an unlabeled gold-annotation campaign. The live CV app and the frozen leaf path do not load this folder. `scripts/build_balanced_education_3class.py` and `scripts/build_balanced_min_exp_dataset.py` write `artifacts/datasets`. `experiments/minimum_experience_ml` and `experiments/contract_type_ml` write the model runs. `job_nlp.recommendation.evaluation.gold_framework` is the command the gold reports tell you to run later.

`rule_alignment/` is an empty directory. **Remove.**

```text
artifacts/
├── README.md
├── datasets/
├── gpu_smoke/
├── internship_consistency_work/
├── merged_corrected_work/
├── metrics/
├── models/
├── predictions/
├── recommendation_eval/
├── recommendation_gold_v1/
└── rule_alignment/          empty
```

### datasets

Education and minimum-experience sheets used as ML inputs.

`balanced_education_3class_900.parquet` and `.xlsx` — 900-row three-class education set. The plus-associate report names the xlsx as an input that originally lived under Downloads. **Artifact.**

`balanced_education_3class_plus_associate.csv`, `.xlsx`, and `_report.json` — 900 three-class rows plus 242 associate rows, 0 duplicates removed, 1142 rows. Columns are `title`, `description`, `education_level`, `evidence`. Counts: BACHELOR 330, UNKNOWN 286, MASTER_OR_HIGHER 284, ASSOCIATE 242. **Artifact, keep** as the education training sheet. The parquet of the 900-row file is the same table in another format.

`balanced_min_experience_dataset.parquet` and `.xlsx` — the minimum-experience counterpart written by `scripts/build_balanced_min_exp_dataset.py`. No report JSON sits beside them. **Artifact.**

### metrics, predictions, and the contract-type model

These three belong to one contract-type experiment. Labels are `PERMANENT`, `FIXED_TERM`, `FREELANCE`, `INTERNSHIP`, `TEMPORARY`, `UNKNOWN`. The test split in `internal_data_validation.json` is 45 rows (5 permanent, 3 fixed-term, 9 freelance, 3 internship, 25 unknown, 0 temporary). Accuracy on 45 rows is not a production score.

`metrics/comparison_metrics.csv` and `.json` — four systems on that test split:

| System | Accuracy | Macro F1 |
|---|---:|---:|
| RULE_ONLY | 0.711 | 0.570 |
| ML_ONLY | 0.733 | 0.536 |
| ML_ONLY_PRETRAINED | 0.556 | 0.119 |
| HYBRID | 0.756 | 0.613 |

`metrics/confusion_matrix_hybrid.csv`, `confusion_matrix_ml_only.csv`, `confusion_matrix_ml_only_pretrained.csv`, `confusion_matrix_rule_only.csv` — one matrix per system. **Artifact.**

`metrics/error_analysis.csv` and `error_summary.json` — error buckets on the same split. The summary counts 6 `ML_UNKNOWN_MISSED`, 23 `OTHER`, 1 `BOTH_WRONG`, 5 `RULE_FP_FREELANCE_FROM_CONTRACT_GENERIC`, 7 `RULE_MISSED_ML_CAUGHT`, 3 `ML_MISSED_RULE_CAUGHT`. **Artifact.**

`metrics/internal_data_validation.json` — split check for `experiments/contract_type_ml/data/raw/contract_type_balanced_finetuning.csv` (1058 rows, 610 oversampled, 0 description-hash leakage across splits). **Artifact.**

`metrics/selected_threshold.json` — threshold 0.6, validation macro F1 0.389 on 45 rows, sweep 0.05 to 0.95. **Artifact.**

`metrics/threshold_search.csv` — the sweep behind that choice. **Artifact.**

`predictions/test_comparison.csv` — the 45 test rows with gold label, rule label, ML label, pretrained label, and hybrid label. Header starts `id, row_number, title, gold_label, ...`. **Artifact.**

`models/from_scratch/` — DeBERTa-v3-small sequence classifier trained from scratch on that contract CSV. `config.json` maps ids to the six labels. `run_metadata.json` records 18 Sep 2026, CUDA on an RTX 4060 Laptop, 491 seconds, `pretraining_used: false`, output dir `artifacts`. `model.safetensors` is about 568 MB. `tokenizer.json` is about 8 MB. `training_args.bin` is the Trainer args blob. `checkpoint-244/` and `checkpoint-305/` repeat the weights and add `optimizer.pt` (about 1.1 GB each), `scheduler.pt`, `rng_state.pth`, and `trainer_state.json`. **Experiment weights.** The live contract extractor does not load them. Keep one checkpoint if the run must be reproducible. The two optimizer states are the expensive duplicates. **Review for deletion** of `optimizer.pt` once the safetensors file is the one you intend to keep.

### gpu_smoke

An earlier pass of the same contract-type from-scratch run, timestamped 11:55 UTC on 18 Sep 2026, nine minutes before `models/from_scratch`. `models/from_scratch/checkpoint-121/` is step 121 and again stores a 568 MB `model.safetensors` plus a 1.1 GB `optimizer.pt`.

`metrics/comparison_metrics.csv` uses the same four systems. Rule-only matches the later run (accuracy 0.711). ML-only accuracy here is 0.20 and hybrid is 0.222, against 0.733 and 0.756 in `artifacts/metrics`. The confusion matrices, `error_analysis.csv`, `error_summary.json`, and `predictions/test_comparison.csv` are the smoke-run copies. **Artifact.** This folder is the failed or unfinished smoke. The later numbers live in `artifacts/metrics`. **Review:** the smoke weights and optimizer can go if `models/from_scratch/model.safetensors` is kept.

### models/20260917T140922Z

A different task: minimum-experience evidence, not contract type. `run_metadata.json` says DeBERTa-v3-small, git commit `56d688f` (current `main`), stage `internal_fine_tuning_from_weak`, initialized from `experiments/minimum_experience_ml/artifacts/domain_pretrain/weak_candidate/...`. Best validation evidence F1 0.918 after 4 epochs. Selected threshold 0.7. `best/` holds `config.json`, `model.safetensors` (about 568 MB), and the tokenizer. **Experiment weights.** Loaded by the minimum-experience ML package when that experiment is run, not by `job-nlpv2` experience extraction.

### internship_consistency_work and merged_corrected_work

Two one-off spreadsheet jobs. Each contains its own `node_modules` (7,796 files, including Playwright, pdf.js, sharp, and tesseract). Those installs exist so the `.mjs` scripts can import `@oai/artifact-tool`. They are not the product's Node workspace. **Remove both `node_modules` trees.**

`internship_consistency_work/prepare_rows.py` reads a corrected workbook from `C:\Users\Hzdou\Downloads\all_corrected_offers_0_2485_with_seniority.xlsx` and `job_nlp/artifacts/reports/full_dataset_extraction/it_english_job_offers_2486.csv`, then calls `job_nlp.extraction.contract_type_extractor.enforce_internship_consistency`. It writes `prepared_rows.json`. **Legacy script.** The Downloads path will fail on another machine.

`build_output.mjs` writes `all_corrected_offers_0_2485_with_internship_consistency.xlsx` (about 3.2 MB) by patching columns E, H, and J–M. `inspect_source.mjs` is the preview helper. `source_preview.png` and `output_preview.png` are screenshots of those sheets. The `.xlsx.inspect.ndjson` (about 21 MB) is a cell dump of the output workbook. **Artifact.** Keep the xlsx if that corrected 2,486-offer sheet is still the reference. The ndjson and both PNG previews are disposable.

`merged_corrected_work/merged_pipeline_corrected_2486.csv` — 2,486 offers. Header: `row_number, title, description, job_family, job_parent, job_leaf, education_level, pipeline_minimum_experience_months, correct_min_experience_months, min_exp_evidence, pipeline_seniority, correct_seniority, seniority_evidence, contract_type, correct_contract_type, work_mode, language, technologies, url, internship_consistency_applied, experience_filled_from_seniority`. Row 0 is a Himalayas Webmaster offer labeled `WEB_ADMIN` / `SENIOR` / `REMOTE`. **Artifact, keep** as the merged pipeline-versus-corrected sheet.

`build_xlsx.mjs` turns that CSV into an xlsx under `job_nlp/artifacts/reports/full_dataset_extraction/`. `merged_preview.png` is a screenshot. **Legacy script plus artifact.**

### recommendation_eval/hazem_douzi

One candidate run, not a general benchmark. `candidate_profile.json` is the matching profile. `evaluation_summary.md` names the target `FULLSTACK_DEVELOPER` → `SOFTWARE_DEVELOPMENT` → `SOFTWARE`, work mode remote required, contract no preference, experience 0 months, education `VOCATIONAL_DIPLOMA`. The parent summary scores 1,596 of 2,000 jobs. Top 10 are all the same family, with 1 exact fullstack title. `run_metadata.json` says the ranker is `deterministic_reciprocal_v1` with geometric fusion. Embeddings, FAISS, a cross-encoder, an LLM, and XGBoost were not used. Config is `job_nlp/recommendation/config/recommendation_v1.yaml`.

`frozen_extraction_with_skills/extractions.jsonl` is the catalog (about 100 MB). `summary.json` says schema `random_unlabeled_job_extraction_1000_v1`, seed 20260912, 2,000 processed, 0 errors, English pools from himalayas (699), keejob (700), rekrute (565), arbeitnow (33), remotive (2), and itjobs_pt (1). **Artifact.** This is the input catalog for the three runs below.

Shared files in the parent folder and in `blind_run_002_valid_contract/`: `all_job_scores.csv`, `candidate_language_normalization.json`, `candidate_normalization_report.json`, `candidate_technology_normalization.json`, `catalog_alignment_audit.csv`, `contract_diagnostics.md`, `contract_validation_report.json`, `contract_validation_report.md`, `duplicate_clusters.csv`, `fullstack_diagnostics.md`, `job_profiles_v2.jsonl`, `job_profile_quality_summary.json`, `language_diagnostics.md`, `manual_review_top_50.csv`, `qualification_missingness_audit.csv`, `remote_diagnostics.md`, `top_100_recommendations.csv`, `top_100_recommendations.json`, `top_30_recommendations.md`, `zero_experience_diagnostics.md`, plus that folder's own `evaluation_summary.md` and `run_metadata.json`.

The parent run and blind run 002 use the same profile hash and the same catalog. They differ on the work-mode gate. The parent scores 1,596 jobs (271 non-remote rejected). Blind run 002 scores 562 jobs (1,381 work-mode rejected, of which 1,110 are unknown work mode). **Artifact.** Blind run 002 is the stricter contract-and-work-mode pass.

`blind_run_003_v1_1_challenger/` compares `deterministic_v1` with `deterministic_v1_1_challenger`. `run_metadata.json` (15 Sep 2026) sets `challenger_status` to `MIXED`, scores 562 jobs, and says taxonomy and extraction were unchanged. `v1_vs_v1_1_comparison.md` says v1 is frozen and v1.1 only changes qualification reliability, seniority fallback, deduplicated presentation, and a job-only IDF index. Extra files versus the earlier runs: `all_job_scores_v1.csv`, `all_job_scores_v1_1.csv`, `duplicate_suppression_audit.csv`, `evaluation_summary_v1_1.md`, `qualification_reliability_audit.csv`, `seniority_fallback_audit.csv`, `technology_idf_audit.csv`, `top_100_v1.json`, `top_100_v1_1.json`, `top_30_v1_1.md`. **Artifact.** This is a challenger comparison on one profile. It is not a labeled gold evaluation.

### recommendation_gold_v1

A prepared annotation campaign that has not been labeled. `build_metadata.json`: 80 candidates, 3,547 pairs, 8/8 families, 70/118 leaves, `models_modified: false`, `ready_for_human_annotation: true`. `reports/dataset_summary.md` says the same and adds that the candidate fixtures are production-schema seeds, not CV parses. `annotation_progress.json` and `reports/annotation_progress.md`: **0 of 3,547 complete.** Pilot status is `PENDING_PILOT_ANNOTATION`.

`reports/v1_metrics.md`, `v1_1_metrics.md`, `v1_vs_v1_1.md`, `idf_ablation.md`, `missingness_ablation.md`, `seniority_ablation.md`, `slice_metrics.md`, `experience_quality.md`, and `annotation_agreement.md` all say `AWAITING_HUMAN_ANNOTATION`. They are placeholders. `annotation_quality.md` says no labels are generated automatically. **Documentation of an unfinished campaign.**

`annotation_blind.csv` and `annotation_completed.csv` are the same size (about 15 MB). Progress is still zero, so `annotation_completed.csv` is the empty template, not a finished gold file. `annotation_double_sample.csv` is the double-annotation subset. `annotation_pool.jsonl` (about 34 MB) is the pair pool. `gold_candidates.jsonl` is the 80 candidate fixtures. `xgb_ranker_dataset.parquet` is a feature table for a ranker that the eval metadata says was not used. **Artifact.** Do not treat any of these as adjudicated gold.

`batches/batch_001.csv` through `batch_017.csv` — locked pair templates. Header columns include `pair_id`, candidate leaf/parent/family, job title and description, and empty label fields `preference_fit_label`, `qualification_fit_label`, `overall_relevance_label`. **Artifact.**

`splits/train_candidates.json` (44), `validation_candidates.json` (17), `locked_test_candidates.json` (19). **Artifact.**

`pilot/` — the same campaign at pilot size. `pilot_readiness_report.md` is `PENDING_PILOT_ANNOTATION`. `pilot_agreement.json` has null kappa and 0 double-annotated pairs. `pilot_progress.json`, `pilot_label_distribution.md`, `pilot_selection_report.md`, `pilot_validation_report.json`, `synthetic_annotation_report.json`, `pilot_disagreements.csv`, and the pilot CSVs (`pilot_annotation_blind.csv`, `pilot_annotation_completed.csv`, `pilot_annotation_synthetic.csv`, `pilot_double_annotation.csv`, `pilot_double_annotation_synthetic.csv`, `pilot_candidates.json`) are the pilot copies. **Artifact.**

`synthetic/annotation_completed_synthetic.csv` and `annotation_double_synthetic.csv` — synthetic fills, named as synthetic. **Artifact.** They are not human labels. The quality report forbids treating automatic labels as gold.

---

## contract-type-dataset/

A standalone package for building an English, all-occupation contract-type dataset. It is not imported by `app/`, `apps/`, or `job-nlpv2`. `experiments/contract_type_ml` looks for older files named `contract_dataset_verified_1013.csv` and `contract_dataset_balanced_1170.csv`. Those names are not produced here.

The package's own quality report says the balanced export was not produced. `ready_for_training` is false. `data/final/` is empty.

```text
contract-type-dataset/
├── README.md, pyproject.toml, requirements.txt, .gitignore
├── configs/          labels, pipeline, sources
├── src/contract_dataset/
├── scripts/          one step per file
├── tests/test_core.py
├── data/
│   ├── input/raw/    usajobs, linkedin, jobicy
│   ├── interim/      normalized records and duplicate groups
│   ├── review/       the workbook a person is supposed to fill
│   ├── final/        empty
│   └── archive/it_filtered_20260918T234011Z/   the previous IT-only run
└── reports/
```

`pyproject.toml` names the package `contract-type-dataset` 0.1.0, Python ≥3.10, dependencies pandas, openpyxl, and PyYAML. Pytest puts `src` on the path. `requirements.txt` also lists pyarrow, beautifulsoup4, datasets, duckdb, rapidfuzz, and pytest. **Supporting, keep** with the package.

`.gitignore` ignores raw downloads, interim tables, the review csv/json, inspect dumps, preview PNGs, `data/final/`, and report csv/json. The large files are on disk anyway. `__pycache__` and `.pytest_cache` are generated. **Artifact, remove** those two caches.

### What the code does

`src/contract_dataset/schemas.py` closes the labels at `PERMANENT`, `FREELANCE`, `INTERNSHIP`, `FIXED_TERM`, and `UNKNOWN`. There is no `TEMPORARY` label. `UNKNOWN` is only a reviewed outcome. A final record must have a label in that set. **Active for this package.**

`evidence.py` turns explicit phrases into a candidate label and character offsets. Two different labels in one text become a conflict (`CONFLICTING_EVIDENCE`) and no candidate. **Active.**

`labeling.py` prefers an internal row that already has a verified label. Otherwise a source-field label and a text label that disagree become `PENDING` with reason `SOURCE_EVIDENCE_CONFLICT`. A missing signal stays unresolved. It does not pick a winner. **Active.**

`language.py` is a small English/other word list. It returns `en` when its own score is at least 0.55. It is not the fastText gate in `job_nlp/ingestion/preprocess/gate.py`. `configs/pipeline.yaml` sets `language_min_score: 0.72`, and nothing in the package reads that key. The live cutoff is the 0.55 inside `classify_language`. **Active, review** that unused yaml value before treating 0.72 as the gate.

`normalization.py` strips HTML to text and hashes the normalized text. `deduplication.py` clusters exact text hashes and title/company/location keys. `loaders.py` reads local JSONL plus the internal workbook, and tags a coarse `occupation_group` from title words (healthcare, engineering, and so on). Occupation is descriptive. It is not an eligibility filter. The internal workbook path is `CONTRACT_INTERNAL_XLSX`, defaulting to `C:\Users\Hzdou\Downloads\all_annotated_contract_type_0_2485_final.xlsx`. **Active on this machine only** until that path is set.

`pipeline.py` loads local sources, drops missing titles, text under 80 characters, spam, and non-English, then attaches candidates. `audit.py` counts labels and sets `ready_for_training` only when a final audit has every target label and no errors.

`configs/labels.yaml` — the five labels, a target of 500 accepted per class, and aliases. `contract` and `consultant` map to `FREELANCE`. `temporary` maps to `FIXED_TERM`. **Supporting.**

`configs/sources.yaml` — Hugging Face streams for USAJobs, LinkedIn, and Jobicy; DuckDB for open-apply; optional Kaggle Upwork; the internal xlsx; and local scraper adapters under `job_nlp/ingestion/` (Himalayas, TunisieTravail, Arbeitnow, RemoteOK, Remotive, ITJobs.pt, Rekrute). The current download script does not call those scrapers. **Supporting.** The scraper entries describe an older plan.

### Scripts

Run order is in the README. Each script is one step:

| Script | Role |
|---|---|
| `scripts/_common.py` | Puts `src` on the path and writes JSON |
| `scripts/reset_external_data.py` | Moves raw, interim, review, and reports into `data/archive/it_filtered_<stamp>/`. Refuses to run without `--archive --confirm` |
| `scripts/download_sources.py` | Streams at most 1,000 rows from USAJobs, LinkedIn, and Jobicy. Records open-apply and Upwork as skipped. Does not invent rows |
| `scripts/inspect_sources.py` | Counts local raw files |
| `scripts/normalize.py` | Writes normalized interim tables |
| `scripts/generate_candidates.py` | Writes `data/interim/candidates.jsonl` |
| `scripts/deduplicate.py` | Writes `duplicates.jsonl` and cluster ids |
| `scripts/build_review_queue.py` | CSV and JSON queue. Columns include `candidate_label`, evidence offsets, and an empty `final_label` unless the row is already `HUMAN_REVIEWED` |
| `scripts/build_review_workbook.mjs` | Turns that queue into the xlsx a person edits |
| `scripts/verify_review_workbook.mjs` | Checks the workbook |
| `scripts/apply_reviews.py` | Reads sheet `Review Queue` and requires `record_id`, `final_label`, `review_status` |
| `scripts/validate_labels.py` | Audit, not final |
| `scripts/build_balanced_dataset.py` | Reads `data/review/reviewed.jsonl`, which is not on disk, and balances toward 500 per class |
| `scripts/split_dataset.py` | 70/15/15 group-aware split into `data/final/` |
| `scripts/audit_final.py` | Final audit. This is what would set `ready_for_training` |
| `scripts/write_migration_report.py` | Compares the newest archive with the current candidates |

**Active scripts, keep.** `build_balanced_dataset.py` and `split_dataset.py` have not been run to a finished export.

`tests/test_core.py` checks the closed label set, a fixed-term evidence hit, a permanent-versus-freelance conflict, HTML normalization, the language function, and dedup. **Test, keep.**

### Current data and reports

Raw downloads, 1,000 records each: `data/input/raw/usajobs/records.jsonl` (about 54 MB), `linkedin/records.jsonl` (about 5 MB), `jobicy/records.jsonl` (about 7 MB). **Artifact.** Gitignore expects these to stay local.

Interim tables, same records in several formats: `candidates.jsonl` (3,511 candidates, about 27 MB), `duplicates.jsonl` (about 6 MB), `normalized.csv`, `normalized.jsonl`, and `normalized.parquet`. **Artifact.**

Review queue: `review_queue_all_occupations.csv`, `.json`, and `.xlsx` (about 10 MB). The `.xlsx.inspect.ndjson` is about 101 MB and `review_queue_all_occupations_preview.png` is a screenshot. **Artifact.** Keep the xlsx as the review surface. The inspect dump and the PNG are disposable.

`reports/candidate_audit.json` and `label_validation.json` agree: 3,511 English records, 1,872 `HUMAN_REVIEWED`, 1,639 `PENDING`, `ready_for_training: false`. Accepted labels so far are PERMANENT 36, FREELANCE 73, INTERNSHIP 31, FIXED_TERM 19, UNKNOWN 1,713, and 1,639 still null. Candidate labels are wider: PERMANENT 629, FREELANCE 102, FIXED_TERM 103, INTERNSHIP 46, UNKNOWN 1,713, unresolved 918. **Artifact.**

`reports/raw_counts_by_source.csv` — internal 2,486, plus 1,000 from each of Jobicy, LinkedIn, and USAJobs. `source_statistics.csv` — retained records are internal 1,872, LinkedIn 887, USAJobs 752. Jobicy contributed none of the 3,511. `rejection_reasons.csv` — 996 short or missing text, 893 duplicates, 86 non-English. `label_distribution.csv` matches the candidate counts. `candidate_label_by_source.csv` — most accepted UNKNOWN rows are the internal sheet (1,713). Most USAJobs candidates are PERMANENT (525). `candidate_label_by_occupation.csv` — the same counts split by the coarse occupation tag. `shortage_report.csv` — accepted counts versus a 500 final target. Every class except UNKNOWN is short by 427 to 481 accepted labels. `final_quality_report.md` states the export was withheld because 1,639 candidates are still pending. `all_occupations_migration_report.md` compares this run with the archived IT-filtered run (2,936 candidates then, 3,511 now, 0 occupation rejections). `download_sources.json` matches the downloader: three sources saved, open-apply skipped for a missing DuckDB loader, Upwork skipped for missing Kaggle credentials.

### Archived IT-filtered run

`data/archive/it_filtered_20260918T234011Z/` is the tree `reset_external_data.py` moved on 18 Sep 2026. `migration_baseline.json` records that move. Its raw cache has Jobicy, LinkedIn, USAJobs, and empty `open_apply` and `upwork` directories. Interim and review files are the older IT-filtered copies (`candidates.jsonl` about 26 MB, `review_queue.csv` / `.json` / `.xlsx`). Its `reports/source_statistics.csv` still includes the local scrapers: Himalayas 886, internal 1,872, TunisieTravail 68, LinkedIn 57, Arbeitnow 24, USAJobs 22, and one each of Rekrute and ITJobs.pt. **Artifact, keep** as the before-state of the migration report. Do not mix it with the current all-occupation queue.

---

## cv_parser/

**Active.** This is the Python package the FastAPI app on port 8000 calls. `app/api/routes.py` uses `extract_profile` for `POST /api/cv/parse` and `extract_candidate_profile` for `POST /api/cv/profile`. `apps/api` reaches it over HTTP, then seeds skills from `resources/skills/it_lexicon.json`. Version is `3.0.0`. The package states it is deterministic and CPU-only: PDF geometry first, then a lexicon. It does not run the occupation leaf pipeline.

There is no education extractor. Section headings named education are detected so they are not split into fake jobs, and the classifier comment says full education history is out of scope. The wizard's education step is filled by the user, which matches the Prisma comment on `CandidateEducation`.

Contract and work-mode words here are the web product's words: `CDI`, `CDD`, `INTERNSHIP`, `ALTERNANCE`, `FREELANCE`, `OTHER`, and `REMOTE` / `HYBRID` / `ONSITE`. They are not the job-extraction labels `PERMANENT` and `FIXED_TERM`.

```text
cv_parser/
├── __init__.py, config.py, errors.py, pipeline.py
├── document/          words, lines, blocks
├── ingestion/         PDF open, profile, PyMuPDF
├── layout/            columns, XY-cut, reading order
├── structure/         headings and section types
├── extractors/        identity, experience, preferences, languages, certifications
├── skills/            lexicon plus Nesta/tech v2
├── normalization/     dates, text, candidate profile
├── quality/           parse score and review checklist
├── schemas/           draft JSON and matching profile
├── matching/          confirmed profile plus survey
└── resources/         section aliases, language names, IT lexicon
```

`__pycache__` beside these modules is compiled bytecode. **Artifact, remove.**

### Entry and configuration

`__init__.py` exports `extract_profile` and `extract_candidate_profile` lazily. **Active.**

`pipeline.py` is the orchestrator. It loads the PDF, tries XY-cut reading order, and retries a simple order only when the quality score says the first pass may have scrambled the page. It then extracts identity, desired positions, contract and work-mode preferences, experience, skills, languages, and certifications, and returns a parser draft. `extract_candidate_profile` runs that draft through `normalize_candidate_profile`. **Active.**

`config.py` is a pydantic-settings object. Environment prefix is `CVPARSER_`. Defaults include a 20 MB / 15-page PDF limit, native-text quality bands, heading scores, and `skill_engine = "nesta_tech_v2"`. The other engine names in the skills package docstring are `hybrid` and `lexicon`. **Supporting, keep.**

`errors.py` — `CVParserError` plus empty file, invalid PDF, file too large, too many pages, password required, and malformed PDF. `app/api/routes.py` turns `CVParserError` into HTTP 400. **Active.**

### document, ingestion, layout

`document/models.py` — bounding box, word, line, and block. **Active.**

`document/geometry.py` — bbox normalize and union. **Active.**

`document/line_builder.py` — groups words into lines and blocks using the font-height gap in config. **Active.**

`document/deduplication.py` — drops words that sit on top of each other within `dedup_position_tolerance_pt`. **Active.**

`ingestion/validator.py` — opens the PDF and enforces size, page count, and password rules. **Active.**

`ingestion/pdf_profiler.py` — per-page native-text quality: `DIGITAL_GOOD` or a thinner/suspect/poor state, plus `ocr_required`. **Active.**

`ingestion/pymupdf_extractor.py` — reads words with PyMuPDF and builds the document. This is the ingestion entry `load_document`. **Active.**

`ingestion/ocr_fallback.py` — `run_ocr_on_page` raises `NotImplementedError`. The profiler can flag a page, and this function is not called from `load_document`. **Legacy stub.** Scanned CVs are flagged, not read.

`layout/regions.py` — a rectangular region. **Active.**

`layout/column_detector.py` — counts columns from horizontal gaps. **Active.**

`layout/xy_cut.py` — recursive XY-cut order. **Active.**

`layout/reading_order.py` — `assign_reading_order` for strategies `XY_CUT` and `SIMPLE`. **Active.**

`layout/quality.py` — layout status used by the adaptive retry. **Active.**

### structure and extractors

`structure/heading_detector.py` — scores a line as a heading from font size and bold ratio. A short `Label : value` line is data, not a heading. **Active.**

`structure/section_signatures.py` — structural patterns that classify a section when the heading text is not enough. **Active.**

`structure/section_classifier.py` — assigns section type and record spans. Record-bearing types are professional experience, internship, alternance, projects, and certifications. Education is folded so degree lines are not split, and it is not emitted as records. **Active.**

`structure/record_segmenter.py` — splits a section into one span per job, project, or certificate. **Active.**

`extractors/identity.py` — email and full name from the header. **Active.**

`extractors/location.py` — country and phone. Used by identity. **Active.**

`extractors/target.py` — desired positions from an explicit target, a headline, or a profile statement. **Active.**

`extractors/preferences.py` — contract and work mode only from a line that also says seeking, looking for, or the French equivalent. A past “Stage chez …” line is not a desired internship. **Active.**

`extractors/experience.py` — experience records, type (`PROFESSIONAL`, `INTERNSHIP`, `ALTERNANCE`, `FREELANCE`, `UNKNOWN`), and a union of durations. **Active.**

`extractors/languages.py` — language names and CEFR-style levels, using `resources/languages/language_names.json`. **Active.**

`extractors/certifications.py` — certificate rows and any technology mentioned on them. **Active.**

### skills

`skills/extractor.py` — walks sections and returns the skills block of the draft. Default path is Nesta plus technology taxonomy v2. **Active.**

`skills/nesta_tech_v2.py` — loads `job_nlp.skills.en_skill_stack.EnSkillStack` once and maps `TECHNOLOGY` versus `PROFESSIONAL_SKILL`. This is the live link from the CV parser into the job skill stack. **Active.** Depends on `job_nlp.skills`.

`skills/lexicon.py` — loads `resources/skills/it_lexicon.json` once. **Active** when the engine is `lexicon` or `hybrid`, and the API seed always reads the file directly.

`skills/models.py` — canonical skill and alias entry. Alias policy is `SAFE`, `CONTEXT_REQUIRED`, or `SYMBOLIC`. **Active.**

`skills/automaton.py` — Aho-Corasick over normalized aliases. **Active.**

`skills/boundaries.py` — rejects a match that is only part of a longer word. **Active.**

`skills/normalization.py` — match-text normalization and technology-list splitting. **Active.**

`skills/matcher.py` — one text blob: normalize, scan, check boundaries, disambiguate. **Active.**

`skills/disambiguation.py` — `CONTEXT_REQUIRED` aliases (for example `JS`, `C`, `Go`) need surrounding technical context. **Active.**

`skills/candidates.py` — a line that is a technology list (“Skills: Python, SQL”) is split instead of matched as one phrase. **Active.**

`skills/evidence.py` — merges hits into one skill with evidence spans, and keeps unmapped hits separate. **Active.**

### normalization, quality, schemas, matching

`normalization/text.py` — strip a heading line and other language-agnostic cleanup. **Active.**

`normalization/dates.py` — guarded date ranges. Precision is `YEAR`, `MONTH`, or `DAY`. Unknown stays empty. **Active.**

`normalization/candidate_profile.py` — draft JSON to `CandidateKnowledgeProfile`. Drops parse quality, review items, and meta. **Active.**

`quality/scoring.py` — scores a parse so the pipeline can choose XY-cut or simple order, then builds `parse_quality`. **Active.**

`quality/review.py` — a flat checklist of items the review form should show. **Active.**

`schemas/internal.py` — document, page profile, and page state. Not the HTTP body. **Active.**

`schemas/parser_response.py` — the draft the review form receives. Confidence is `HIGH`, `MEDIUM`, or `LOW`, not a float. `app/api/schemas.py` subclasses `ParserDraftResponse`. **Active.**

`schemas/verified_profile.py` — the matching profile. `JobFamily` here is a closed list of thirteen role names (`FRONTEND_DEVELOPER`, `BACKEND_DEVELOPER`, `FULLSTACK_DEVELOPER`, and so on, plus `OTHER`). That list is not the eight-family occupation taxonomy (`SOFTWARE`, `DATA_AI`, `SECURITY`, …). Seniority on this profile is `INTERN`, `JUNIOR`, `MID`, `SENIOR`, `LEAD`, `MANAGER`. **Active for the CV product.** Do not treat these family names as the leaf registry.

`matching/candidate_matching_adapter.py` — builds a `CandidateKnowledgeProfile` from a confirmed profile plus the preference survey. It calls `shared_matching.skill_identity.canonicalize_skill_name`. **Active.** Depends on `shared_matching`.

### resources

`resources/sections/aliases.json` — heading phrases in English, French, and Arabic for `PROFILE_SUMMARY`, `SKILLS`, `PROFESSIONAL_EXPERIENCE`, `INTERNSHIP`, `ALTERNANCE`, `PROJECTS`, `CERTIFICATIONS`, `LANGUAGES`, `EDUCATION`, `CONTACT`, and `IGNORED`. **Supporting, keep.**

`resources/languages/language_names.json` — names the language extractor recognizes. **Supporting, keep.**

`resources/skills/it_lexicon.json` — 188 canonical skills with aliases. The first entries are programming languages and frameworks (`Python`, `Java`, `JavaScript` with `JS` marked `CONTEXT_REQUIRED`, `C` and `Go` marked `CONTEXT_REQUIRED`). **Supporting, keep.** `apps/api/prisma/seed.ts` upserts this file into the `Skill` table. It is a CV lexicon, not the 118-leaf occupation catalog.

---

## data/

**Supporting placeholder.** Two files, no datasets.

`README.md` says this folder holds source, processed, taxonomy, and reference datasets, and that runtime knowledge-base resources must stay at their documented paths. The datasets that sentence describes are not here. They live under `job_nlp/data/`, `contract-type-dataset/data/`, `experiments/`, and `artifacts/datasets/`. **Documentation, review.** The README describes a role this directory does not currently fill.

`.gitkeep` is an empty file so git can track the directory. **Supporting, keep.**

`cv_parser/config.py` sets `DATA_DIR` to this folder and creates it on import (`mkdir` if missing). No parser module reads a file from it. The CV resources that are actually loaded sit in `cv_parser/resources/`.

Several scrapers use a relative `Path("data") / <source>` (`job_nlp/ingestion/rekrute_scraper.py`, `keejob_scraper.py`, `foreign_api_scraper.py`, and the others). That path follows the process working directory. It is this folder only when the scraper is started from the internship root. No `rekrute/`, `keejob/`, or similar subdirectory is present, so those scrapers have not left a cache here. `job_nlp.paths.DATA_DIR` is `job_nlp/data`, a different directory.

---

## docs/

Six short documents. They describe the repository as it was around 13–15 Sep 2026. Several statements no longer match the tree. **Documentation, review.** Keep them as a dated snapshot. Do not use them as the map of the current folders. This audit file is the later inventory.

```text
docs/
├── README.md
├── project_structure.md
├── active_file_manifest.md
├── cleanup_report.md
├── known_issues.md
└── superpowers/plans/2026-09-13-production-extraction-hardening.md
```

`README.md` says this folder holds architecture, runbooks, structure, cleanup records, an active-file manifest, and the accepted extraction backlog. The architecture and runbooks it names are not in this folder. Those longer documents, where they still exist, are under `job_nlp/docs/`. **Documentation.**

`project_structure.md` draws `job_nlp` as pipeline, extraction, taxonomy, knowledge base, config, and a reserved `recommendation/` namespace. It also says root `data/` holds source and processed datasets, `models/` holds local model repositories, and `archive/` is historical material that is never imported. The `data/` line is the empty placeholder documented above. `archive/` is ignored and not imported, and the directories this file’s siblings name under `archive/` are not on disk. The drawing omits `cv_parser`, `apps/`, `job-nlpv2`, and `contract-type-dataset`. **Documentation, review.**

`active_file_manifest.md` lists `job_nlp/pipeline/`, `job_nlp/taxonomy/`, and `job_nlp/extraction/` as the production core, plus config, the knowledge base, and `models/`. It calls `job_nlp/recommendation/` an empty Recommendation V1 namespace with no algorithm. That package now has `api.py`, `core.py`, `service.py`, `challenger_v1_1.py`, eligibility modules, and three config YAML files. The “empty namespace” line is stale. **Documentation, review.**

`cleanup_report.md` is dated 15 Sep 2026. It says 76 historical test files and one debug script were moved to `archive/pre_recommender_cleanup/tests/`, that no production module was archived, and that the taxonomy stayed 8 / 24 / 118 with decision layer `occupation_decision_v2_1`. The destination path `archive/pre_recommender_cleanup/` is not on disk. The 8 / 24 / 118 counts still match the live leaf registry. **Documentation, review.** The move it records cannot be checked from the current archive tree.

`known_issues.md` freezes the extraction baseline as `occupation_decision_v2_1` and lists unresolved work: role and domain ambiguity, deterministic contradictions, out-of-domain edges, leaf abstentions, parent and family fallback, candidate canonicalization, and score calibration. It says those items were not changed during the cleanup. **Documentation.** This is a backlog note, not a measured error list. The frozen leaf formula used later (70 / 15 / 15) is not mentioned.

`superpowers/plans/2026-09-13-production-extraction-hardening.md` is an implementation plan for the English job-offer API. It tells an agent to use a “superpowers:executing-plans” skill, keep the deterministic extractors and the calibrated family thresholds, cap title at 512 characters, description at 50,000, and metadata strings at 256, and make `/health` return `ok` or `degraded`. Every checkbox in the file is still empty. The bounds and the `degraded` status are present in `job_nlp/api/main.py`. The test file the plan names, `job_nlp/tests/test_api_production_hardening.py`, is not on disk. Task 3’s check for 7,377 enrichment records was not marked done. **Documentation.** The request-size limits landed. The plan file itself was not updated, and the named test was not added.

---

## exp-fn/

**Experiment.** A five-field classifier campaign on top of the rule extractors. It is not imported by `app/`, `apps/`, `cv_parser`, or `job-nlpv2`. The live extractors stay the deterministic ones. This tree is about 28 GB, almost all of it model checkpoints and Colab zip bundles under `artifacts/`.

The five fields and their labels are in `ontology/ontology_v1.json`:

| Field | Labels |
|---|---|
| `education_level` | UNKNOWN, ASSOCIATE, BACHELOR, MASTER_OR_HIGHER |
| `work_mode` | REMOTE, HYBRID, ONSITE, UNKNOWN |
| `contract_type` | UNKNOWN, PERMANENT, FIXED_TERM, FREELANCE, INTERNSHIP |
| `minimum_experience_bracket` | 0_YEARS, 1_2_YEARS, 3_5_YEARS, 5_7_YEARS, 8_PLUS_YEARS, UNKNOWN |
| `seniority_level` | INTERN_ENTRY, JUNIOR, MID, SENIOR, LEAD_PRINCIPAL, UNKNOWN |

Those contract and experience labels match the job-extraction enums, not the CV product’s `CDI` / `CDD`. `ontology/auxiliary_vocab.json` adds source tags `RULE`, `ML`, `HYBRID`, `UNKNOWN` and warning codes such as `RULE_ML_CONTRADICTION`. **Supporting for this experiment.**

`configs/runtime.yaml` pins Python 3.12.10, split seed 42, and `frozen_test: not_evaluated`. The ontology sha256 in that file is the same hash stored in `archive/exp-fn/artifacts/rules/rule_adapter_manifest.json`. Model configs name `microsoft/deberta-v3-small`, `jjzha/jobberta-base`, and `answerdotai/ModernBERT-base`, each with one classification head per field. `configs/protocol/` holds the campaign locks, selection rules, and one contract file per JobBERTa reduced bundle v1 through v5 plus the DeBERTa and ModernBERT sessions. **Supporting.** They describe the runs. They are not read by the live API.

```text
exp-fn/
├── datasets_clean_annotation_EN.xlsx
├── train-00000-of-00001 (2).parquet
├── requirements-colab.txt
├── ontology/
├── configs/
├── src/
├── scripts/
├── tests/
├── data/                 derived tables and adaptation corpora
├── artifacts/            audits, gates, checkpoints, Colab zips
├── outputs/              empty
├── .rule_work/           local install for one spreadsheet script
└── .pytest_cache/
```

`.pytest_cache/` is a test cache. **Artifact, remove.**

### Source and the rule adapter

`src/rules_adapter.py` calls the public `job_nlp` rule interface and checks that evidence offsets still match the title or description. It refuses URL-shaped evidence. **Experiment.** It is the bridge from this campaign back to the deterministic extractors.

`src/safe_logging.py` keeps raw title and description text out of logs. **Supporting.**

`requirements-colab.txt` pins Torch 2.5.1 from the CUDA 12.4 index and transformers 4.48.3. The internship `requirements.txt` pins a different transformers line (`<4.46`) and sentence-transformers 5.x. These two environments are not the same. **Supporting for Colab only.**

### Scripts

`scripts/run_phase_a.py` builds the derived tables from the workbooks without editing them. `run_phase_b.py` and `run_phase_b_smoke.py` prepare validation-only coverage. `execute_phase_b.py`, `finalize_phase_b.py`, `finalize_phase_b_gates.py`, `create_campaign_lock.py`, and `package_colab_phase_b.py` are the Phase-B campaign. **Experiment.**

`run_deberta_supervised_ablation.py` trains three DeBERTa variants: base, TAPT, and DAPT then TAPT. `run_jobberta_local_ablation.py` trains JobBERTa base and TAPT locally. **Experiment.**

The `build_*_colab_bundle.py` and `verify_*_bundle.py` pairs pack a train/validation-only zip for Colab and check its hash. There is one pair for DeBERTa, one for JobBERTa, one for ModernBERT, and five for “JobBERTa reduced” (v1 through v5). `v5` is a direct-RoBERTa finalizer that reuses the v4 algorithm with v5 names. Matching `*_colab_startup.py` and `*_colab_runner.py` files are the Colab session gate and the trainer. `jobberta_reduced_colab_execute.py` is the execution-enabled reduced campaign. **Experiment.** Later versions did not delete the earlier bundles.

`scripts/build_rule_results_workbook.mjs` reads `exp-fn/artifacts/rule_extraction_binary_workmode_v5/rule_extraction_results.json` and writes an xlsx under `exp-fn/outputs/`. That JSON is not in this tree. The same dump now lives under `archive/exp-fn/`. `outputs/` is empty, so this script has not been run against the current layout. `.rule_work/node_modules/@oai` is the install it needs. **Legacy script.** The node_modules tree can go with it.

### Data

`datasets_clean_annotation_EN.xlsx` — 1,118 rows, 7 columns, about 6 MB. This is the file the earlier root note thought was missing from the repo root. It lives here. The newer workbook at the repo root is `datasets_clean_annotation_EN_v2.xlsx`. **Artifact.** Phase A read this copy, not the v2 workbook.

`train-00000-of-00001 (2).parquet` — 141,897 rows, 10 columns, about 139 MB. The Phase-0 audit marks it `BLOCKED` because it has no `title` or `description` column. **Artifact, review.** It was accepted as a file and rejected as a job-text table.

`data/derived/` — `canonical_all.parquet`, `canonical_train.parquet`, `canonical_validation.parquet`, `canonical_test_frozen.parquet`. The frozen test file is present and the gate says it was not used for scoring. **Artifact.**

`data/adaptation/dapt_external_clean.parquet` (about 154 MB) and `tapt_train.parquet` (about 6 MB) are the continued-pretraining corpora. **Artifact.**

`data/manifests/split_manifest_local_v1.json` and `split_manifest_colab_train_validation_v1.json`, each with a `.sha256`. **Artifact.** `tests/test_phase_a_b.py` checks those hashes.

There is no `exp-fn/data/processed/`. The archived experience report that names `exp-fn/data/processed/dataset_min_experience_grounded.xlsx` is still pointing at a missing path.

### Artifacts and what the runs actually scored

`artifacts/gates/gate_state.json` says `PHASE_A_COMPLETE` as of 22 Sep 2026, next allowed gate `CONTINUE_ML_PREP`, frozen test `UNUSED`. Checkpoint folders and ablation CSVs from later training are already on disk, so this gate file was not advanced when those runs finished. **Artifact, review.** Do not treat the gate as the full history of the folder.

`artifacts/audits/` — input inventory, canonical audit (3,585 groups, 0 conflicts, leakage PASS), grouping audit, split audit, near-duplicate list. `input_inventory.md` says raw titles are not in the report. **Artifact.**

`artifacts/coverage/` — a 512-token coverage diagnostic on train and validation only. **Artifact.**

`artifacts/local_preparation/` — environment, model inventory, smoke results, and a short pytest note. Preflight records Python 3.12.10 and CUDA available. **Artifact.**

`artifacts/adaptation/adaptation_ablation_report.md` says the required ablation was registered and not executed, and that no scores were invented. That sentence is the early local-prep note. The CSV beside it, `deberta_supervised_ablation_results.csv`, is a later completed run. Validation mean macro-F1, frozen test not touched:

| Variant | Mean five-field macro-F1 |
|---|---:|
| DeBERTa base | 0.606 |
| DeBERTa TAPT | 0.652 |
| DeBERTa DAPT+TAPT | 0.642 |

Per-field, education is the high field (about 0.81–0.83) and minimum experience is the low one (about 0.36–0.43). **Artifact.** These are validation numbers on this split. They are not a production score and they are not the frozen-test score. The report says the frozen test was not accessed.

`jobberta_supervised_ablation_report.md` — JobBERTa base mean macro-F1 0.665, TAPT 0.658. The file keeps **base**, because the rule prefers the simpler path when the two are within 0.005. **Artifact.** Same limit: validation only.

Checkpoint directories, each a Hugging Face save (config, tokenizer, weights):

- `artifacts/adaptation/checkpoints/deberta_v3_small/` under `dapt`, `tapt`, and `dapt_tapt`
- `artifacts/adaptation/checkpoints/jobberta_base/tapt/` with numbered checkpoints plus two `.tmp` checkpoint folders
- `artifacts/models/ablation/deberta_v3_small/base/screening_lr_1e-05_seed_42/best`
- `artifacts/models/deberta_supervised_ablation/{base,tapt,dapt_tapt}/best`
- `artifacts/models/jobberta_supervised_ablation/{base,tapt}/best`

**Experiment weights.** Nothing in the live extraction path loads them. The two `.tmp` JobBERTa folders are incomplete copies. **Review for deletion** once one retained checkpoint per variant is chosen. The gate’s retained JobBERTa path is base, and the best DeBERTa validation score in the CSV is TAPT.

`artifacts/colab/` — zip bundles and their sha256 and verification JSON. `deberta_colab_bundle.zip` is about 536 MB. The JobBERTa and ModernBERT bundles are about 6 MB each, and the reduced JobBERTa line repeats that zip for v1 through v5. `deberta_bundle_chwo_zg9/deberta_tapt_checkpoint/` is an unpacked checkpoint. `package_colab_phase_b.py` also expects `exp_fn_colab_bundle.zip`, which is not in this listing. **Artifact.** Keep one verified bundle per model if a Colab rerun is still planned. The v1–v4 reduced bundles are successive copies.

Logs in `artifacts/adaptation/` (`*.log`, `*.err`, including empty `phase_b_resume.log` and `phase_b_strict_v2.log`) record process output. `phase_b_strict_v3.err` is the non-empty error log of that name. **Artifact.**

### Tests

`tests/test_phase_a_b.py` checks the ontology field order and the split-manifest hashes. `test_phase_b_protocol.py` checks the campaign bundle path. `test_deberta_precision_policy.py`, `test_deberta_tokenizer_preflight.py`, and `test_jobberta_preflight.py` are startup checks. `test_jobberta_reduced_inference.py` and `_v2.py` cover the reduced bundle. `test_modernbert_campaign_bundle.py` covers the ModernBERT bundle. **Tests, keep** with the experiment. They do not guard `job-nlpv2`.

---

## experiments/

**Experiment.** Four isolated DeBERTa packages, one per field, plus two large CSV inputs at the folder root. Nothing in `app/`, `apps/`, `cv_parser`, or `job-nlpv2` imports this tree. Each package says it does not replace the production extractor. The scores below are the numbers written in each package’s own report. They are not a production measurement of `job-nlpv2`.

```text
experiments/
├── folloz contract extraction.txt
├── contract_dataset_verified_1013.csv
├── postings.csv
├── contract_type_ml/
├── education_ml/
├── minimum_experience_ml/
└── work_mode_ml/
```

`folloz contract extraction.txt` is the brief for the contract experiment (the filename is spelled that way). It asks for rules, scratch DeBERTa-v3-small, LinkedIn domain-adaptive pretraining, and a hybrid, on a 1,013-row labeled set plus a 123k LinkedIn export. **Documentation.**

`contract_dataset_verified_1013.csv` — about 5 MB. Header: `title`, `description`, `contract-type`, `evidence`. The first row is an NHS administration post labeled `FIXED_TERM`, and the evidence cell includes a source URL. The contract README says this is the 1,013-row verified set. It sits in `experiments/`, not in `contract_type_ml/data/raw/`, which is where the brief said to put it. `prepare_data.py` searches both places. **Artifact, keep** as the labeled contract set for this experiment.

`postings.csv` — about 493 MB. Header starts `job_id, company_name, title, description, … formatted_work_type, work_type`. This is the LinkedIn export the README calls `linkedin_123k.csv`. The README says the DAPT corpus reuses a 123,849-record decontaminated export so the full file is not copied again. **Artifact.** It is unlabeled domain text, not the 1,013-row gold file.

Each package has a `.pytest_cache`. **Artifact, remove.**

### contract_type_ml

Labels in `config/config.yaml`: `PERMANENT`, `FREELANCE`, `INTERNSHIP`, `FIXED_TERM`, `UNKNOWN`. Seed 42, split 70/15/15, model `microsoft/deberta-v3-small`, hybrid abstains below confidence 0.65. **Experiment.**

`src/prepare_data.py` builds the split and the DAPT text. `src/dapt_pretrain.py` continues masked-language training. `src/train_classifier.py` trains scratch or DAPT modes. `src/rule_extractor.py` and `src/rule_wrapper.py` wrap the deterministic contract extractor. `src/hybrid_resolver.py` keeps a model label only at confidence ≥ 0.65 and otherwise keeps the rule evidence. `src/evaluate_ablation.py` writes the report. **Experiment.**

`reports/benchmark_comparison.md`, on the frozen test the README sizes at 152 rows:

| Pipeline | Macro F1 | Accuracy |
|---|---:|---:|
| rule | 0.719 | 0.697 |
| ml_scratch | 0.893 | 0.895 |
| ml_dapt | 0.834 | 0.836 |
| hybrid | 0.843 | 0.842 |

Scratch beat both DAPT and the hybrid on that split. `ablation_metrics.json` and `error_analysis.csv` are the per-class detail. **Artifact.**

`data/processed/dapt_corpus.txt` and `dapt_pretrain_corpus.txt` are the same size, 478 MB each. **Artifact, review.** One of the two is enough. Checkpoints with weights: `classifier_dapt` and `classifier_scratch` at about 552 MB each, `deberta_v3_dapt` at about 928 MB. Several `checkpoint-*` folders and `classifier_dapt_final`, `classifier_dapt_verified`, and `deberta_v3_scratch` measured empty. **Experiment weights.** The live contract extractor does not load them.

### education_ml

A package `education_ml` for four outputs: level (`UNKNOWN`, `ASSOCIATE`, `BACHELOR`, `MASTER_OR_HIGHER`), requirement (`REQUIRED`, `PREFERRED`, `UNSPECIFIED`), an experience-in-lieu flag, and a verbatim evidence span. The model ranks candidate sentences. A separate resolver turns the chosen sentence into the enum. Engineering, Master, PhD, and Bac+5 map to `MASTER_OR_HIGHER`. An explicit “Bachelor's or Master's” maps to `BACHELOR`. **Experiment.**

`src/education_ml/rule_adapter.py` does not call `job_nlp`. It calls this package’s own `enum_resolver`. The README’s prepare step points at `C:\Users\Hzdou\Downloads\all_annotated_education_0_2485_final.xlsx`. `scripts/migrate_education_dataset_to_4class.py` also looks for `exp-fn/balanced_education_dataset_2546.xlsx` and a copy under this package. **Experiment.**

Tests cover the resolver, segmentation, the rule adapter, and split leakage. **Tests, keep** with the package.

`artifacts/metrics/comparison_metrics.csv` is 260 test documents. Exact level accuracy: rules 0.865, ML 0.962, hybrid 0.888. `selected_threshold.json` picks 0.45 on 254 validation documents (positive-candidate F1 0.948). **Artifact.** On this split the sentence ranker beat the hybrid. `artifacts/models/best` is about 549 MB. **Experiment weights.**

### minimum_experience_ml

Predicts the minimum professional experience in months. `null` means no explicit minimum. `0` is only an explicit “no experience required”. A title word such as Junior or Intern is not enough. The model labels a candidate span as required-minimum or not. `number_parser.py` then reads months from that span. **Experiment.**

`src/min_experience_ml/rule_adapter.py` wraps `job_nlp.extraction.seniority_experience_extractor.SeniorityExperienceExtractor` and does not change it. `prepare_internal_data.py` reads `C:\Users\Hzdou\Downloads\all_corrected_offers_0_2485_with_seniority.xlsx`. `configs/default.yaml` leaves `weak_enabled` and `green_enabled` false. The README says the workbook is not copied into the repo.

`data/raw/green/` is a copy of the LREC 2022 job-description NER corpus by Green, Maynard, and Lin, including `raw_data/answers.txt` (about 14 MB), `testset.txt`, a CRF baseline under `baseline/`, and preprocessing scripts. **Artifact.** It is a public benchmark dropped into the experiment. Default config does not train on it. `artifacts/domain_pretrain/green_token/` and `weak_candidate/` still hold checkpoints from runs that did, including `weak_candidate/models/20260917T140153Z/best`, which is the initialization path named by `artifacts/models/20260917T140922Z` at the repo root.

`artifacts/metrics/comparison_metrics.csv`: the rule row has requirement F1 0.942 and month-exact accuracy 0.876. The ML row is requirement F1 0.0 and 92 `CLASSIFIER_FALSE_NEGATIVE` errors, so that saved model did not mark required-minimum spans. The hybrid row matches the rule row. **Artifact.** This comparison says the hybrid added nothing over the rules. It is a different file from the later evidence-F1 0.918 checkpoint recorded under root `artifacts/models/`.

Weight-bearing saves are about 143 MB for the smoke runs and about 278–549 MB for the domain-pretrain and weak-candidate runs. **Experiment weights.**

Tests cover the number parser, segmentation, split leakage, the rule adapter, and transfer. **Tests, keep** with the package.

### work_mode_ml

One label among `REMOTE`, `HYBRID`, `ONSITE`, and `UNKNOWN`. The README says `UNKNOWN` is not turned into onsite. Phrases such as “hybrid cloud”, “remote desktop”, and “remote interview” are excluded. An immediate onsite requirement wins over a future hybrid option. Input is a local parquet `data/raw/jobs_aramente_latest.parquet` named in `config/config.yaml`. **Experiment.**

`src/download_and_filter.py` builds the English corpus. `src/dapt_pretrain.py`, `src/train_classifier.py`, `src/hybrid_resolver.py`, and `src/evaluate_ablation.py` mirror the contract package. `src/rule_wrapper.py` calls the deterministic work-mode extractor. Confidence gate in the config is 0.70. `tests/test_work_mode.py` is the package test. **Experiment. Test, keep.**

`reports/benchmark_comparison.md`:

| Pipeline | Accuracy | Macro F1 |
|---|---:|---:|
| RULE | 0.739 | 0.737 |
| SCRATCH | 0.639 | 0.631 |
| DAPT | 0.578 | 0.576 |
| HYBRID | 0.767 | 0.765 |

On this split the hybrid is a small step above the rules, and both model-only runs are below the rules. `data/processed/dapt_pretrain_corpus.txt` is about 41 MB. Checkpoints `dapt`, `deberta_v3_dapt`, and `scratch` are about 549 MB each. **Experiment weights.** The live work-mode extractor in `job-nlpv2` does not load them.

---

## job_nlp/

**Active package**, version `1.0.0` in `__init__.py`. This is the English job-offer service. `extract_job` and `JobNLPService` load from `pipeline/job_extraction_pipeline.py`. The public skill path is Nesta plus technology taxonomy v2. Occupation resolution is still Decision Layer `occupation_decision_v2_1` inside this package. The frozen 70/15/15 leaf formula lives in `job-nlpv2`, which this service does not call.

`docs/REPOSITORY_LAYOUT.md` says `job_nlp/` is the single home for active extraction. That was true when it was written. The field extractors below are now thin loaders. Their code is in `job-nlpv2`.

About 705 files. This section covers the package root, source, and `data/`. `artifacts/` (224 files, 207 of them reports) is named and not opened file by file.

```text
job_nlp/
├── README.md, README_JOB_EXTRACTION_FINAL.md, CHANGELOG.md, requirements.txt
├── __init__.py, paths.py, family_crosswalk.py
├── api/  config/  contracts/  pipeline/  extraction/  skills/
├── taxonomy/  preprocessing/  rules/  fusion/  structured/  schemas/
├── ingestion/  knowledge_base/  recommendation/  matching/
├── models/  scripts/  tests/  docs/  v2/  experiments/  investigation/
├── data/  leaf relations/
└── artifacts/     not opened file by file in this pass
```

`__pycache__/` is empty or compiled bytecode. **Artifact, remove.**

### Package root

`README.md` points at the Nesta plus v2 skill stack and at `docs/REPOSITORY_LAYOUT.md`. **Documentation.**

`README_JOB_EXTRACTION_FINAL.md` is the skill contract. English only. Skills are Nesta spans classified as technology or professional skill, plus full-text recovery from `data/technology/v2/IT_TECH_TAXONOMY_V2_RUNTIME.csv`. ESCO skill mapping is off. `skills_only: true` on `POST /api/v1/jobs/extract` returns `professional_skills` and `technologies`. Nesta is `ojd-daps-skills==3.0.0` installed with `--no-deps`, and `skops` must stay below 0.10. **Documentation, keep.**

`requirements.txt` pins that stack: FastAPI, torch, sentence-transformers 5.5–6, transformers 4.45 up to but not including 4.46, tokenizers below 0.21, spaCy, RapidFuzz, opencv below 5 so NumPy stays on 1.x. This is the job-service environment. It is not the Colab pin in `exp-fn/requirements-colab.txt`. **Supporting, keep.**

`CHANGELOG.md` records 22 Sep 2026 rule/ML alignment: the five-field ontology under `contracts/`, evidence offsets, and updates to education, work mode, contract, seniority, and minimum experience. **Documentation.**

`paths.py` is the path table. `DATA_DIR` is `job_nlp/data`, not the empty root `data/`. It also points at taxonomy JSON, the v2 technology CSVs, seniority rules, parent and leaf model dirs under `artifacts/models`, and skill-NER paths under `data/ner`. Several of those NER and model paths are from older phases. **Supporting.** A missing path here fails only when that phase is run.

`family_crosswalk.py` builds an exact leaf-id map from `data/taxonomies/job_family_taxonomy_v1_1.json` onto `knowledge_base/it_knowledge.sqlite`. Unmatched leaves abstain. **Active** for that crosswalk. It is not the 70/15/15 scorer.

### What actually runs an offer

`api/main.py` is a FastAPI app titled “Job NLP Extraction EN_V1”. Every request goes through the preprocessing gate. A refusal does not call `JobNLPService`. Title is capped at 512 characters, description at 50,000, metadata strings at 256. `/health` returns `ok` or `degraded`. The service loads with `JOB_NLP_LEAF_MODE` defaulting to `production`. **Active.** This is the job API, separate from the CV API in `app/` on port 8000.

`ingestion/preprocess/gate.py` — ACCEPT or REFUSE only. No REVIEW state. **Active.**

`ingestion/preprocess/text.py` — HTML to text, then the confirmation chunks. **Active.**

`ingestion/preprocess/language.py` — one fastText lid.176 model per process. A missing model refuses. **Active.**

`ingestion/preprocess/config.py` and `ingestion/config/preprocess_gate.yaml` — the 0.95 / 0.80 thresholds. **Supporting.** Do not treat a move of this package as safe: the gate finds the yaml and the model from its own file path.

`ingestion/preprocess/integrate.py` — calls extraction only after ACCEPT. **Active.**

`ingestion/preprocess/adapters.py` — maps a stored scrape or an API body onto the gate input. **Active.**

`pipeline/job_extraction_pipeline.py` — about 100 KB. The orchestrator: cleaning, language check, structured fields, Nesta skills, and occupation resolution. **Active.**

`pipeline/schemas.py`, `pipeline/validator.py`, `pipeline/conflict_resolver.py` — the result objects, validation, and field conflicts. **Active.**

`pipeline/README.md` says the pipeline is frozen at `occupation_decision_v2_1`. **Documentation.**

`schemas/normalized_job_offer.py` — the public offer schema. **Active.**

`preprocessing/cleaner.py`, `job_sections.py`, `long_text.py`, `model_text.py`, `text_builder.py` — text cleanup and the string the occupation model sees. **Active.**

`skills/en_skill_stack.py` — Nesta plus v2 recovery. This is what `cv_parser/skills/nesta_tech_v2.py` loads. **Active.**

`skills/nesta_extractor.py` — Nesta spans. **Active.**

`skills/requirement_classifier.py` — REQUIRED, PREFERRED, or UNSPECIFIED. The public skills-only response omits these buckets. **Active.**

`skills/technology_v2.py` and `skills/technology_matching_policy.py` — loaders. The code is `job-nlpv2/technologies/`. **Active re-export.**

`skills/tech_lexicon_precision.py` — older lexicon precision helper. **Review.** The final README says the V1 lexicon is not on the skill path.

### Extractors that moved

These files only load `job-nlpv2` and re-export its names. Editing them does not change behavior.

| File here | Implementation |
|---|---|
| `extraction/contract_type_extractor.py` | `job-nlpv2/contract/contract_type_extractor.py` |
| `extraction/work_mode_extractor.py` | `job-nlpv2/work_mode/work_mode_extractor.py` |
| `extraction/seniority_experience_extractor.py` | `job-nlpv2/experience/seniority_experience_extractor.py` |
| `extraction/education/extractor.py` and `__init__.py` | `job-nlpv2/education/` |

`extraction/language_extractor.py` and `extraction/language_cli.py` are still local. **Active.**

`extraction/README.md` still says these modules are the runtime implementations and must stay behavior-compatible. The implementations have moved. **Documentation, review.**

`rules/` is the older regex layer the pipeline still imports for some fields (`rules/__init__.py` exports certifications into the pipeline). Files: `base.py`, `contract.py` (CDI/CDD style, prefer UNKNOWN), `education.py`, `experience.py` (bracket wrapper), `seniority.py`, `work_mode.py` (COVID and temporary remote negatives), `title_rules.py`, `languages.py`, `certifications.py`, `country.py` (metadata only). **Active where the pipeline imports them. Review** against the `job-nlpv2` extractors so the two copies do not drift. The archived copies under `archive/*/investigation` are the same generation of rules.

`contracts/ontology.json` and `ontology.py` — the five-field label set used by `exp-fn`: education, work mode, contract (`PERMANENT` / `FIXED_TERM` / …), experience brackets, seniority. `adapters.py` and `business_policy.py` are the rule-first hybrid and `to_bracket()`. **Active** for that alignment. The CV product’s `CDI` / `CDD` enums are a different list.

`config/production_en_v1.yaml` — `skill_extractor_mode: nesta_tech_v2`, ESCO mapping false, no translation. **Supporting.**

`config/occupation_decision_v2.json`, `leaf_calibration_policy_v1.json`, `pipeline_defaults_v1.json`, `labels_v1.json`, `business_rules_v2.json`, `seniority_rules_v1.json`, `loader.py`. **Supporting.** Seniority rules here are the title-seniority patterns. The experience extractor’s year brackets do not read this file.

### Occupation resolution

`taxonomy/decision_layer_v2.py` — evidence fusion for `occupation_decision_v2_1`. **Active.**

`taxonomy/semantic_resolver.py` — embedding fallback. It reads the enriched profile JSON at the repo root. **Active.** A second copy of that JSON sits under `job-nlpv2` and can drift.

`taxonomy/title_vector_resolver.py` — nearest reviewed title. **Active** as a fallback.

`taxonomy/engine.py`, `loader.py`, `collision_rules.py`, `calibration_policy.py`, `title_normalization.py`, `model_identity.py`. **Active** pieces of the same resolver. `collision_rules.py` matches the older file kept under `archive/leaf/investigation`.

`taxonomy/README.md` and `README_SEMANTIC_FAMILY.md`. **Documentation.**

`taxonomy/corrections/` — five manual taxonomy files, including `title_leaf_parent_family_v2_manual_complete.json` (about 1.7 MB) and `titles_1445_complete_taxonomy_mapping_v2_enriched.csv` (about 1 MB). **Artifact, keep** as the correction record. They are not the 118-leaf registry CSV at the repo root.

`fusion/job_family_resolver.py`, `parent_resolver.py`, `leaf_resolver.py`, `job_family_consistency.py`, `seniority_resolver.py`. **Legacy inside the package.** Same roles as `archive/leaf/investigation/10_job_family_parent_leaf` and the seniority resolver. The pipeline README names Decision Layer v2, not this fusion package, as the frozen occupation path.

`models/job_family_parent/train_tfidf_svm.py`, `train_xlmr.py`, `losses.py` and `models/job_family_leaf/train_tfidf_leaf.py`, `registry.py` and `models/seniority/train_tfidf.py` are the training scripts for those older classifiers. **Experiment.** `paths.py` still points at their output under `artifacts/models`.

`structured/fields.py`, `occupation_esco.py`, `pipeline.py` — structured field assembly and an ESCO occupation CSV at `data/resources/esco/ESCO_IT_OCCUPATIONS_RUNTIME.csv`. **Active** for structured fields. The final skill README says ESCO is not used to map skills.

### Ingestion

Scrapers, each writing under a relative `data/<source>` when run from the working directory:

| File | Board |
|---|---|
| `rekrute_scraper.py` | Rekrute, all occupations. Contains `english_offer_url` and `visible_description` |
| `keejob_scraper.py` | Keejob |
| `tunisietravail_scraper.py` | TunisieTravail WordPress API |
| `france_travail_scraper.py` | France Travail |
| `itjobs_pt_scraper.py` | ITJobs.pt |
| `foreign_api_scraper.py` | Arbeitnow, Himalayas, RemoteOK, Remotive, no API key |

`it_filter.py` and `market_filter.py` decide IT and Maghreb-reachable posts. `build_corpus.py`, `build_dual_corpora.py`, `run_dual_pipeline.py`, `fill_fields.py`, `inspect_fields.py`, `scrape_config.py`. **Active** as the scrape toolkit. The English IT board used for the later 100-offer scrape is not what `iter_live_urls` lists. That method still uses the French listing template.

`ingestion/data/` holds `_state.json` files for arbeitnow, himalayas, remoteok, and remotive, plus `corpora/build_summary.json`. The offer JSONL files are not in this listing. **Supporting.** RemoteOK and Remotive state files are 2 bytes.

`ingestion/.git/` is a nested git directory inside the package. **Review.** It is not the internship repository’s `.git`.

`ingestion/README.md` is about 350 KB. **Documentation.** Too large to treat as a short guide. It is a scrape log as much as a readme.

### Knowledge base and leaf relations

`knowledge_base/it_knowledge.sqlite` — about 145 MB. The relational taxonomy `family_crosswalk.py` reads. **Active data.**

`knowledge_base/src/` — builders and migrations: `it_kb.py`, `build_from_sources.py`, `policy.py`, eight-family consolidation, taxonomy correction v2, residual consolidation, generic-leaf retirement, application-developer removal, cloud/platform merge. **Supporting scripts.** They rewrite the sqlite file. They are not called on each offer.

`knowledge_base/exports/` — CSV dumps (skill catalog, skill domains, reviewed titles, technology coverage). The largest are `skill_domains.csv` (about 5 MB) and `skill_parent_candidates.csv` (about 4 MB). **Artifact.**

`knowledge_base/custom_sources/leaf_profiles/batch_01` through `batch_04` — profile JSON for leaves that were unprofiled. **Supporting data.**

`knowledge_base/docs/` — `DATA_DICTIONARY.md`, `INTEGRATION.md`, `BUILD_REPORT.md`, coverage and validation JSON. **Documentation.** `INTEGRATION.md` still points at `archive/job_nlp/taxonomy_migrations/`, which is not on disk.

`knowledge_base/examples/candidate.json` and `job.json`. **Documentation.**

`leaf relations/` — a folder whose name contains a space. `definitions.csv`, `main_tasks.csv`, `leaves (2).csv`, `leafs (5).csv`, `technologies (8).csv` (about 660 KB). **Artifact.** The frozen leaf path uses technology-name cosine, not a vote over `technologies (8).csv`.

### Recommendation

`recommendation/` is no longer the empty namespace `docs/active_file_manifest.md` describes. `README.md` says it ranks English IT jobs from extraction output and does not change occupation extraction. Preference score P and qualification score Q are fused. Unknown job fields drop out of the score instead of counting as failures. **Active code, unlabeled gold.** The campaign in root `artifacts/recommendation_gold_v1` is still 0 of 3,547 labeled.

`core.py` (about 30 KB), `service.py`, `api.py`, `challenger_v1_1.py`. Config: `recommendation_v1.yaml`, `recommendation_v1_1.yaml`, `feature_schema_v1.yaml`. Eligibility, features, scoring, ranking, explanations, logging, and schemas are small modules, one concern each. `models/xgb_ranker.py` is present. The Hazem Douzi run metadata said XGBoost was not used. **Active for the deterministic ranker. Review** the ranker file so it is not mistaken for the path that produced those scores.

`evaluation/gold_framework.py`, `run_hazem_douzi.py`, `run_blind_run_003.py`, annotation workflow and synthetic annotations. **Experiment.** These wrote root `artifacts/recommendation_eval` and `recommendation_gold_v1`.

`recommendation/tests/test_recommendation_v1.py`, `test_recommendation_v1_1.py`, `test_gold_framework.py`. **Tests, keep.**

### Data

`data/04_job_extraction_pipeline_working_v1.csv` — about 25 MB. The working extraction table named in `paths.py`. **Artifact.**

`data/english_common_lemmas.txt` — about 86 KB. **Supporting.**

`data/taxonomies/job_family_taxonomy_v1_1.json` — about 290 KB. The taxonomy `family_crosswalk.py` and the old engine load. The archive copy of this era had 510 leaves and 35 parents. The live registry used by the frozen leaf path is 118 / 24 / 8. **Supporting, review** which file a given script opens before treating this JSON as current.

`data/technology/v2/IT_TECH_TAXONOMY_V2_RUNTIME.csv` — about 590 KB. Header `tech_id, canonical_name, aliases, matching_policy, category, sources`. This is the technology list the skill stack recovers. **Supporting, keep.**

`data/technology/v2/IT_TECH_TAXONOMY_V2_TECH_ONLY.csv` — about 2.9 MB. The wider table. **Supporting.**

`data/technology/v2/DEACTIVATIONS.md` — records removal of generic tokens such as `architect`, `basic`, and `edge` from the runtime file. **Documentation.**

`data/resources/esco/ESCO_IT_OCCUPATIONS_RUNTIME.csv` and `ESCO_IT_SKILLS_V1.csv` (about 4 MB). **Supporting** for the ESCO occupation helper. Not the skill mapper. The final README turns that mapper off.

`data/v2/active/english/keejob_en.jsonl` and `rekrute_en.jsonl` — about 2.3 MB each. The English pools later samples read. **Artifact, keep.**

`data/v2/archive/french/` and `mixed/` are present as directories. No files were in them in this listing. **Review.**

`data/v2/processed/linker/esco_catalogue_v121.csv` — about 5 MB. Input to `scripts/esco_linker_phase_b.py`. **Artifact.**

`data/resources/tech_lexicon/` is an empty directory in this listing. **Review.**

### Scripts, tests, docs, leftovers

`scripts/` — 57 one-off runners. They are not imported by the API. Groups:

- Corpus and hierarchy exports: `export_it_english_2486_csv.py`, `export_english_raw_dataset.py`, `export_all_scraped_raw_dataset.py`, `export_full_hierarchy_compact.py`, `export_500_hierarchy_compact.py`, `export_title_hierarchy.py`, `export_title_hierarchy_eight.py`, `export_title_hierarchy_151.py`, `export_138_28_12_hierarchy.py`, `export_title_leaf_parent_family.py`, `merge_it_english_raw_datasets.py`, `filter_english_datasets.py`, `filter_english_hierarchy_compact.py`.
- Sample runs of `JobNLPService`: `run_full_dataset.py`, `run_random_1000_unlabeled.py`, `run_2000_hierarchy_multisource.py`, `run_500_hierarchy_multimode.py`, `run_himalayas_100_extraction.py`, `run_random_50_final.py`, `run_it_kb_random_20.py`, `run_mixed_200_skills_family.py`, `rerun_previous_20.py`, `sample_en_tn_ma_quality.py`.
- Skills and ESCO experiments: `extract_skills_from_dataset.py`, `extract_skills_all_offers.py`, `compare_ours_vs_nesta.py`, `esco_linker_phase_b.py`, `eval_span_baseline_t0.py`, `benchmark_esco_xlmr.py`.
- Leaf and vector studies: `analyze_leaf_errors.py`, `audit_enriched_leaf_profiles.py`, `rebuild_enriched_leaf_vectors.py`, `evaluate_enriched_leaf_vectors.py`, `evaluate_title_vector_nn_100.py`, `evaluate_taxonomy_vector_evolution.py`, `evaluate_family_leaf_hybrid_100.py`, `match_title_vectors.py`, `export_leaf_profiles_compact_json.py`, `export_leaf_evidence_json.py`, `split_leaf_evidence_by_family.py`, `calibrate_semantic_family.py`, `build_gold_100_it_offers.py`, and the retirement refresh scripts.
- Annotation and rule alignment: `evaluate_rule_alignment.py` (reads the root annotation workbook), `review_annotations_500.py`, `review_quality_annotation_set.py`, `build_job_quality_annotation_draft.py`, `evaluate_job_quality.py`, plus the education-dataset builders.

**Experiment scripts, keep** only the ones you still rerun. `run_full_dataset.py` is the one that still walks the live gate.

`tests/test_preprocess_gate.py`, `test_preprocess_integration.py`, `test_rekrute_visible_description.py`, `test_rule_ml_alignment.py`, `test_skill_title_extraction.py`. **Tests, keep.** These guard the gate, the visible Rekrute description, and the rule alignment. They do not guard the 70/15/15 leaf formula.

`docs/PRODUCTION_RUNBOOK.md`, `README_JOB_EXTRACTION_OVERVIEW.md`, `README_FAMILY_PARENT_LEAF_PIPELINE.md` (about 20 KB), `business_rules_v2.md`, `rule_ml_alignment_audit.md` and `.json`, and `research/Job Attribute Extraction Research….md`. **Documentation.** The family/parent/leaf pipeline doc describes the Decision Layer path, not `job-nlpv2`.

`v2/paths.py` and `v2/training/model_b.py`, `model_c.py` — an older v2 training path. The two model files are the same size (5,940 bytes). **Legacy.** Production skills are `skills/`, and this `v2/` package is not the technology CSV under `data/technology/v2`.

`experiments/README.md` says skill experiments moved to `archive/experiments/`. That directory is not on disk. The package `__init__.py` is empty. **Documentation, review.**

`investigation/other_column_extraction/` — a copied slice of an older pipeline (orchestrator, language gate, languages, certifications, country) plus a 20-offer sample. `_copied_files.txt` lists what was copied. **Legacy.** Do not import it beside `pipeline/`.

`artifacts/` — 6 files under `models/` (including `semantic_family/profile_vectors.npz` and `semantic_title_index/title_vectors.npz`), 6 under `v2/`, 5 under `rule_alignment/`, and 207 under `reports/`. **Not opened file by file in this pass.** The npz files are the semantic indexes the taxonomy README tells the resolver to load. **Supporting data** for that fallback. The reports are generated output.

---

## models/

Repo-root weight folder. About 5.7 GB and 129 files. This is not `job_nlp/models/`, which only holds training scripts. Gitignore ignores `models/`. The live leaf path loads one directory from here: `job-title-normalizer-e5-base`.

```text
models/
├── lid.176.bin
├── job-title-normalizer-e5-base/
├── esco-xlm-roberta-large/
├── experiments/esco-xlm-roberta-large/
└── models/
    ├── job_family_leaf/
    ├── job_family_parent/
    ├── seniority/
    ├── model_c_esco/
    ├── semantic_family/
    └── semantic_title_index/
```

### lid.176.bin

FastText language-id model, about 125 MB. **Supporting.** `job_nlp/tests/test_preprocess_gate.py` loads whatever path the gate config names and fails if that file is missing. The binary on disk is this one.

### job-title-normalizer-e5-base

**Active.** `job-nlpv2/leaf/support.py` sets `MODEL` to this directory. The card says it is a sentence-transformers fine-tune of `intfloat/multilingual-e5-base` for retrieving a canonical occupation from a noisy title, over a 4,055-occupation ESCO and O*NET corpus. `config.json` is `XLMRobertaModel`, 12 layers, hidden size 768. `model.safetensors` is about 1.06 GB. `tn_preset.json` says queries need the prefix `query: ` and passages need `passage: `. `1_Pooling/config.json` is mean pooling. `eval/similarity_evaluation_val-synonym-vs-nonsynonym_results.csv` records cosine Spearman about 0.849 after two epochs. **Keep.** The frozen leaf formula embeds titles with this model. It is not a classifier with a softmax over the 118 leaves.

### esco-xlm-roberta-large

ESCOXLM-R, the Zhang, van der Goot, and Plank ACL 2023 model: XLM-R large adapted on the ESCO taxonomy. `config.json` says `RobertaForCustomMaskedLM`, 24 layers, hidden size 1024. This folder has the README, config, and `onnx/model.onnx` (about 1 MB) plus a sentencepiece model. It does not contain `model.safetensors`. The Hugging Face `.cache` is what makes the folder about 136 MB. **Experiment.** `scripts/benchmark_esco_xlmr.py` is the script that was written to score this model. The production skill README says ESCO mapping is off.

### experiments/esco-xlm-roberta-large

The same ESCOXLM-R card and config, plus `model.safetensors` at about 2.1 GB and `sentencepiece.bpe.model` at about 5 MB. **Experiment weights.** This is the full checkpoint. The folder above is the ONNX and cache copy. Nothing in `job-nlpv2/leaf` points here.

### models/models

A second tree of older classifiers. `job_nlp/paths.py` points `MODELS_DIR` at `job_nlp/artifacts/models`, not at this directory. The leaf registry in this tree records artifact paths under `job_nlp/artifacts/models/job_family_leaf/...`. Treat these files as a copy that can drift from that artifacts tree.

`job_family_parent/tfidf_svm_v1/` — TF-IDF plus LinearSVC, `tfidf_linearsvc.joblib` about 19 MB. Validation macro F1 0.709 on 724 rows, train 3,624. `test` is not in the metric file. **Experiment.**

`job_family_parent/xlmr_base_v1_section_aware/` — `FacebookAI/xlm-roberta-base`, 25 parent labels, `model.safetensors` about 1.06 GB. Validation macro F1 0.746, which the file itself compares with the TF-IDF 0.709 (`delta` 0.036). `test_used` is false. **Experiment.**

`job_family_leaf/` — `registry.json` plus nine parent-specific TF-IDF joblibs (`cybersecurity`, `data_engineering`, `enterprise_applications`, `it_support_itsm`, `networking`, `qa_testing`, `software_development`, `ux_ui_design`, `web_development`). Recorded macro F1 in the registry runs from 0.455 (`it_support_itsm`, six classes) to 0.798 (`enterprise_applications`, two classes). Class names are old ids such as `NETWORK_SECURITY_ENGINEER` and `HELPDESK_TECHNICIAN`, not the 118-leaf display names. **Experiment.** The frozen leaf path does not load these joblibs.

`seniority/tfidf_section_aware_v1/` — TF-IDF LinearSVC, about 6 MB. The registry names it the champion at macro F1 0.621. A title-only variant in the same registry is 0.588. **Experiment.** Year brackets in the experience extractor do not use this model.

`seniority/registry.json` and `job_family_leaf/registry.json` store those scores and absolute paths on this machine. **Artifact.**

`model_c_esco/biencoder.pt` — about 1.06 GB. `metrics.json` says 171,294 pairs, backbone `job_nlp/artifacts/v2/models/job-xlmr-tapt`, generated 2 Sep 2026. **Experiment.** The skill README says Model C is not on the skill path.

`semantic_family/profile_vectors.npz` (about 0.4 MB) and `profile_metadata.json` — 156 profiles, 1,445 reviewed titles, 768 dimensions, built with `job-title-normalizer-e5-base`. `semantic_title_index/title_vectors.npz` (about 4 MB) and `title_metadata.json` — 1,445 titles, same model. **Supporting for the semantic fallback** if the resolver is pointed here. A different pair of npz files, different byte sizes, also sits under `job_nlp/artifacts/models/`. Open the metadata fingerprint before assuming the two copies match.

---

## packages/

One npm workspace package. No README in this folder. The root `package.json` builds it first (`build:contracts`), and both `apps/api` and `apps/web` depend on `@job-recommender/contracts`. `node_modules` was not opened; the lockfile resolves that package name to this folder.

```text
packages/
└── contracts/
    ├── package.json
    ├── tsconfig.json
    ├── tsconfig.tsbuildinfo
    ├── src/
    │   ├── index.ts
    │   ├── common.ts
    │   ├── candidate-draft.ts
    │   ├── candidate-profile.ts
    │   └── candidate-preferences-survey.ts
    └── dist/
        ├── index.js / index.d.ts
        ├── common.js / common.d.ts
        ├── candidate-draft.js / candidate-draft.d.ts
        ├── candidate-profile.js / candidate-profile.d.ts
        └── candidate-preferences-survey.js / candidate-preferences-survey.d.ts
```

`package.json` — **Active, keep.** Private package `@job-recommender/contracts` 0.1.0. `main` and `exports` point at `dist/`, so the apps import the compiled JavaScript, not the TypeScript source. Scripts are `tsc -b` (build, watch, typecheck). The only dependency is TypeScript 5.

`tsconfig.json` — **Supporting, keep.** Extends the root `tsconfig.base.json`, composite project, `rootDir` `src`, `outDir` `dist`. `apps/api/tsconfig.json` and `apps/web/tsconfig.json` list this project under `references`.

`tsconfig.tsbuildinfo` — **Artifact, remove from source control.** Incremental `tsc` cache. `.gitignore` already ignores `*.tsbuildinfo`.

`dist/` — **Artifact, keep on disk after a build, do not edit.** Ten files: each `src` module compiled to `.js` and `.d.ts`. `index.js` only re-exports the four modules. `.gitignore` ignores `dist/`. Rebuild with `npm run build:contracts`.

### src

`index.ts` — **Active, keep.** Re-exports `common`, `candidate-draft`, `candidate-profile`, and `candidate-preferences-survey`.

`common.ts` — **Active, keep.** Shared enums and the API envelope. Callers include `apps/web/src/api/client.ts` (`ApiError`, `isApiError`) and the review form schemas.

- `Confidence`: HIGH, MEDIUM, LOW, UNKNOWN.
- `ContractType`: CDI, CDD, INTERNSHIP, ALTERNANCE, FREELANCE, OTHER. These match `apps/api/prisma/schema.prisma`. They are the CV product labels. The Python job extractor uses PERMANENT, FIXED_TERM, FREELANCE, INTERNSHIP, UNKNOWN. Do not treat the two lists as the same enum.
- `WorkMode`: REMOTE, HYBRID, ONSITE. Same three values as the job work-mode extractor and as Prisma.
- `MobilityPreference`: LOCAL, FOREIGN, REMOTE.
- `ExperienceType`: PROFESSIONAL, INTERNSHIP, ALTERNANCE, FREELANCE, UNKNOWN. Matches Prisma.
- `LanguageLevel`: CEFR A1–C2 plus NATIVE, FLUENT, ADVANCED, INTERMEDIATE, BASIC, UNKNOWN. Matches Prisma.
- `DraftStatus`: PARSED, EDITING, CONFIRMED, EXPIRED, DISCARDED. Matches Prisma.
- `ParseQualityStatus`: GOOD, FAIR, POOR. Prisma stores parse quality as a plain string, not this enum.
- `ApiSuccessEnvelope`, `ApiError`, `ApiErrorEnvelope`, and `isApiError`.

`candidate-draft.ts` — **Active, keep.** The UI draft the parser adapter is supposed to emit (`CandidateDraft`). React review components import this type (`ReviewForm`, identity, experience, skills, languages, `draft-mappers`). Fields carry `EditableField` (`value`, `confidence`, `needsReview`). Skills use `SkillEvidenceSource` labels (SKILLS_SECTION, PROFESSIONAL_EXPERIENCE, INTERNSHIP, ALTERNANCE, PROJECT, CERTIFICATION, EDUCATION, PROFILE), the same set as the Prisma `SkillEvidenceSource` enum. Draft status on this type is only PARSED or EDITING. There is no occupation family and no education-level enum; certifications here are name, issuer, and year.

`candidate-profile.ts` — **Active, keep.** The confirmed profile. `CandidateProfileInput` is what the web sends on confirm (`useConfirmProfile`, `draft-mappers`). `CandidateProfileResponse` is what `GET` profile returns (`profile.service.ts`). Education records are free-text degree, institution, and field, plus dates. The response also carries contract types, work modes, mobility, preferred countries, and goals `FIND_JOB` or `OPTIMIZE_PROFILE`. Experience totals are month counts split by type.

`candidate-preferences-survey.ts` — **Active, keep.** The survey after CV confirmation: `CandidatePreferenceSurveyInput` and `CandidatePreferenceSurveyResponse`. Used by `useSubmitPreferenceSurvey` and `profile.service.ts`. Fields are profile id, contract types, work modes, mobility, preferred countries, goals, and `preferencesCompletedAt`. Prisma `PreferenceType` (CONTRACT_TYPE, WORK_MODE, MOBILITY, PREFERRED_COUNTRY, GOAL) is not exported from this package; the survey sends the values, not that storage enum.

The package comment says these types must not re-export the raw Python parser schema. That schema stays in `apps/api`. **Keep the source.** Nothing here is the 118-leaf occupation taxonomy or the job-extraction enums.

---

## recommendation/

Repo-root skill ranker. This is not `job_nlp/recommendation/`, which fuses a preference score and a qualification score. `__init__.py` says this package is legacy and that V1 lives in `job_nlp.recommendation`. That line is stale. `app/main.py` imports `recommendation.api` and mounts it at `/api/recommendations`. The FastAPI title on port 8000 is “CV Extraction + Skill Recommendation Service”.

The score is skills only. Job title, job description, occupation, education, experience, and location are not inputs. Thresholds in the artifact note are uncalibrated heuristics.

```text
recommendation/
├── __init__.py
├── api.py
├── service.py
├── config.py
├── db.py
├── normalize.py
├── candidate_builder.py
├── models/__init__.py
├── scoring/
├── matching/
├── ranking/
├── embeddings/
├── explanation/
├── evaluation/manual_eval.py
├── scripts/
├── migrations/
├── tests/
└── artifacts/recommendation_v1/
```

### Entry and score

`api.py` — **Active, keep.** `POST /api/recommendations/jobs`. Body is `candidate_id`, `profile_description`, `technology_skills` (`taxonomy_id`, `name`, `proficiency`), `limit` (default 20), `debug`. The handler always calls `use_db=False`, so this route never reads Postgres. It ranks the in-memory JSONL cache.

`service.py` — **Active, keep.** Loads `job_nlp/artifacts/reports/skills_all_offers_v1/all_offers_skills_per_job.jsonl` on the first request, embeds unique professional skill names with the encoder, then calls `recommend_jobs`. `use_db=True` loads `rec_jobs` instead. Nothing in `api.py` passes that flag.

`config.py` — **Supporting, keep.** `RecommendationSettings`, env prefix `RECOMMENDATION_`. Defaults: model `BAAI/bge-small-en-v1.5`, dimension 384, CPU, batch 128. Professional cosine gates 0.85 (strong, cap 0.90) and 0.75 (partial, cap 0.70). Exact professional match scores 1.0. Requirement weights 1.0 / 0.7 / 0.4 for required / unspecified / preferred. Category mix 0.55 professional and 0.45 technology. Required-skill penalty floor 0.5. Top K 20. Proficiency factors beginner 0.50, intermediate 0.75, advanced and expert 1.00. Database URL falls back to `DATABASE_URL`, then `postgresql+psycopg://postgres:postgres@localhost:5432/job_recommender`. Prisma `postgresql://` URLs are rewritten for SQLAlchemy.

`scoring/final_score.py` — **Active, keep.** `skill_match_score` is the weighted mix of the two category scores. A missing category is dropped and the remaining weight is renormalized. If required skills exist, the score is multiplied by `0.5 + 0.5 * coverage`. Coverage counts exact and strong professional matches, and exact technology matches. Partial cosine matches do not count as covered.

`ranking/recommend_jobs.py` — **Active, keep.** Scores every job, sorts by `skill_match_score`, returns the top K. No index.

`models/__init__.py` — **Active, keep.** Pydantic types: `SkillType` TECHNOLOGY or PROFESSIONAL_SKILL, `Requirement` REQUIRED / PREFERRED / UNSPECIFIED, `MatchType` EXACT / SEMANTIC_STRONG / SEMANTIC_PARTIAL / NONE, candidate and job skill bundles, and `RecommendationResult` (scores, matched and missing lists, explanation, optional debug).

### Matching

`matching/professional.py` — **Active, keep.** Exact `professional::<sha256>` key first. Otherwise the best cosine against the candidate’s professional vectors. Strong and partial bands come from config. Unrelated pairs score 0.

`matching/technology.py` — **Active, keep.** Exact `taxonomy_id` only. A hit is multiplied by the proficiency factor. Java and JavaScript stay distinct because the ids differ. No embedding.

`matching/requirements.py` — **Active, keep.** Maps requirement and proficiency strings onto the config weights.

`matching/skill_match.py` — re-exports the two scorers. **Supporting.**

`scoring/professional_score.py` and `scoring/technology_score.py` — the same re-exports. **Supporting.** `scoring/__init__.py` is empty.

`normalize.py` — **Active, keep.** NFKC, casefold, collapsed whitespace, then `professional::<sha256>`. Names shorter than two characters are dropped. The key is for storage identity, not for meaning.

`candidate_builder.py` — **Active, review.** Builds the candidate from `profile_description` by calling `job_nlp.skills.en_skill_stack.EnSkillStack` and keeping `PROFESSIONAL_SKILL` entities, then embeds those names. Technology skills come from the request, not from that extractor. A search of this repo finds no `en_skill_stack.py` and no `class EnSkillStack`. A request that fills `profile_description` fails on that import until the class is restored. The recorded live sample has `professional_from_stack: []`.

`explanation/skill_gap.py` — re-exports `RecommendationResult`. The gap lists are filled in the matchers, not here. **Supporting.** `explanation/__init__.py` is empty.

### Embeddings and database

`embeddings/encoder.py` — **Active, keep.** Lazy `SentenceTransformer`, L2-normalized vectors. `HashEmbeddingEncoder` is the test double. Default model name is the BGE small English model above, not the E5 title normalizer.

`embeddings/repository.py` — **Supporting, keep.** Reads and upserts `skill_embeddings` so one professional key is encoded once per model.

`embeddings/backfill.py` — **Supporting, keep.** CLI `python -m recommendation.embeddings.backfill` fills professional embeddings for job skills already in Postgres.

`db.py` — **Supporting, keep.** SQLAlchemy models `rec_jobs`, `skill_embeddings`, `job_skills`, `rec_candidate_skills`. Embeddings are PostgreSQL `real[]`. Cosine runs in Python. Tables are separate from the Prisma candidate tables.

`migrations/001_recommendation.sql` — **Supporting, keep.** Creates those four tables and indexes. No `vector` column.

`migrations/001_recommendation_down.sql` — **Supporting, keep.** Drops the four tables.

`scripts/migrate.py` — **Supporting, keep.** Applies the SQL with `psycopg`. Does not need the `psql` binary.

`scripts/import_job_skills.py` — **Supporting, keep.** Upserts the skills JSONL into `rec_jobs` and `job_skills`.

`ranking/job_store.py` — **Active, keep.** Parses a JSONL row only when `status` is `ok`. Dedupes technology ids and professional keys. `load_jobs_from_db` attaches stored professional vectors. `attach_embeddings_in_memory` does the same for the JSONL path.

`artifacts/recommendation_v1/01_db_schema.md` and `09_architecture.md` still describe pgvector and `vector(384)`. The SQL and `FINAL_STATUS.md` store `real[]` and say pgvector is optional. **Documentation, review.** Trust the SQL.

### Scripts, tests, artifacts

`evaluation/manual_eval.py` — **Experiment, review.** Two hard-coded phrase pairs, plus an optional JSON file. Not a labeled eval set.

`scripts/smoke_cv_recommend.py` — **Experiment, review.** Parses one PDF at a fixed path outside this repo (`Hazem DOUZI CV.pdf` on the Desktop), then recommends from Postgres. Writes `10_hazem_cv_live.json`.

`tests/test_scoring.py`, `test_embedding_cache.py`, `test_import_parse.py` — **Test, keep.** Twelve checks named in `08_test_report.txt`: exact professional, strong semantic, unrelated professional, technology exact versus Java/JavaScript, preferred-missing still high, required penalty, no double count, weight renormalization, stable keys, JSONL skip and dedupe, one encode per shared key. They use the hash encoder. They do not load BGE or Postgres.

`artifacts/recommendation_v1/` — **Artifact, keep.**

- `02_embedding_config.json` and `05_similarity_thresholds.json` copy the config numbers. The threshold file says they are initial heuristics, not hiring probabilities.
- `03_job_import_report.json` is a ready-to-run note: 2,801 ok rows, 232 unsupported language, pipeline named Nesta plus Tech Taxonomy V2.
- `03_import_job_skills_report.json` records a finished import: 2,801 jobs, 232 skipped, 17,020 technology links, 68,089 professional links, about 102 seconds.
- `04_embedding_backfill_report.json` records 36,175 unique professional skills, 35,704 embeddings written, 0 failures, about 450 seconds, model BGE small, dimension 384. About 471 keys skipped on conflict.
- `06_recommendation_sample.json` is a demo Data Engineer row at 0.647, scored with the hash encoder. The note says production uses BGE.
- `07_performance_report.json` says the unit suite passed and full-corpus latency is `PENDING_MODEL_AND_DB`.
- `08_test_report.txt` lists the twelve passed tests.
- `10_hazem_cv_live.json` is one CV smoke. `professional_from_stack` is empty. Rank 1 is “Customer Support Advisor” at 1.0 because the only technology on that job (HTML) matched and there was no professional score to mix in. Several later rows have `professional_score` 0 and `technology_score` 1.0. This file is one run, not a quality measure.
- `FINAL_STATUS.md` says the system is complete, no model training, no LLM ranking, and the NLP pipeline was not modified. It also says occupation, education, experience, and location matching are not implemented. Read that beside the pending performance line and the missing `EnSkillStack` import.

`ranking/__init__.py` and `matching/__init__.py` are empty. **Supporting.**

---

## scripts/

Repo-root command-line runners. Six Python files plus `__pycache__`. Nothing in the app, the API, or the CV parser imports this folder. This is not `job_nlp/scripts/` (the 57 extraction runners already noted under `job_nlp`).

```text
scripts/
├── benchmark.py
├── evaluate_corpus.py
├── build_skill_lexicon.py
├── build_balanced_education_3class.py
├── merge_education_3class_associate.py
└── build_balanced_min_exp_dataset.py
```

`benchmark.py` — **Supporting, keep.** Times one PDF through `cv_parser`: ingest, section classify, skill extract, then full `extract_profile`. Default path is `data/samples/sample_cv.pdf`. That file is not in the repo. Pass a PDF path on the command line. It prints milliseconds, sections, skills, and parse quality. It does not write a report.

`evaluate_corpus.py` — **Experiment, review.** Runs `extract_profile` over `ResumesPDF/ResumesPDF/*.pdf` and compares skill mentions loosely with `ResumesJsonAnnotated/`. Neither directory is in this repo. The script’s own header says those annotations are noisy weak labels and the overlap number is not precision or recall. It also sniffs an IT subset with a keyword list (two hits required). Default report path is `corpus_evaluation_report.json` at the working directory. That file is not on disk. Flags: `--limit`, `--seed` (42), `--report`, `--progress-every`, `--slow-warn-ms` (3000).

`build_skill_lexicon.py` — **Supporting, keep.** Reads `cv_parser/resources/skills/it_lexicon.json` (188 skill ids) and checks duplicate ids, alias collisions, and a fixed list of regression terms (Python through Pytest). `--check-only` validates without writing. `--esco-csv` and `--onet-csv` append extra rows as `OTHER_IT` with policy SAFE, then overwrite the lexicon. Curated rows win on alias clash because new labels are skipped when the text already exists. The header says the seed list is mirrored in the JSON. The script does not contain that seed; it only loads the JSON.

`build_balanced_education_3class.py` — **Experiment, review.** Requires `--input` (an xlsx with `title`, `description`, `correct_education_level`, `education_evidence`). Maps DOCTORATE and MASTER to `MASTER_OR_HIGHER`, samples 330 `BACHELOR` and 286 `UNKNOWN` (`random_state` 42), and asserts 900 rows. Drops ASSOCIATE, VOCATIONAL_DIPLOMA, and HIGH_SCHOOL. Writes `artifacts/datasets/balanced_education_3class_900.xlsx` and `.parquet`. `artifacts/datasets/` is not on disk, so this builder has not left its output in the repo.

`merge_education_3class_associate.py` — **Experiment, review.** Hard-coded inputs under `C:\Users\Hzdou\Downloads\`: `balanced_education_3class_900.xlsx` and `associate_it_offers_dataset.csv`. Renames associate columns onto `title`, `description`, `education_level`, `evidence`, maps `VOCATIONAL_DIPLOMA` to `ASSOCIATE`, drops duplicate title+description, shuffles with seed 42. Writes `artifacts/datasets/balanced_education_3class_plus_associate.csv`, `.xlsx`, and a JSON report. Those outputs are not on disk. This is the script that puts ASSOCIATE back after the 900-row builder removed it.

`build_balanced_min_exp_dataset.py` — **Experiment, review.** Requires `--input` with `title`, `description`, `correct_min_experience`, `min_exp_evidence`, `correct_seniority`. Month cutoffs in this file: exactly 0 → `0_YEARS`, then `<= 24` → `1_2_YEARS`, `<= 60` → `3_5_YEARS`, `<= 84` → `5_7_YEARS`, else `8_PLUS_YEARS`. `job_nlp/tests/test_rule_ml_alignment.py` asserts a different `to_bracket`: 0–11 months `0_YEARS`, 12–35 `1_2_YEARS`, 36–59 `3_5_YEARS`, 60–95 `5_7_YEARS`, 96 and above `8_PLUS_YEARS`. The module that test imports, `job_nlp.contracts.business_policy`, is not on disk. Do not treat this script’s cutoffs as the live extractor. When months are missing, title words fill a bracket (intern → 0, junior → 1–2, mid → 3–5, senior/lead → 5–7, principal/director → 8+). Quotas keep every `0_YEARS` and `8_PLUS_YEARS` row and sample 150 of each other class. Writes `artifacts/datasets/balanced_min_experience_dataset.parquet` and `.xlsx`. Those files are not on disk.

`__pycache__/` — **Artifact, remove from source control.** Bytecode. Gitignore already covers it.

---

## shared_matching/

Four files. Shared labels and skill-name cleanup for comparing a CV with a job. Current importers: `cv_parser/matching/candidate_matching_adapter.py` (skill names only) and `job_nlp/pipeline/job_extraction_pipeline.py` plus `job_nlp/schemas/normalized_job_offer.py`. The root `recommendation/` package is not on disk in this listing. `app/main.py` still imports `recommendation.api`, so that import fails until the package is restored. This folder does not score jobs.

```text
shared_matching/
├── __init__.py
├── enums.py
├── skill_identity.py
└── contracts.md
```

`__init__.py` — **Active, keep.** Re-exports the enums and the two name helpers `canonicalize_skill_name` and `skill_match_key`. It does not export `professional_skill_id`. Callers that need that function import `skill_identity` directly.

`enums.py` — **Active, keep.** String literals and normalizers. Unknown input becomes `UNKNOWN`, empty, or `None`. It does not invent a level.

- `MatchingContractType`: PERMANENT, FIXED_TERM, INTERNSHIP, ALTERNANCE, FREELANCE, TEMPORARY, OTHER, UNKNOWN. `CvContractType`: CDI, CDD, INTERNSHIP, ALTERNANCE, FREELANCE, OTHER. `contract_to_matching` maps CDI → PERMANENT and CDD → FIXED_TERM. `PART_TIME` is mapped to OTHER and the comment says that is a schedule, not a contract. `contract_to_cv` maps TEMPORARY and UNKNOWN back to OTHER, so UNKNOWN does not survive the round trip.
- `WorkMode`: REMOTE, HYBRID, ONSITE. `normalize_work_mode` returns `None` when the value is missing or outside those three.
- `WorkSchedule`: FULL_TIME, PART_TIME, UNKNOWN. `FULL` and `PART` are accepted.
- `Seniority` lists INTERN, JUNIOR, MID, MID_LEVEL, SENIOR, LEAD, MANAGER, DIRECTOR, EXECUTIVE, UNKNOWN. `normalize_seniority` only keeps INTERN, JUNIOR, MID, SENIOR, LEAD, MANAGER, and UNKNOWN. DIRECTOR, EXECUTIVE, and MID_LEVEL become UNKNOWN.
- `CareerLevel` and `LeadershipLevel` are declared. No function in this file normalizes them.
- `RequirementModality`: REQUIRED, PREFERRED, UNSPECIFIED. `normalized_job_offer.py` imports this, plus `Language` and `WorkSchedule`.
- `EducationLevel`: UNKNOWN, ASSOCIATE, BACHELOR, MASTER_OR_HIGHER. `education_rank` is 0, 1, 2, 3. `normalize_education_level` folds HIGH_SCHOOL and SECONDARY to UNKNOWN, VOCATIONAL_DIPLOMA and BAC+2 to ASSOCIATE, LICENCE and BAC+3 to BACHELOR, and MASTER, DOCTORATE, ENGINEER, and BAC+5 to MASTER_OR_HIGHER. HIGHER_EDUCATION stays UNKNOWN.
- `Language`: ENGLISH, FRENCH, ARABIC, GERMAN, SPANISH, ITALIAN, PORTUGUESE, DUTCH, UNKNOWN, with French aliases (`anglais`, `français`, `arabe`, and the rest of that table).
- `LanguageLevel`: UNKNOWN, A1–C2, NATIVE, FLUENT. ADVANCED, INTERMEDIATE, and BASIC, which exist on the TypeScript contract, become UNKNOWN here.
- `normalize_country_code` returns a two-letter code when the input is already two letters, or from a short alias list (Tunisia TN, Morocco MA, France FR, and the other names in that dict). `remote`, `worldwide`, and `anywhere` return empty. Other country names return empty.

`skill_identity.py` — **Active, keep.** A fixed alias table, about forty entries: `reactjs` → React, `k8s` → Kubernetes, `js` → JavaScript, `aws` → Amazon Web Services, `postgres` → PostgreSQL, and the other rows in the dict. `postgresql` is listed twice with the same target. Unknown names are trimmed and capitalized. All-caps tokens of at most six letters stay as written. `skill_match_key` is the canonical name folded to lower case. `professional_skill_id` builds `SKILL::<slug>` (C++ becomes `c-plus-plus`, C# becomes `c-sharp`). The job pipeline calls both helpers when it writes a skill onto the offer. The CV adapter calls only `canonicalize_skill_name`. This table is not the 188-row `it_lexicon.json` and not a taxonomy id.

`contracts.md` — **Documentation, review.** Says recommendation should compare family, skills, experience, contract, work mode, country, languages, and certifications, and should not rank on raw description text. The skill ranker that was in `recommendation/` scored professional cosine and technology ids only. The types named here, `CandidateKnowledgeProfile` and `JobMatchingProfile`, are not defined in this folder. `CandidateKnowledgeProfile` is built in `cv_parser/matching/candidate_matching_adapter.py`.

---

## job-nlpv2/

Deterministic job-field extractors plus the frozen 70/15/15 leaf script. There is no package `__init__.py` at this root. `job_nlp/pipeline/job_extraction_pipeline.py` loads contract, education, experience, and work mode through thin re-exports under `job_nlp/extraction/`. One `ImportError` in that block sets all four to `None`, so a missing dependency disables every field extractor together. The leaf script is not imported by that pipeline. It is a standalone run. This folder does not apply the 0.55 / 0.015 title gates. Those live elsewhere. There is no gold label file here, so this section does not state a top-1 accuracy.

```text
job-nlpv2/
├── README.md
├── contract/
├── education/
├── experience/
├── work_mode/
├── technologies/
└── leaf/
```

`README.md` — **Documentation, keep.** Points at each entry below and says commands run from the internship root so `job_nlp` imports resolve.

### contract/

`contract_type_extractor.py` — **Active, keep.** Labels: PERMANENT, FIXED_TERM, FREELANCE, INTERNSHIP, UNKNOWN. CDI maps to PERMANENT. CDD, interim, and temporary map to FIXED_TERM. Alternance and apprenticeship map to INTERNSHIP. The FREELANCE alias list includes the bare word `consultant`, so a permanent IT consulting title can also be marked FREELANCE. These are not the CV product labels CDI/CDD in `packages/contracts`. `job_nlp/extraction/contract_type_extractor.py` loads this file.

`contract_type_cli.py` — **Supporting, keep.** Reads JSON or JSONL (`title`, `description`) and prints `contract_types`.

### education/

A small package. `python -m education` from this folder, or the re-export `job_nlp.extraction.education`.

`extractor.py` — **Active, keep.** Public `to_dict()` returns only `required_education_levels`: UNKNOWN, ASSOCIATE, BACHELOR, MASTER_OR_HIGHER. High school becomes UNKNOWN. BTS, DUT, and vocational diploma become ASSOCIATE. Master, engineering, Bac+5, and doctorate become MASTER_OR_HIGHER. An empty list means no requirement was stated. `to_dict(detailed=True)` adds modality, evidence offsets, and flags.

`dictionaries.py`, `patterns.py`, `normalizer.py`, `clause_parser.py`, `models.py` — **Active, keep.** Alias lists, generated patterns, and the result types. `EducationLevel` ranks are UNKNOWN 0, ASSOCIATE 5, BACHELOR 6, MASTER_OR_HIGHER 7.

`config.py` — **Supporting, keep.** Default country `MA` from `EDUCATION_COUNTRY`. UK, IN, and DE override a few aliases (HND, A-levels, Abitur).

`cli.py`, `__main__.py` — **Supporting, keep.** JSON or JSONL in, one JSON object per line out. Optional `--country`.

`requirements.txt` — **Supporting.** The only line is `pytest`.

`README.md` — **Documentation, keep.** Matches the public one-field output.

### experience/

`seniority_experience_extractor.py` — **Active, review.** Brackets are 0_YEARS, 1_2_YEARS, 3_5_YEARS, 5_7_YEARS, 8_PLUS_YEARS, UNKNOWN. `months_to_bracket` calls `job_nlp.contracts.business_policy.to_bracket`. That module is not on disk, so importing this file raises `ImportError`. The pipeline then drops contract, education, work mode, and experience together. Seniority labels on the result are INTERN_ENTRY, JUNIOR, MID, SENIOR, LEAD_PRINCIPAL, UNKNOWN. A separate `Seniority` enum still lists INTERN through EXECUTIVE for older imports. Unquantified “experience required” can become 1_2_YEARS with the warning `UNQUANTIFIED_EXPERIENCE_ASSUMED_1_2_YEARS`. Internship contract text can force 0_YEARS.

`seniority_experience_cli.py` — **Supporting, keep.** One JSON object in, one JSON object out. Optional `--contract-type`.

### work_mode/

`work_mode_extractor.py` — **Active, keep.** ONSITE, HYBRID, REMOTE. Hybrid wins when both remote and onsite are present. An optional `workplace` argument treats a page line `Teleworking : Hybrid|Yes|No` as authoritative (`Hybrid`/`hybride` → HYBRID, `Yes`/`oui`/`Remote` → REMOTE, `No`/`non` → ONSITE). A self-check under `if __name__` asserts those three page lines and a sentence that is both remote and in the office. The early “fully remote” branch still returns REMOTE before the hybrid split, and the split pattern looks for `onsite` without a hyphen. `job_nlp/extraction/work_mode_extractor.py` loads this file.

`work_mode_cli.py` — **Supporting, keep.** Same JSON/JSONL shape as the contract CLI. Passes `item["teleworking"]` when that key is present.

### technologies/

`technology_v2.py` — **Active, review.** Loads `IT_TECH_TAXONOMY_V2_RUNTIME.csv` through `job_nlp.paths`. That CSV is not on disk (`job_nlp/data/technology/v2/` is missing). `recover_full_text` finds taxonomy aliases in title or description text: slash aliases, slash compounds, then a trie of exact tokens. It does not embed. The import `from technology_matching_policy import ...` is a bare module name, so this file only imports when `job-nlpv2/technologies` is on `sys.path`.

`technology_matching_policy.py` — **Active, keep.** Decides whether a hit is safe, context-required, or rejected (generic English, prose antipatterns, distinctive casing). `job_nlp.paths.PACKAGE_ROOT` is used for the lemma file.

### leaf/

The frozen occupation formula. Not called by `JobNLPService`.

`support.py` — **Active, keep.** Paths, the English title table for the 100 Rekrute offers, and the guards. `MODEL` is `models/job-title-normalizer-e5-base`. `load_registry` requires 118 leaves, 8 families, and 24 parents, joined by exact leaf name. It refuses to run if old id `L0001` and new id `L001` have the same name, so ids are not matched by stripping zeros. `sections` takes the text between `Job :` and `Required profile :`. `is_out` is true for comptable/accountant, or for commercial/inside-sales when the title has none of engineer, developer, support, analyst, informatique. `role_override` can move a winner to IT Project Manager, Backend Developer, IT Consultant, or Application Support Specialist. It does not add a Tech Lead SAS leaf.

`it_leaf_pipeline_tech15.py` — **Experiment, keep.** Loads the E5 model, encodes the 5,259 catalog titles (`passage: `) and each offer title (`query: ` after `normalize_occupation_title`). Technology score is the max cosine between Job-section chunks and that leaf’s technology names from the enriched JSON. Definition score is the max cosine to the leaf definition. Task score is the mean of the max cosines over main-task atoms. Baseline = 0.75 title + 0.25 technology. Enriched (the emitted leaf) = 0.70 title + 0.15 technology + 0.15 × (definition + tasks) / 2. Role override, then `is_out`, run after the argmax. Profile skill lines are not in the formula. The script writes the report README. It imports `job_nlp.taxonomy.title_normalization`, which is not on disk.

`frozen_title70_tech15/it_leaf_pipeline_title70_tech15.py` — **Experiment, keep.** The same script, with `sys.path` pointed at `leaf/` so `support` imports. It writes the same report path.

`inputs/` — **Active input, keep.**

| File | Rows | Role |
|---|---|---|
| `leaves_best.csv` | 118 | Current ids L001…, family, parent, leaf name |
| `definitions_best.csv` | 118 | One definition per leaf name |
| `main_tasks_best.csv` | 118 | Semicolon-separated tasks per leaf name |
| `leafs_best.csv` | 118 | Older ids L0001…, used only for the id-collapse check |
| `technologies_best.csv` | 9,645 | Technology name, aliases, related leaf names. Not the cosine vote. The vote uses technology names on each leaf in the JSON |
| `it_titles_master_taxonomy_no_seniority_best.csv` | 5,259 | Title, Parents, Leafs, Families. Copy of the root catalog |
| `leaf_profiles_compact_118_24_8_enriched_best.json` | 118 leaves | Copy of the root enriched profiles. Technology names for the cosine come from here |
| `rekrute_it_100_translated_best.jsonl` | 100 | The offer file this script scores |

`reports/rekrute_it_100_title70_tech15/README.md` and `frozen_title70_tech15/README.md` — **Artifact, keep.** The same generated table, about 153 KB. Baseline and enriched leaves differ on 14 of the 100 offers. Two rows are `OUT_OF_IT_DOMAIN`: `COMMERCIAL SÉDENTAIRE` and `Comptable clôture opérationnelle interco (F/H)`. The file is a run record, not a labeled accuracy score.

`__pycache__/` under each folder — **Artifact.** Gitignore covers it.
