# extractionv2

One command crawls the English IT board, then appends normalized rows.

```powershell
python -m extractionv2
```

That calls `ingestionv2` first, then reads `ingestionv2/output/rekrute_raw.jsonl` and appends to `extractionv2/output/rekrute_it.jsonl`. An offer id already in the output file is skipped.

An offer continues only when the English gate accepts it and `assign_leaf` returns one of the 118 names in `jobnlpv2/leaf/inputs/leaves_best.csv`. The leaf query uses `normalize_occupation_title`. Anything else, including no leaf, is a short refusal. Education, contract, work mode, experience, and technologies do not run on a refusal.

Accept row: the raw source fields, `description`, `family`, `parent`, `leaf`, `education` (a list), `contract_type`, `work_mode`, `experience`, and `technologies` (canonical names from `technologies_best.csv`). The page lines stay beside the enums as `education_raw`, `teleworking_raw`, `contract_raw`, and `experience_raw`.

Refuse row: `url`, `title`, `decision`, `reason`.

Offline checks:

```powershell
python -m pytest extractionv2/tests/test_rekrute.py
```
