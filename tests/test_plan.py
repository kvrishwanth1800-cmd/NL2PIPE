from nl2pipe.plan import inspect_dataset


def test_inspect_finds_user_tables(sandbox_db):
    plans = {p.name: p for p in inspect_dataset(sandbox_db)}
    assert "users" in plans and "events" in plans


def test_internal_tables_hidden(sandbox_db):
    names = [p.name for p in inspect_dataset(sandbox_db)]
    assert not any(n.startswith("_dlt") for n in names)


def test_row_counts_and_columns(sandbox_db):
    plans = {p.name: p for p in inspect_dataset(sandbox_db)}
    assert plans["users"].rows == 3
    assert plans["events"].rows == 3
    cols = {c.name for c in plans["users"].columns}
    assert {"id", "name", "email", "signups"} <= cols
    assert not any(c.name.startswith("_dlt") for c in plans["users"].columns)
