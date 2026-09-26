# jobnlpv2

Extractors for the Rekrute English IT pipeline. Run commands from the internship repo root.

The leaf query calls `normalize_occupation_title` in `job_nlp/taxonomy/title_normalization.py`. That string is only the retrieval query. The stored title stays the page title.

| Piece | Where |
|---|---|
| English gate | `jobnlpv2/gate`. `run_gate` returns ACCEPT or REFUSE. Full text at or above 0.95 accepts. Otherwise the first two substantive chunks must both be English at or above 0.80. A missing `models/lid.176.bin` refuses. |
| Visible description | `jobnlpv2/visible.py`. `div.contentbloc`, skipping the info bar and the Head office block. The JSON-LD description is not used. |
| Leaf | [`jobnlpv2/leaf/README.md`](leaf/README.md). `assign_leaf` returns the enriched name from `0.70 title + 0.15 technology + 0.15 * (definition + main tasks) / 2`. Family and parent come from that name in `leaf/inputs/leaves_best.csv` (118 / 24 / 8). |
| Education | `jobnlpv2/education`. Levels: `UNKNOWN`, `ASSOCIATE`, `BACHELOR`, `MASTER_OR_HIGHER`, as a list. |
| Experience | `jobnlpv2/experience/seniority_experience_extractor.py`. Brackets come from `to_bracket`. |
| Contract | `jobnlpv2/contract/contract_type_extractor.py`. `PERMANENT`, `FIXED_TERM`, `FREELANCE`, `INTERNSHIP`, `UNKNOWN`. |
| Work mode | `jobnlpv2/work_mode/work_mode_extractor.py`. `REMOTE`, `HYBRID`, `ONSITE`. A `Teleworking :` line is passed through as the workplace. |
| Technologies | `jobnlpv2/technologies/technology_v2.py`. `recover_full_text` reads `leaf/inputs/technologies_best.csv` (`technology`, `aliases`). |

`extractionv2` calls these in that order. It does not keep a second copy of the rules.
