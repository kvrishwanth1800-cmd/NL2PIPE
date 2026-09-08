# Example requests to try

Plain-English prompts that produce reasonable `dlt` pipelines:

- "Load the public GitHub events API into a table, incremental on created_at."
- "Pull all rows from a Postgres table `public.orders` into DuckDB, merge on id."
- "Read every CSV in ./data and load each as its own table, replace on each run."
- "Fetch pages from the JSONPlaceholder /posts endpoint with pagination and load them."
- "Load Stripe charges via the REST API, incremental on `created`, merge on `id`."
  (reads STRIPE_API_KEY from the environment)

Offline (no API key) — run an existing script through the same sandbox/plan/quality flow:

    nl2pipe build --code-file examples/example_pipeline.py
