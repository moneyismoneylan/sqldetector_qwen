"""Simple cProfile runner for the SQLFuzzer.

This utility helps identify hotspots in payload generation.  It
profiles a sample run and prints the ten most expensive functions.
"""
from __future__ import annotations

import cProfile
import pstats
import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from sqldetector.fuzzer.sql_fuzzer import SQLFuzzer


def main() -> None:
    fuzzer = SQLFuzzer()

    def run() -> None:
        list(fuzzer.generate("mysql", "SELECT 1"))

    profiler = cProfile.Profile()
    profiler.runcall(run)
    stats = pstats.Stats(profiler)
    stats.sort_stats("cumtime").print_stats(10)


if __name__ == "__main__":
    main()
