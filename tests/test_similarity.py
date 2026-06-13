from pipeline import similarity


def test_offline_fingerprint_is_lexical():
    fp = similarity.fingerprint("the wax shell on a babybel cheese")
    assert fp["kind"] == "lexical"


def test_empty_catalog_returns_zero():
    score, who = similarity.max_similarity("anything at all")
    assert score == 0.0 and who is None


def test_remember_then_identical_is_high():
    text = "Bricks have three holes to save clay and lock the mortar in place."
    similarity.remember("job-1", text)
    score, who = similarity.max_similarity(text)
    assert who == "job-1"
    assert score > 0.9  # identical lexical content


def test_unrelated_text_is_low():
    similarity.remember("job-1", "Why airport carpets use busy geometric patterns.")
    score, _ = similarity.max_similarity("The economics of why coins have ridged edges.")
    assert score < similarity.THRESHOLD


def test_remember_is_idempotent_per_job():
    similarity.remember("job-1", "first version of the script about golf balls")
    similarity.remember("job-1", "rewritten version about golf ball dimples drag")
    # Only one entry should exist for job-1 (the latest).
    catalog = similarity._load()
    assert sum(1 for e in catalog if e.get("job_id") == "job-1") == 1
