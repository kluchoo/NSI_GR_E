#!/usr/bin/env python3
"""
Pomiar metryk lab 5 (obciążenie + współbieżność) — wynik wklejasz do raportu.

    uv run python scripts/lab5_benchmark.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.test_niefunkcjonalne import (  # noqa: E402
    OPERACJI_OBCIAZENIOWYCH,
    POWTORZEN_WSPOLBIEZNOSCI,
    WORKEROW_ROWNOLEGLE,
    _scenariusz_przelewy_wspolbiezne,
    _wplac_rownolegle,
    _wplac_sekwencyjnie,
    OCZEKIWANE_SALDO_CEL,
)


def main() -> None:
    print("=== Lab 5 — metryki niefunkcjonalne (zespół E) ===\n")

    przejscia = 0
    for i in range(POWTORZEN_WSPOLBIEZNOSCI):
        saldo_cel, _ = _scenariusz_przelewy_wspolbiezne()
        if saldo_cel == OCZEKIWANE_SALDO_CEL:
            przejscia += 1
    print(
        f"Test współbieżny przelew: {przejscia}/{POWTORZEN_WSPOLBIEZNOSCI} przejść "
        f"(saldo celu oczekiwane {OCZEKIWANE_SALDO_CEL})"
    )

    czas_seq, saldo_seq = _wplac_sekwencyjnie(OPERACJI_OBCIAZENIOWYCH)
    czas_par, saldo_par = _wplac_rownolegle(OPERACJI_OBCIAZENIOWYCH, WORKEROW_ROWNOLEGLE)

    thr_seq = OPERACJI_OBCIAZENIOWYCH / czas_seq
    thr_par = OPERACJI_OBCIAZENIOWYCH / czas_par

    print(f"\nObciążenie: {OPERACJI_OBCIAZENIOWYCH} × wplac(..., 1)")
    print(f"  sekwencyjnie:  czas {czas_seq:.4f} s, przepustowość {thr_seq:,.0f} op/s, saldo {saldo_seq}")
    print(
        f"  równolegle ({WORKEROW_ROWNOLEGLE} wątków): czas {czas_par:.4f} s, "
        f"przepustowość {thr_par:,.0f} op/s, saldo {saldo_par}"
    )
    rel = (thr_par / thr_seq - 1) * 100 if thr_seq else 0
    print(f"  przyspieszenie równoległe vs sekwencja: {rel:+.1f}% przepustowości")


if __name__ == "__main__":
    main()