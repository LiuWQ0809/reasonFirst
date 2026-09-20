#!/usr/bin/env python3
"""Run with uv from the source checkout; do not inspect or print credentials."""
from gitlab_agent.project_access import main

if __name__ == "__main__":
    raise SystemExit(main())
