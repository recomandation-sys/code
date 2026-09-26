"""Rekrute keeps the translated offer body, not the original hidden description."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ingestion"))

from rekrute_scraper import english_offer_url, parse_job

PAGE = """
<html><body>
<script type="application/ld+json">
{"@type":"JobPosting","title":"Test Lead","description":"le Test Lead a pour missions principales en francais"}
</script>
<div class="contentbloc">
  <div class="col-md-12 info blc">Test Lead - Rabat</div>
  <div class="col-md-12 blc">Job : the Test Lead main missions are to organize testing and support the squad.</div>
  <div class="col-md-12 blc">Required profile : You have a degree and experience in software testing.</div>
  <div class="col-md-12 blc">Head office address : Avenue Bin Al Ouidane, Rabat</div>
</div>
</body></html>
"""


def test_description_uses_the_translated_block():
    job = parse_job("https://www.rekrute.com/offre-emploi-test-lead-rabat-1.html", PAGE)
    assert "francais" not in (job.description or "")
    assert "organize testing" in (job.description or "")
    assert "Head office" not in (job.description or "")


def test_offer_url_uses_the_english_page():
    assert english_offer_url("https://www.rekrute.com/offre-emploi-a-1.html").startswith(
        "https://www.rekrute.com/en/"
    )
    same = "https://www.rekrute.com/en/offre-emploi-a-1.html"
    assert english_offer_url(same) == same
