"""main.py — one-command pipeline: stocks -> JSON ready for Pages.

Usage:
    uv run main.py               # full pipeline (stocks + insights)
    uv run python -m src.build    # stocks only
    uv run python -m src.insights # insights only

Exit codes: 0 success, 1 fatal (per-ticker errors never fatal).
NOTE (ADR-001): SFTP upload removed from pipeline; deploy via git push to
GitHub Pages. upload.py retained for course reference only.
"""

from __future__ import annotations

import logging
import sys
import time

from src import build as stocks_build
from src import insights as stock_insights

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("pipeline")


def main() -> int:
    t0 = time.time()
    try:
        print("=== Step 1: stocks fetch -> features -> forecast -> backtest ===")
        stocks_build.build_all()

        print("\n=== Step 2: AI insights (Gemini or fallback) ===")
        try:
            stock_insights.build_insights()
        except Exception as e:  # noqa: BLE001
            logger.warning("insights step had an issue (continuing): %s", e)

        dt = time.time() - t0
        print(f"\nPipeline complete in {dt:.1f}s. Output ready in output/.")
        print("Deploy: git push -> GitHub Pages serves https://sohail-ahmed.space/")
        return 0
    except Exception as e:  # noqa: BLE001 — fatal (e.g. no tickers at all)
        logger.error("pipeline FAILED: %s", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
