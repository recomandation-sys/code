# ingestionv2

Rekrute English IT board only.

```powershell
python -m ingestionv2
```

The listing is `https://www.rekrute.com/en/offres-emploi-metiers-de-l-it.html?p={page}&s=1`. The crawl stops when a page adds no offer id that was not already on an earlier page. Each offer is fetched on its `/en/` URL.

Raw rows append to `ingestionv2/output/rekrute_raw.jsonl`. A second run does not fetch an offer id already in that file.

A raw row holds the page fields: `url`, `title`, `company`, `company_logo`, `country`, `date_posted`, `deadline`, `education`, `teleworking`, `contract`, `experience`, and `description`. The description is the visible `div.contentbloc` text. The JSON-LD description is ignored. Enum mapping happens later, in `extractionv2`.
