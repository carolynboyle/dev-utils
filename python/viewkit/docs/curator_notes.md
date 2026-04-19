are there any others above that also are not specific to viewkit?

8:35 AM
Yes. Of the 16 files I generated, only 7 belong in viewkit. The rest are all curator:

viewkit (dev-utils repo):

query_models.py
query_builder.py
query_loader.py
exceptions.py (updated)
__init__.py (updated)
test_query_builder.py
fixtures/queries.yaml

================================================
curator repo:

data/queries.yaml — the actual SQL definitions
config.py — path resolution for queries.yaml
base.py — BaseRepository accepts QueryLoader
deps.py — FastAPI dependency for QueryLoader
projects.py — inline SQL replaced with loader calls
tasks.py — same
tags.py — same
files.py — same
projects_routes.py — passes loader to repositories