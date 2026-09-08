"""A self-contained dlt pipeline used for offline demos and tests.

Uses in-memory data so it needs no network and no credentials — run it through
nl2pipe with:  `nl2pipe build --code-file examples/example_pipeline.py`.
"""

import dlt


@dlt.resource(name="users", primary_key="id", write_disposition="merge")
def users():
    yield from [
        {"id": 1, "name": "Ada", "email": "ada@example.com", "signups": 3},
        {"id": 2, "name": "Linus", "email": "linus@example.com", "signups": 1},
        {"id": 3, "name": "Grace", "email": None, "signups": 7},
    ]


@dlt.resource(name="events", primary_key="event_id", write_disposition="append")
def events():
    yield from [
        {"event_id": 101, "user_id": 1, "kind": "login"},
        {"event_id": 102, "user_id": 1, "kind": "purchase"},
        {"event_id": 103, "user_id": 2, "kind": "login"},
    ]


if __name__ == "__main__":
    pipeline = dlt.pipeline(
        pipeline_name="demo",
        destination="duckdb",
        dataset_name="sandbox",
    )
    print(pipeline.run([users(), events()]))
