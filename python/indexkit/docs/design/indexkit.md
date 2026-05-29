
10:34 AM
indexkit — a dev-utils package extracted from doc-gen, responsible for one thing: generating a structured local manifest of a repository's contents. Other tools (currently fletcher) depend on this manifest as input. Extracting it from doc-gen gives those tools a clean, minimal dependency. Timeshift/backup functionality stays in doc-gen (Dr. Filewalker).

