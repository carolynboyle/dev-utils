viewkit/
    onthefly/
        __init__.py
        config.py      # reads viewkit: section from dev-utils config.yaml
        runner.py      # wires QueryLoader → DBConnection → result
        formatter.py   # ASCII table, JSON, CSV output
        cli.py         # argparse entry point