"""
main.py
Entry point. Loads config.yaml and runs both agents on a loop,
checking every `check_interval_minutes`.

Usage:
    python main.py          # run once
    python main.py --loop   # run repeatedly forever
"""

import sys
import time
import yaml

from naukri_agent import run_naukri_agent
from linkedin_agent import run_linkedin_agent


def load_config(path="config.yaml"):
    with open(path, "r") as f:
        cfg = yaml.safe_load(f)

    # Common mistake: known_skills/target_roles ending up as one long
    # string instead of a proper YAML list (usually from bad indentation
    # or merged lines). Fail loudly instead of silently matching nothing.
    for key in ("known_skills", "target_roles"):
        if isinstance(cfg.get(key), str):
            raise ValueError(
                f"'{key}' in config.yaml is a single string, not a list! "
                f"Each item needs its own line starting with '  - ', e.g.:\n"
                f"{key}:\n  - \"python\"\n  - \"mysql\"\n"
                f"Please fix config.yaml and try again."
            )
    return cfg


def run_once(cfg):
    print("=== Job agent run starting ===")
    print(f"[main] Loaded known_skills from config.yaml: {cfg.get('known_skills')}")
    print(f"[main] Loaded target_roles from config.yaml: {cfg.get('target_roles')}")
    try:
        run_linkedin_agent(cfg)
    except Exception as e:
        print(f"[main] LinkedIn agent crashed: {e}")

    try:
        run_naukri_agent(cfg)
    except Exception as e:
        print(f"[main] Naukri agent crashed: {e}")
    print("=== Job agent run finished ===")


if __name__ == "__main__":
    cfg = load_config()

    if "--loop" in sys.argv:
        interval = cfg["run"]["check_interval_minutes"] * 60
        while True:
            run_once(cfg)
            print(f"[main] Sleeping {interval/60:.0f} minutes...")
            time.sleep(interval)
    else:
        run_once(cfg)