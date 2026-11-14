"""
Zajęcia projektowe nr 5 — testy niefunkcjonalne (obciążenie, współbieżność).

Uruchomienie (bez coverage — szybsze, bez szumu w raporcie):
    uv run pytest tests/test_niefunkcjonalne.py -o addopts= -s

Tylko współbieżność:
    uv run pytest tests/test_niefunkcjonalne.py -o addopts= -k wspolbiezny

Metryki obciążeniowe (tabela do raportu):
    uv run python scripts/lab5_benchmark.py
"""

from __future__ import annotations

import threading
import time
from decimal import Decimal

import pytest

from API import BankSystem

NUM_ZRODLO = "1234567895"
NUM_CEL = "9876543215"

LICZBA_WATKOW_PRZELEWU = 100
KWOTA_PRZELEWU = 10
OCZEKIWANE_SALDO_CEL = Decimal(LICZBA_WATKOW_PRZELEWU * KWOTA_PRZELEWU)

POWTORZEN_WSPOLBIEZNOSCI = 20
OPERACJI_OBCIAZENIOWYCH = 10_000
WORKEROW_ROWNOLEGLE = 8


def _bank_z_dwooma_kontami(saldo_zrodlo: int = 10_000) -> BankSystem:
    bank = BankSystem()
    bank.utworz_konto(NUM_ZRODLO, "Zrodlo", saldo_zrodlo)
    bank.utworz_konto(NUM_CEL, "Cel", 0)
    return bank


def _jeden_przelew_w_watku(bank: BankSystem) -> None:
    bank.przelew(NUM_ZRODLO, NUM_CEL, KWOTA_PRZELEWU)


def _scenariusz_przelewy_wspolbiezne() -> tuple[Decimal, Decimal]:
    bank = _bank_z_dwooma_kontami()
    watki = [threading.Thread(target=_jeden_przelew_w_watku, args=(bank,)) for _ in range(LICZBA_WATKOW_PRZELEWU)]
    for w in watki:
        w.start()
    for w in watki:
        w.join()
    return bank.konta[NUM_CEL].saldo, bank.konta[NUM_ZRODLO].saldo


@pytest.mark.niefunkcjonalne
def test_przelew_wspolbiezny_saldo_koncowe():
    """100 wątków × przelew 10 PLN — saldo konta docelowego musi wynosić dokładnie 1000."""
    saldo_cel, saldo_zrodlo = _scenariusz_przelewy_wspolbiezne()
    assert saldo_cel == OCZEKIWANE_SALDO_CEL
    assert saldo_zrodlo == Decimal("10000") - OCZEKIWANE_SALDO_CEL


@pytest.mark.niefunkcjonalne
def test_przelew_wspolbiezny_wielokrotne_uruchomienia():
    """Ten sam scenariusz 20 razy — wynik statystyczny do raportu (niestabilność = bug SUT)."""
    przejscia = 0
    odchylenia: list[str] = []

    for nr in range(POWTORZEN_WSPOLBIEZNOSCI):
        saldo_cel, saldo_zrodlo = _scenariusz_przelewy_wspolbiezne()
        if saldo_cel == OCZEKIWANE_SALDO_CEL and saldo_zrodlo == Decimal("9000"):
            przejscia += 1
        else:
            odchylenia.append(f"run {nr + 1}: cel={saldo_cel}, zrodlo={saldo_zrodlo}")

    print(
        f"\n[lab5] przelew współbieżny: {przejscia}/{POWTORZEN_WSPOLBIEZNOSCI} przejść, "
        f"oczekiwane saldo celu={OCZEKIWANE_SALDO_CEL}"
    )
    if odchylenia:
        print("[lab5] odchylenia:", "; ".join(odchylenia[:5]))

    assert przejscia == POWTORZEN_WSPOLBIEZNOSCI, (
        f"Niespójność salda w {POWTORZEN_WSPOLBIEZNOSCI - przejscia} z {POWTORZEN_WSPOLBIEZNOSCI} prób"
    )


@pytest.mark.niefunkcjonalne
def test_wplac_wspolbiezny_wielokrotne_uruchomienia():
    """
    Metoda wplac nie ma locka (w przeciwieństwie do przelew).
    Na CPythonie GIL często maskuje wyścigi — test służy jako obserwacja, nie jako twardy wymóg labu.
    """
    n_watkow = 200
    przejscia = 0

    for _ in range(POWTORZEN_WSPOLBIEZNOSCI):
        bank = BankSystem()
        bank.utworz_konto(NUM_ZRODLO, "A", 0)

        def wpisz():
            bank.wplac(NUM_ZRODLO, 1)

        watki = [threading.Thread(target=wpisz) for _ in range(n_watkow)]
        for w in watki:
            w.start()
        for w in watki:
            w.join()
        if bank.konta[NUM_ZRODLO].saldo == Decimal(n_watkow):
            przejscia += 1

    print(f"\n[lab5] wplac współbieżny (bez locka): {przejscia}/{POWTORZEN_WSPOLBIEZNOSCI}, {n_watkow} wątków")

    assert przejscia == POWTORZEN_WSPOLBIEZNOSCI


def _wplac_sekwencyjnie(n: int) -> tuple[float, Decimal]:
    bank = BankSystem()
    bank.utworz_konto(NUM_ZRODLO, "A", 0)
    start = time.perf_counter()
    for _ in range(n):
        bank.wplac(NUM_ZRODLO, 1)
    elapsed = time.perf_counter() - start
    return elapsed, bank.konta[NUM_ZRODLO].saldo


def _wplac_rownolegle(n: int, workers: int) -> tuple[float, Decimal]:
    bank = BankSystem()
    bank.utworz_konto(NUM_ZRODLO, "A", 0)
    chunk, remainder = divmod(n, workers)

    def worker(loops: int) -> None:
        for _ in range(loops):
            bank.wplac(NUM_ZRODLO, 1)

    start = time.perf_counter()
    threads = [threading.Thread(target=worker, args=(chunk,)) for _ in range(workers)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    for _ in range(remainder):
        bank.wplac(NUM_ZRODLO, 1)
    elapsed = time.perf_counter() - start
    return elapsed, bank.konta[NUM_ZRODLO].saldo


@pytest.mark.niefunkcjonalne
def test_obciazenie_wplaty_sekwencyjnie_i_rownolegle():
    """10 000 wpłat — czas, poprawność salda; przepustowość wypisuje się z -s lub w scripts/lab5_benchmark.py."""
    czas_seq, saldo_seq = _wplac_sekwencyjnie(OPERACJI_OBCIAZENIOWYCH)
    czas_par, saldo_par = _wplac_rownolegle(OPERACJI_OBCIAZENIOWYCH, WORKEROW_ROWNOLEGLE)

    assert saldo_seq == Decimal(OPERACJI_OBCIAZENIOWYCH)
    assert saldo_par == Decimal(OPERACJI_OBCIAZENIOWYCH)

    thr_seq = OPERACJI_OBCIAZENIOWYCH / czas_seq
    thr_par = OPERACJI_OBCIAZENIOWYCH / czas_par

    print(
        f"\n[lab5] {OPERACJI_OBCIAZENIOWYCH} wplat po 1 PLN:\n"
        f"  sekwencyjnie: {czas_seq:.4f} s, {thr_seq:,.0f} op/s\n"
        f"  rownolegle ({WORKEROW_ROWNOLEGLE} watkow): {czas_par:.4f} s, {thr_par:,.0f} op/s"
    )