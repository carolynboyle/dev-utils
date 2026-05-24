# post-notes addition — add to Future Posts section

- **sniffkit post** — the problem of LLM output as untyped `.txt` files.
  The designing-gemma use case: 461 runs, all `.txt`, need to be served
  as HTML/CSS/MD without manual inspection. sniffkit as the general
  solution; `sniffkit-looper.sh` as the designing-gemma-specific wrapper.
  Hook: "every file was named run_042.txt. none of them were plain text."
  Planned `--parent-dir` flag as the natural evolution — generalizing the
  looper pattern back into the tool without coupling it to any specific
  project structure.
