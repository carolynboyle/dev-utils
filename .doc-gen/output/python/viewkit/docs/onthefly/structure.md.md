# structure.md

**Path:** python/viewkit/docs/onthefly/structure.md
**Syntax:** markdown
**Generated:** 2026-05-20 15:41:52

```markdown
viewkit/
    onthefly/
        __init__.py
        config.py      # reads viewkit: section from dev-utils config.yaml
        runner.py      # wires QueryLoader → DBConnection → result
        formatter.py   # ASCII table, JSON, CSV output
        cli.py         # argparse entry point
```
