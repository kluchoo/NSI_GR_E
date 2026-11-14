# Zajęcia projektowe nr 5 — testy niefunkcjonalne

**Zespół E.** SUT: `BankSystem` (`API.py`).  
Instrukcja: `docs/P5.pdf`.  
Testy: `tests/test_niefunkcjonalne.py`.

## Szybki start

```bash
uv sync
uv run pytest tests/test_niefunkcjonalne.py -o addopts= -s
uv run python scripts/lab5_benchmark.py
```

- `-o addopts=` — wyłącza domyślne `--cov` (lab 5 nie mierzy pokrycia).
- `-s` — widać wydruk metryk `[lab5] ...` w terminalu (do screenów).

**Wynik u nas:** 4 testy **passed** (stan z uruchomienia na `lab5`).

---

## 1. Co było do zrobienia (w skrócie)

| # | Zadanie z PDF | Gdzie w repo |
|---|----------------|--------------|
| 1 | Test współbieżności na operacji zmieniającej saldo | `test_przelew_wspolbiezny_saldo_koncowe` |
| 2 | 20 powtórzeń i licznik przejść | `test_przelew_wspolbiezny_wielokrotne_uruchomienia` |
| 3 | Test obciążeniowy (~10 000 operacji) | `test_obciazenie_wplaty_sekwencyjnie_i_rownolegle` |
| 4 | Sekwencja vs wątki | ta sama funkcja + `scripts/lab5_benchmark.py` |
| 5 | Przepustowość (op/s) | wydruk w teście / skrypt |

Scenariusz współbieżności jest jak w PDF: **100 wątków**, każdy robi `przelew(1234567895 → 9876543215, 10)`, oczekiwane saldo celu **1000**.

---

## 2. Test współbieżności — opis i wynik

**Metoda:** `przelew` — modyfikuje saldo dwóch kont; w `API.py` jest `threading.Lock()` wewnątrz metody, więc aktualizacje są wzajemnie wykluczane.

**Asercje:**

- konto docelowe: saldo = `1000`;
- konto źródłowe: saldo = `9000` (start 10 000 − 100 × 10).

**20 uruchomień scenariusza (w jednym teście):**

| Metryka | Wynik |
|---------|--------|
| Przejścia | **20 / 20** |
| Niespójności salda | brak |

**Dodatkowo:** `test_wplac_wspolbiezny_wielokrotne_uruchomienia` — 200 wątków × `wplac(..., 1)`, 20 prób. U nas też **20/20** (CPython + GIL często maskuje brak locka przy `wplac`). Do raportu warto napisać, że **`wplac` nie ma locka**, a **`przelew` ma** — to widać w kodzie, testy funkcjonalne tego nie sprawdzają.

---

## 3. Test obciążeniowy — czas i przepustowość

**Operacja:** `wplac("1234567895", 1)` × **10 000** na jednym koncie.

| Wariant | Czas [s] | Przepustowość [op/s] | Saldo końcowe |
|---------|----------|----------------------|---------------|
| Sekwencyjnie | ~0,021–0,023 | ~428 000–477 000 | 10 000 |
| Równolegle (8 wątków) | ~0,022–0,035 | ~285 000–445 000 | 10 000 |

Wynik zależy od CPU i obciążenia maszyny — **przed oddaniem raportu uruchom u siebie** `scripts/lab5_benchmark.py` i wklej **swoje** liczby.

**Obserwacja:** równoległe wpłaty na **to samo** konto nie muszą być szybsze (a czasem są wolniejsze przez koszt wątków i walkę o GIL). To normalny wniosek niefunkcjonalny: wyższa przepustość ≠ zawsze „włączamy wątki”.

---

## 4. Co wkleić do raportu zespołowego

1. **Współbieżność:** opis scenariusza + tabela `X/20` przejść.
2. **Obciążenie:** dwa wiersze (sekwencja / równolegle): czas, **op/s**, poprawność salda.
3. **Jeśli kiedyś test się wyłoży:** dokładne saldo z komunikatu błędu — to dowód buga, nie „flakowy test”.
4. **Wnioski:** np. lock w `przelew` stabilizuje saldo; testy z lab 4 nie mierzyły czasu ani wyścigów; 100% coverage z lab 2–3 tego nie zastąpi.

---

## 5. Co zescreenować

1. Terminal: `uv run pytest tests/test_niefunkcjonalne.py -o addopts= -s` — sekcja **`4 passed`** i linie `[lab5] przelew współbieżny: 20/20`.
2. Terminal: `uv run python scripts/lab5_benchmark.py` — cała tabela czasu i op/s.
3. Edytor: fragment `przelew` z `with self._lock:` w `API.py` (uzasadnienie stabilności).
4. (Opcjonalnie) `tests/test_niefunkcjonalne.py` — funkcja `_scenariusz_przelewy_wspolbiezne`.

---

## 6. Pytania kontrolne — ściąga

1. **Funkcjonalne vs niefunkcjonalne:** „Czy przelew ustawia saldo na 1000?” vs „Czy 100 równoległych przelewów **zawsze** daje 1000?”.
2. **Niestabilność:** przełączenia wątków przez OS — ten sam kod, inna kolejność = inny wynik przy braku synchronizacji.
3. **Przepustowość vs latency:** op/s (wiele operacji) vs czas jednej wpłaty.
4. **Load vs stress:** typowe obciążenie (10k wpłat) vs zwiększanie aż do awarii (lab 5 w PDF — głównie load).

---

## 7. Uwaga: „P5” w README vs zajęcia nr 5

W `README.md` wariant E wspomina **retry / circuit breaker** przy `przelew_zewnetrzny` — to kontekst **odporności integracji** (inny blok / późniejsza praca). **Zajęcia projektowe nr 5 z `P5.pdf`** dotyczą **testów niefunkcjonalnych** (obciążenie, współbieżność), nie implementacji retry w kodzie produkcyjnym.