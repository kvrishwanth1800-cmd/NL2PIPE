import dlt
from dlt.sources.helpers import requests

@dlt.resource(name="github_events", write_disposition="replace")
def github_events():
    resp = requests.get("https://api.github.com/events?per_page=100")
    resp.raise_for_status()
    yield resp.json()

if __name__ == "__main__":
    pipeline = dlt.pipeline(
        pipeline_name="demo", destination="duckdb", dataset_name="sandbox"
    )
    print(pipeline.run(github_events()))
