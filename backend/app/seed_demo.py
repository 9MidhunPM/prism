"""Run with: python -m app.seed_demo (requires DEMO_MODE=true)."""

from .demo import seed_demo_accounts


if __name__ == "__main__":
    print(seed_demo_accounts())
