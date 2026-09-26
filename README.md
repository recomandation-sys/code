# Job Recommender — CV Upload & Review

A candidate can upload a PDF CV, have it parsed by a deterministic, CPU-only
Python service, review/edit the extracted data in a web form, and confirm it
into a verified profile stored in PostgreSQL.

The system has three moving parts that run as separate processes in
development:

| Service            | Tech                          | Default URL             |
| ------------------- | ------------------------------ | ------------------------ |
| `cv_parser` (Python) | FastAPI, PyMuPDF, RapidFuzz, Aho-Corasick — no LLM | http://localhost:8000 |
| `apps/api` (Node)    | Express, TypeScript, Prisma, PostgreSQL | http://localhost:3000 |
| `apps/web` (Node)    | React, Vite, TanStack Query    | http://localhost:5173 |

Architecture docs live in [`readme/`](readme/) — start with
[`readme/README_CV_EXTRACTION_ARCHITECTURE.md`](readme/README_CV_EXTRACTION_ARCHITECTURE.md)
(the parser) and [`readme/README_CV_UPLOAD_REVIEW_WEB_ARCHITECTURE.md`](readme/README_CV_UPLOAD_REVIEW_WEB_ARCHITECTURE.md)
(the web app). Job EN_V1 is maintained under [`job_nlp/`](job_nlp/); see the
layout guide at [`job_nlp/docs/REPOSITORY_LAYOUT.md`](job_nlp/docs/REPOSITORY_LAYOUT.md).

## Frozen job-extraction milestone

The production job-offer extraction baseline is frozen as
`occupation_decision_v2_1`. Its authoritative IT occupation taxonomy contains
8 families, 24 parents, and 118 leaves. The pipeline extracts structured
education, language, contract type, work mode, seniority, minimum experience,
technologies, and the occupation hierarchy.

The next phase is reserved for Recommendation System V1 under
`job_nlp/recommendation/`; no recommender algorithm is implemented yet. Planned
signals are family, parent, optional leaf, technologies, minimum experience,
education, languages, contract type, and work mode. Nesta professional-skill
phrases and raw task similarity are intentionally excluded from the first
recommendation model because of extraction noise and inconsistent task data.

Historical extraction tests and one-off reports are retained under
`archive/pre_recommender_cleanup/` and are not runtime dependencies.

## Rekrute extraction

The English IT board is a separate path from the CV app:

```powershell
python -m extractionv2
```

`ingestionv2` saves raw `/en/` pages to `ingestionv2/output/rekrute_raw.jsonl`. `extractionv2` appends accept and refuse rows to `extractionv2/output/rekrute_it.jsonl` and skips offer ids already written. The gate, the 70/15/15 leaf, and the enum mappers live in `jobnlpv2`. The leaf query calls `normalize_occupation_title` in `job_nlp/taxonomy/title_normalization.py`. Details are in [ingestionv2/README.md](ingestionv2/README.md), [extractionv2/README.md](extractionv2/README.md), and [jobnlpv2/README.md](jobnlpv2/README.md).

## Prerequisites

- **Python 3.12** with the project's virtual environment at `.venv/` (already
  set up in this repo — see `requirements.txt` if you need to recreate it).
- **Node.js 20+** and npm.
- **PostgreSQL** running locally (a native Windows install, not Docker) with
  a `job_recommender` database and a superuser you know the password for.

## 1. One-time setup

### 1.1 Python parser

```powershell
# From the repo root, with the existing .venv:
.venv\Scripts\pip install -r requirements.txt
```

### 1.2 Node workspaces

```powershell
npm install
```

This installs dependencies for the root, `apps/api`, `apps/web`, and
`packages/contracts` via npm workspaces in one pass.

### 1.3 Environment files

Copy the example env files and adjust as needed (in particular the
PostgreSQL password in `DATABASE_URL`):

```powershell
Copy-Item apps/api/.env.example apps/api/.env
Copy-Item apps/web/.env.example apps/web/.env
```

See the root [`.env.example`](.env.example) for what each variable does.

### 1.4 Database: migrate + seed

```powershell
npm run prisma:generate --workspace apps/api
npm run prisma:migrate --workspace apps/api
npm run prisma:seed --workspace apps/api   # loads cv_parser/resources/skills/it_lexicon.json into the Skill table
```

(`prisma:migrate` runs `prisma migrate dev`, creating the `job_recommender`
database's tables if the database itself already exists. Create the database
first with `psql` or pgAdmin if it doesn't exist yet.)

## 2. Running everything (development)

Start each service in its own terminal, in this order:

**Terminal 1 — Python CV parser**

```powershell
.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```

**Terminal 2 — Express API**

```powershell
npm run dev:api
```

**Terminal 3 — React web app**

```powershell
npm run dev:web
```

Then open http://localhost:5173 and upload a CV PDF.

## 3. Common tasks

| Task | Command |
| --- | --- |
| Run API unit + integration tests | `npm run test:api` |
| Run web tests | `npm run test:web` |
| Run everything's tests | `npm test` |
| Typecheck API | `npm run typecheck --workspace apps/api` |
| Typecheck web | `npm run typecheck --workspace apps/web` |
| Build all workspaces | `npm run build` |
| Open Prisma Studio (inspect DB) | `npm run prisma:studio` |
| Create a new migration after editing `schema.prisma` | `npm run prisma:migrate --workspace apps/api` |
| Run Python parser tests | `.venv\Scripts\python -m pytest` |

## 4. Request flow (high level)

1. The user drops a PDF on the **upload page** (`apps/web`). The file is
   validated client-side (PDF, ≤10 MB) and POSTed to the Express API.
2. The **Express API** (`apps/api`) forwards the file as multipart/form-data
   to the Python parser's `/api/cv/parse` endpoint, validates the parser's
   JSON response against a Zod schema, adapts it into a `CandidateDraft`
   (stable IDs, `needsReview` flags, resolved skill IDs against the canonical
   `Skill` table), and persists it as a `CvParseDraft` row (raw JSON +
   derived UI draft) in PostgreSQL.
3. The **review page** loads the draft by ID and lets the user edit every
   field before confirming.
4. On confirm, the API re-validates the payload, recomputes aggregate
   experience durations server-side, resolves/creates canonical skills, and
   atomically writes a relational `CandidateProfile` (with its nested
   positions, experiences, skills, languages, certifications) in a single
   Prisma transaction. Confirming the same draft twice is idempotent — it
   returns the existing profile instead of creating a duplicate.
5. If parsing fails (or the user skips upload entirely), the API can create
   an empty "manual" draft so the same review form can be used to build a
   profile from scratch.

## 5. Repository layout

```
app/                  Python FastAPI entry point (cv_parser HTTP wrapper)
cv_parser/            Deterministic CV parsing pipeline (no LLM)
apps/api/             Express + TypeScript + Prisma backend
apps/web/             React + TypeScript + Vite frontend
packages/contracts/   Shared TypeScript types used by both apps/api and apps/web
ingestionv2/          Rekrute English IT crawl, raw JSONL
extractionv2/         English gate, leaf, enums, normalized JSONL
jobnlpv2/             Gate, leaf, and the enum extractors that path calls
```
