import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRAPER_SRC = os.path.join(ROOT, "scraper", "src")
SRC = os.path.join(ROOT, "src")
for p in [SCRAPER_SRC, SRC]:
    if p not in sys.path:
        sys.path.insert(0, p)


