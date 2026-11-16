# Zajęcia projektowe nr 6 — analiza statyczna

**Zespół E.** SUT: `BankSystem` (`API.py`).  
Instrukcja: `docs/NSI_Proj06.pdf` (blok P4).  
Surowy wynik narzędzi: `docs/_lab6_*.txt`.  
Skrypt: `scripts/lab6_static.sh`.

## Szybki start

```bash
uv sync
uv pip install radon pylint flake8   # albo: pip install ...
bash scripts/lab6_static.sh API.py
```

Wyniki poniżej pochodzą z uruchomienia na `API.py` (stan gałęzi `lab6`).

---

## 1. Co było do zrobienia

| # | Zadanie z PDF | Gdzie w raporcie |
|---|----------------|------------------|
| 1 | `radon`: CC każdej metody + MI pliku | §2 |
| 2 | Metody o najwyższej złożoności — co ją podnosi | §3 |
| 3 | `pylint` / `flake8` + ocena uwag | §4 |
| 4 | Ręczny przegląd kodu | §5 |
| 5 | Porównanie ze wcześniejszymi testami | §6 |

---

## 2. Metryki radon

### 2.1. Złożoność cyklomatyczna (McCabe)

Progi z instrukcji: **1–10** proste, **11–20** uwaga, **> 20** kandydat do podziału.  
U nas wszystkie bloki są w paśmie A/B (≤ 6). Średnia dla pliku: **A (2,83)**.

| Blok | CC | Ocena radon | Co podnosi CC |
|------|----|-------------|---------------|
| `BankSystem.wyciag_miesieczny` | **6** | B | pętla + warunek miesiąca + `if/elif` po typach operacji |
| `BankSystem._numer_poprawny` | 5 | A | `isinstance` / długość / `isdigit` (or) + porównanie cyfry kontrolnej |
| `BankSystem.wyplac` | 5 | A | status, znak kwoty, saldo, limit dzienny |
| `BankSystem.przelew` | 5 | A | status, znak kwoty, saldo, limit systemowy (+ lock, dwa konta) |
| `BankSystem.przelew_zewnetrzny` | 5 | A | status, znak kwoty, saldo (+ procesor) |
| `BankSystem._suma_dzisiejszych_wyplat` | 4 | A | pętla historii + filtr daty i typu |
| `BankSystem.wplac` | 3 | A | typ kwoty + znak |
| `BankSystem.utworz_konto` | 3 | A | walidacja numeru + duplikat |
| pozostałe | 1–3 | A | proste ścieżki |

Pełny dump: `docs/_lab6_radon_cc.txt`.

### 2.2. Indeks utrzymywalności (MI)

| Plik | MI | Ocena radon |
|------|----|-------------|
| `API.py` | **42,04** | A |

Skala z instrukcji: poniżej **20** — trudny w utrzymaniu. **42** jest powyżej progu ostrzegawczego; plik jest krótki (SLOC 161), więc MI nie spada mimo kilku metod z CC 5–6.

### 2.3. Surowy rozmiar (`radon raw`)

| Metryka | Wartość |
|---------|---------|
| LOC | 216 |
| SLOC | 161 |
| LLOC | 170 |
| Komentarze jednoliniowe | 3 |
| Bloki docstring / multi | 19 |
| Puste linie | 33 |

### 2.4. Halstead (wybrane metody, wysiłek)

| Metoda | Volume | Difficulty | Effort |
|--------|--------|------------|--------|
| `przelew` | 62,3 | 5,0 | **311** |
| `wyciag_miesieczny` | 84,0 | 2,3 | 196 |
| `przelew_zewnetrzny` | 53,8 | 3,6 | 192 |
| `_numer_poprawny` | 66,4 | 2,8 | 183 |
| `wyplac` | 49,8 | 3,3 | 166 |

`przelew` ma najwyższy **effort** Halsteada przy tym samym CC co `wyplac` — więcej operandów (dwa konta, limit 1e6, lock).

---

## 3. Metody o najwyższej złożoności — opis

### `wyciag_miesieczny` (CC 6)

Zagnieżdżenie: pętla po historii → warunek `year`/`month` → rozgałęzienie typów na wpłaty vs wypłaty. To nie jest „błąd”, tylko wiele równorzędnych przypadków w jednej funkcji. Ryzyko: pominięcie typu operacji (np. `przelew_zewnetrzny` nie wchodzi ani do wpłat, ani do wypłat) — widać dopiero przy testach funkcjonalnych / przeglądzie, nie w samej liczbie CC.

### `wyplac` / `przelew` / `przelew_zewnetrzny` (CC 5)

Każda metoda to łańcuch walidacji (konto / blokada / kwota / środki / limit). CC jest umiarkowane, ale **logika biznesowa jest wrażliwa na kolejność warunków** — to właśnie ujawniły testy z lab 4 (limit sprawdzany za późno w `przelew`, brak sumy dziennej w `wyplac`).

### `_numer_poprawny` (CC 5)

Jedna linia z trzema warunkami złożonymi `or` podnosi CC bez zagnieżdżeń. Algorytm cyfry kontrolnej jest czytelny; ryzyko to raczej komunikaty / format numeru niż struktura sterowania.

---

## 4. flake8 i pylint — uwagi z komentarzem

### 4.1. flake8 (12 zgłoszeń)

| Kod | Przykład | Ocena zespołu |
|-----|----------|----------------|
| **F541** | L87 `f"Konto {{numer}} juz istnieje"`, L144 analogicznie dla `{numer_z}` | **Zasadne.** Podwójne nawiasy → literał `{numer}` w komunikacie. Zgodne z obserwacją z lab 4. |
| **E501** | linie > 79 znaków | **Styl / fałszywy alarm w tym kontekście.** Plik ma też próg pylint 100; czytelność nie cierpi. |
| **W292** | brak newline na końcu pliku | **Zasadne, kosmetyczne.** Łatwa poprawka. |

### 4.2. pylint — wynik **7,88 / 10**

| Kod | Treść | Ocena |
|-----|--------|-------|
| **W1309** | f-string bez interpolacji (L87, L144) | **Zasadne** — ten sam bug co F541. |
| **W0613** | nieużywane argumenty w `ZewnetrznyProcesor.wyslij_przelew` | **Fałszywy alarm względem intencji SUT.** Sygnatura jest częścią API procesora; ciało celowo ignoruje wartości i tylko losuje awarię. |
| **C0115 / C0116** | brak docstringów na `Konto`, `BankSystem`, większości metod | **Częściowo zasadne.** Dokumentacja zewnętrzna jest w `sut_dokumentacja.pdf`; docstringi w kodzie są niespójne (jest przy `przelew_zewnetrzny` i wyjątkach). |
| **C0103** | nazwa modułu `API` ≠ snake_case | **Fałszywy alarm projektowy.** Nazwa pliku jest narzucona wariantem / repo. |
| **W0107** | `pass` w klasach wyjątków | **Kosmetyczne.** Puste ciało wyjątku z docstringiem jest idiomatyczne; `pass` można usunąć. |
| **R0903** | za mało metod publicznych (`Konto`, `ZewnetrznyProcesor`) | **Fałszywy alarm.** To nośniki stanu / stub integracji, nie service object. |
| **W0621** | `konto` redefiniuje nazwę z `if __name__ == "__main__"` | **Fałszywy alarm.** Konflikt tylko z demo na dole pliku, nie z logiką biblioteki. |
| **C0301 / C0304** | długa linia, brak final newline | jak E501 / W292 |

**Wniosek narzędziowy:** nie liczyć ostrzeżeń „na sztuki”. Dwa prawdziwe sygnały jakości to **F541/W1309** (zepsute komunikaty) oraz świadomość, że linter **nie** zgłasza braku wywołania `_suma_dzisiejszych_wyplat` ani kolejności limitu w `przelew`.

---

## 5. Ręczny przegląd kodu

Niezależnie od radon/pylint/flake8 (obserwacje z czytania `API.py`):

1. **`_suma_dzisiejszych_wyplat` istnieje, ale `wyplac` jej nie woła.** Limit w `wyplac` to tylko `kwota > LIMIT_DZIENNY_WYPLAT`. To jest dokładnie rozbieżność D1 ze specyfikacji (lab 4): suma dzienna wypłat + przelewów wychodzących.
2. **`przelew`: odjęcie salda i wpis historii *przed* sprawdzeniem limitu 1 000 000.** Przy kwocie > 1e6 wyjątek leci, a środki znikają ze źródła (lab 4, D2).
3. **Niespójna walidacja typu kwoty:** `wplac` rzuca `TypeError`; `wyplac` / `przelew` robią `Decimal(str(...))` i przepuszczają `"100"` albo rzucają `InvalidOperation` (lab 4, D3).
4. **F-stringi z podwójnymi nawiasami** w `utworz_konto` i `przelew` (blokada) — numer nie wchodzi do komunikatu.
5. **Lock tylko w `przelew`.** Zgodnie z dokumentacją (dwa konta). `wplac`/`wyplac` bez locka — temat lab 5 (współbieżność).
6. **`przelew_zewnetrzny`:** jedna próba, brak retry — celowe na blok odporności; linter tego nie ocenia jako „błąd”, przegląd tak (świadoma kruchość).
7. **`wyciag_miesieczny` pomija `przelew_zewnetrzny`** w sumach wpłat/wypłat — nie wynika wprost z sekcji 6.8 docs (wymienia konkretne typy); warto to mieć na liście pytań do prowadzącego / późniejszej poprawki.
8. **Brak walidacji `miesiace` / stopy** w `nalicz_odsetki` (0 i ujemne miesiące = no-op).

---

## 6. Porównanie z testami z wcześniejszych bloków

| Metoda (wysokie CC / effort) | Co pokazały testy wcześniej | Czy pokrywa się ze statyką? |
|------------------------------|-----------------------------|-----------------------------|
| `wyplac` (CC 5) | Lab 4: brak limitu łącznego; zły typ kwoty | **Tak.** CC wynika z wielu warunków, ale usterka to *brak* warunku (suma) — metryka tego nie widzi, przegląd i testy funkcjonalne tak. |
| `przelew` (CC 5, najwyższy Halstead effort) | Lab 4: utrata środków przy limicie; lab 5: lock stabilizuje współbieżność | **Tak.** Wysoki effort + kolejność `if` = miejsce, gdzie testy funkcjonalne i niefunkcjonalne coś znalazły. |
| `przelew_zewnetrzny` (CC 5) | Testy stubem procesora; awaria = `ProcesorNiedostepny` | Częściowo — CC z walidacji; kruchość integracji jest zamierzona, nie „bug do naprawy teraz”. |
| `wyciag_miesieczny` (CC 6, najwyższe CC) | Testy strukturalne/pokrycie; bez dużych xfail z lab 4 | **Częściowo nie.** Najwyższe CC ≠ najwięcej znalezionych usterek. Złożoność to klasyfikacja typów, nie błędna kolejność efektów ubocznych. |
| `_suma_dzisiejszych_wyplat` (CC 4) | Test jednostkowy metody pomocniczej w `test_bank.py` | Metoda jest „zielona” w coverage, ale **martwa w ścieżce produkcyjnej** — coverage + CC mylą, przegląd demaskuje. |

**Wniosek łączący bloki:**  
metody wskazane przez radon jako „ciekawsze” (`wyplac`, `przelew`) **pokrywają się** z miejscami, gdzie testy funkcjonalne (lab 4) ujawniły rozbieżności ze specyfikacją. Same metryki **nie wystarczyłyby**: najwyższe CC ma `wyciag_miesieczny`, a najgroźniejsza usterka biznesowa siedzi w kolejności instrukcji w `przelew` (efekt uboczny przed `raise`) — tego CC nie wyróżnia ponad inne walidacje. Analiza statyczna jest kompasem; przegląd + testy dynamiczne dają dowód.

---

## 7. Co wkleić do raportu zespołowego

1. Tabelę CC (§2.1) + MI = **42,04**.  
2. Fragment flake8/pylint z komentarzem „zasadne vs fałszywy alarm” (§4) — zwłaszcza **F541/W1309**.  
3. 3–5 punktów z przeglądu ręcznego (§5), w tym nieużywane `_suma_dzisiejszych_wyplat` i kolejność limitu w `przelew`.  
4. Zdanie z §6: metody złożone ≈ problematyczne w lab 4, ale MI/CC same nie wykrywają race ani braku wymagania ze specyfikacji.

### Co zescreenować

1. Terminal: `radon cc API.py -s -a` (średnia + top metody).  
2. Terminal: `radon mi API.py -s`.  
3. Terminal: `flake8 API.py` (widać F541).  
4. Terminal: `pylint API.py` (score ~7.9).  
5. Edytor: fragment `wyplac` bez wywołania `_suma_...` oraz `przelew` z limitem po `saldo -=`.

---

## 8. Pytania kontrolne — odpowiedzi

**1. Czym analiza statyczna różni się od testowania? Czego nie wykryje?**  
Statyczna ocenia tekst źródłowy bez uruchamiania. Dynamiczna uruchamia program na konkretnych danych. Statyczna nie wykryje m.in. race condition (lab 5), usterek zależnych od konkretnych wartości wejściowych czy czasu, ani „brakującego wymagania”, którego nie ma w kodzie (limit łączny).

**2. Co mierzy złożoność cyklomatyczna i jak czytać wysoką wartość?**  
Liczbę niezależnych ścieżek ≈ decyzje + 1. Wysoka wartość = trudniej przetestować wyczerpująco i większe ryzyko usterki; to sygnał do przeglądu / ewentualnego podziału, nie automatyczny dowód błędu.

**3. Co to MI i z czego się buduje?**  
Maintainability Index (0–100): łączy m.in. CC, objętość Halsteada i liczbę linii. Im wyżej, tym łatwiejszy kod w utrzymaniu; poniżej ~20 — trudny.

**4. Dlaczego metryki nie zastępują przeglądu przez człowieka?**  
Metryki nie rozumieją intencji biznesowej ani kolejności efektów ubocznych. U nas CC nie wyróżnia „odjęcie salda przed limitem”, a linter nie krzyczy, że `_suma_dzisiejszych_wyplat` nie jest wołana z `wyplac`. Człowiek + testy ze specyfikacji to uzupełniają.

---

## 9. Przygotowanie do zajęć nr 7

Z PDF: mieć komplet testów z P2/P3 w repo; upewnić się, że repo jest na GitHubie (lub innym CI).  
U nas: `tests/test_bank.py`, `tests/test_funkcjonalne.py`, `tests/test_niefunkcjonalne.py` — gotowe do spięcia w pipeline.
