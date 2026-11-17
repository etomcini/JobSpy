from jobspy import scrape_jobs


def test_scrape_jobs_is_importable():
    assert callable(scrape_jobs)
