"""Source entry point; use `uv run python scripts/tunnel.py --help`."""
from gitlab_agent.tunnel_lifecycle import main

if __name__ == "__main__":
    raise SystemExit(main())
