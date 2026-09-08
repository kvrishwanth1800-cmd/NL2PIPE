from nl2pipe.quality import checks_to_sql, generate_checks, run_checks


def test_generates_and_runs_checks(sandbox_db):
    checks = generate_checks(sandbox_db)
    assert checks, "expected at least some checks"
    results = run_checks(sandbox_db, checks)
    assert len(results) == len(checks)


def test_email_null_is_flagged(sandbox_db):
    # Grace has a NULL email -> there must be NO 'no nulls' check on users.email,
    # because the column is not fully populated in the sample.
    names = [c.name for c in generate_checks(sandbox_db)]
    assert "users.email: no nulls" not in names
    # but id is fully populated and unique -> both checks present
    assert "users.id: no nulls" in names
    assert "users.id: unique" in names


def test_not_empty_checks_pass(sandbox_db):
    checks = [c for c in generate_checks(sandbox_db) if c.name.endswith("not empty")]
    assert all(r.passed for r in run_checks(sandbox_db, checks))


def test_checks_export_to_sql(sandbox_db):
    sql = checks_to_sql(generate_checks(sandbox_db))
    assert "SELECT" in sql and sql.strip().endswith(";")
