# Zajęcia projektowe nr 4 — testy funkcjonalne

**Zespół E.** SUT: `BankSystem` (`API.py`).  
Podstawa przypadków: `docs/sut_dokumentacja.pdf`, nie struktura kodu.  
Testy: `tests/test_funkcjonalne.py`.

Do raportu projektowego wchodzą cztery rzeczy z instrukcji: klasy równoważności i wartości brzegowe, tablica decyzyjna z testami, rozbieżności dokumentacji z zachowaniem oraz wnioski. Na końcu są odpowiedzi na pytania kontrolne.

Uruchomienie:

```bash
uv run pytest tests/test_funkcjonalne.py -o addopts= -rx
```

Wynik: **54 przypadki, 46 passed, 8 xfailed**. Znacznik `xfail(strict=True)` oznacza test napisany pod specyfikację, który SUT oblewa. Suite zostaje zdatny do zajęć nr 5, a rozbieżność nie ginie w tłumie. Po naprawie SUT taki test zacznie przechodzić i pytest zgłosi `XPASS`, dopóki znacznik nie zostanie zdjęty.

Surowe czerwone wyniki tych ośmiu testów:

```bash
uv run pytest tests/test_funkcjonalne.py -o addopts= --runxfail --tb=short \
  -k "limit_laczny or nie_zmienia_stanu or napis_liczbowy or nieliczbowa"
```

## 1. Wybrane metody

Instrukcja każe wziąć dwie albo trzy metody, inne niż te rozbierane strukturalnie na zajęciach 2 i 3, albo te same, ale ze specyfikacji.

| Metoda | Dlaczego ta |
| --- | --- |
| `utworz_konto` | Sekcja 3 specyfikacji (długość, same cyfry, cyfra kontrolna) nie była osobnymi klasami w `tests/test_bank.py`. Tamten plik sprawdzał numer za krótki i numer z literami. |
| `wyplac` | Ta sama metoda co w testach strukturalnych, nowa perspektywa. Specyfikacja 6.4 definiuje limit 5000 jako sumę dzienną wypłat i przelewów wychodzących. Testy z zajęć 2 i 3 porównywały z limitem jedną kwotę. |
| `przelew` | Zachowanie zależy naraz od istnienia obu kont, blokady, znaku kwoty, salda i limitu 1 000 000. Do tego jest tablica decyzyjna. |

`wplac` zostało przy testach strukturalnych: jego kontrakt (typ kwoty, kwota dodatnia, brak konta) jest tam już pokryty i zgodny ze specyfikacją.

## 2. Klasy równoważności i wartości brzegowe

Klasa to zbiór danych, w którym specyfikacja opisuje jeden sposób reakcji. Z klasy bierzemy reprezentanta, a na granicy klas wartość brzegową i sąsiadów. Słowo „przekracza” w specyfikacji czytamy jako relację ostrą: wartość równa granicy jest jeszcze dopuszczalna.

### 2.1. `utworz_konto(numer, wlasciciel, saldo_poczatkowe=0)`

Cyfra kontrolna: \(c_{10} = (c_1+\ldots+c_9) \bmod 10\). Dla `1234567895` suma wynosi 45, 45 mod 10 = 5, numer jest poprawny. Sąsiednie cyfry kontrolne to 4 i 6.

| Klasa | Reprezentant | Oczekiwane wg specyfikacji | Test | Wynik |
| --- | --- | --- | --- | --- |
| 10 cyfr, dobra cyfra kontrolna, saldo 0,01 | `1111111119`, „Anna Nowak”, 0,01 | konto, saldo 0,01, status „aktywne” | `test_utworz_konto_poprawny_numer_i_saldo_brzegowe` | zgodny |
| saldo domyślne oraz jawne 0 | brak argumentu; `0` | saldo 0 | `test_utworz_konto_saldo_domyslne_i_zero` | zgodny |
| same zera (suma kontrolna = 0) | `0000000000` | konto utworzone | `test_utworz_konto_zera_wiodace` | zgodny |
| właściciel: pusty napis | `""` | specyfikacja mówi „dowolna nazwa” i nie wyklucza pustego napisu | `test_utworz_konto_pusty_wlasciciel` | zgodny |
| saldo ujemne | `-50` | parametr jest liczbą, znaku specyfikacja nie zabrania | `test_utworz_konto_saldo_ujemne` | zgodny |
| długość 9 | `123456789` | `ValueError` | `...numer_poza_klasa_poprawna[dlugosc-9]` | zgodny |
| długość 11 | `12345678950` | `ValueError` | `...[dlugosc-11]` | zgodny |
| pusty numer | `""` | `ValueError` | `...[pusty]` | zgodny |
| znak inny niż cyfra | `123456789a`, `123456789 ` | `ValueError` | `...[litera]`, `...[spacja]` | zgodny |
| cyfra kontrolna o 1 za mała | `1234567894` | `ValueError` | `...[kontrolna-o-1-za-mala]` | zgodny |
| cyfra kontrolna o 1 za duża | `1234567896` | `ValueError` | `...[kontrolna-o-1-za-duza]` | zgodny |
| typ inny niż napis | `1234567895` jako int, `None` | `ValueError` (to nie jest ciąg dziesięciu cyfr) | `...[int-zamiast-napisu]`, `...[none]` | zgodny |
| numer już istnieje | drugi raz `1234567895` | `ValueError`, pierwsze konto bez zmian | `test_utworz_konto_duplikat` | zgodny |

Wartości brzegowe numeru: długości 9, 10 i 11 oraz cyfra kontrolna \(c\), \(c-1\), \(c+1\). Wartości brzegowe salda: brak argumentu, 0, 0,01, liczba ujemna.

Numer `9999999991` ma poprawną cyfrę kontrolną (suma 81, reszta 1), ale konta o tym numerze nie zakładamy. To inna klasa niż zły numer: przy wypłacie i przelewie daje `KontoNieIstnieje`, nie `ValueError`.

### 2.2. `wyplac(numer, kwota)`

Saldo konta testowego A (`1234567895`) to 10 000, chyba że opis testu mówi inaczej. Limit dzienny ze specyfikacji: 5000, liczony łącznie z wypłatami i przelewami wychodzącymi danego dnia.

| Klasa | Reprezentant | Oczekiwane | Test | Wynik |
| --- | --- | --- | --- | --- |
| konto nie istnieje | `9999999991`, kwota −1 | `KontoNieIstnieje` | `test_wyplac_konto_nie_istnieje` | zgodny |
| konto zablokowane | kwoty 0, −0,01 i 100 | `KontoZablokowane`, saldo bez zmian | `test_wyplac_zablokowane_ma_pierwszenstwo` | zgodny |
| kwota niedodatnia | 0, −0,01, −1 | `ValueError`, saldo bez zmian | `test_wyplac_kwota_niedodatnia` | zgodny |
| 0 < kwota < saldo, poniżej limitu | 0,01 oraz 100 | nowe saldo | `test_wyplac_kwota_minimalna`, `test_wyplac_sukces_i_wpis` | zgodny |
| kwota = saldo, saldo poniżej limitu | saldo 100, kwota 100 | saldo 0 | `test_wyplac_rowna_saldu_ponizej_limitu` | zgodny |
| kwota = saldo + 0,01, nadal poniżej limitu | saldo 100, kwota 100,01 | `ValueError`, saldo 100 | `test_wyplac_brak_srodkow` | zgodny |
| pojedyncza kwota 4999,99 i 5000 | przy saldzie 10 000 | wypłata wykonana | `test_wyplac_brzeg_pojedynczej_kwoty_w_limicie` | zgodny |
| pojedyncza kwota 5000,01 | przy saldzie 10 000 | `ValueError`, saldo bez zmian | `test_wyplac_pojedyncza_kwota_ponad_limit` | zgodny |
| suma dwóch wypłat = 5000 | 3000, potem 2000 | obie wykonane, saldo 5000 | `test_wyplac_suma_dzienna_rowna_limitowi` | zgodny |
| suma dwóch wypłat = 5000,01 | 3000, potem 2000,01 | druga: `ValueError`, saldo zostaje 7000 | `test_wyplac_druga_wyplata_przekracza_limit_laczny` | **niezgodny** |
| przelew wychodzący + wypłata = 5000 | przelew 4000, wypłata 1000 | wypłata wykonana | `test_wyplac_suma_z_przelewem_rowna_limitowi` | zgodny |
| przelew + wypłata = 5000,01 | przelew 4000, wypłata 1000,01 | wypłata: `ValueError`, saldo A zostaje 6000 | `test_wyplac_po_przelewie_przekracza_limit_laczny` | **niezgodny** |
| kwota `float` | 10,5 | saldo 9989,5 | `test_wyplac_kwota_float` | zgodny |
| napis wyglądający na liczbę | `"100"` | `TypeError` (sekcja 4: tylko int, float, Decimal) | `test_wyplac_napis_liczbowy` | **niezgodny** |
| wartość nieliczbowa | `"abc"`, `None` | `TypeError`, saldo bez zmian | `test_wyplac_kwota_nieliczbowa` | **niezgodny** |

Granice kwoty względem zera: −0,01, 0, 0,01. Granice względem salda (saldo 100, żeby nie zlały się z limitem 5000): 100 i 100,01. Granice limitu pojedynczej kwoty: 4999,99, 5000, 5000,01. Granice sumy dziennej: 5000 i 5000,01, osobno dla samych wypłat i dla wypłaty po przelewie wychodzącym.

Test sumy równej dokładnie 5000 przechodzi i **nie wykrywa** usterki. Obie kwoty składowe są same w sobie mniejsze od 5000, więc implementacja, która ignoruje sumę, też je przyjmie. Ujawnienie jest dopiero przy 5000,01.

### 2.3. `przelew(numer_z, numer_do, kwota)`

Limit systemowy dotyczy pojedynczej kwoty: specyfikacja mówi, że `ValueError` jest wtedy, gdy **kwota** przekracza 1 000 000. Dwa przelewy po 600 000 (suma 1 200 000) są więc w specyfikacji dopuszczalne i implementacja je wykonuje.

| Klasa | Reprezentant | Oczekiwane | Test | Wynik |
| --- | --- | --- | --- | --- |
| brak konta źródłowego | `9999999991` | `KontoNieIstnieje`, cel bez zmian | `test_przelew_brak_konta_zrodlowego` | zgodny |
| brak konta docelowego | cel `9999999991` | `KontoNieIstnieje`, źródło bez zmian | `test_przelew_brak_konta_docelowego` | zgodny |
| źródło zablokowane | kwota 1 000 001 przy saldzie powyżej tej kwoty | `KontoZablokowane`, oba salda bez zmian | `test_przelew_zrodlo_zablokowane_ma_pierwszenstwo` | zgodny |
| kwota niedodatnia | 0, −0,01 | `ValueError`, salda bez zmian | `test_przelew_kwota_niedodatnia` | zgodny |
| kwota > saldo | 1 000 001 przy saldzie 10 000 | `ValueError`, salda bez zmian | `test_przelew_brak_srodkow` | zgodny |
| typowa kwota dodatnia | 100 | saldo źródła 9900, cel 100 | `test_przelew_sukces` | zgodny |
| kwota minimalna | 0,01 | saldo źródła 9999,99, cel 0,01 | `test_przelew_kwota_minimalna` | zgodny |
| kwota = saldo | 10 000 | źródło 0, cel 10 000 | `test_przelew_cale_saldo` | zgodny |
| cel zablokowany | cel zablokowany, kwota 25 | przelew wykonany; specyfikacja zabrania tylko zablokowanego źródła | `test_przelew_na_konto_zablokowane` | zgodny |
| ten sam numer źródła i celu | 10 na własne konto | specyfikacja milczy; saldo netto bez zmian, w historii obie nogi przelewu | `test_przelew_na_to_samo_konto` | brak sprzeczności ze specyfikacją |
| kwota 999 999,99 | po wpłacie 2 000 000 | przelew wykonany | `test_przelew_tuz_ponizej_limitu` | zgodny |
| kwota = 1 000 000 | j.w. | przelew wykonany, cel ma 1 000 000 | `test_przelew_dokladnie_limit` | zgodny |
| kwota = 1 000 000,01, środki są | saldo przed operacją 2 010 000 | `ValueError` | `test_przelew_ponad_limit_wyjatek` | zgodny co do wyjątku |
| ta sama kwota, warunek końcowy | j.w. | salda i historia **bez zmian** | `test_przelew_ponad_limit_nie_zmienia_stanu` | **niezgodny** |
| napis `"50"` | | `TypeError` | `test_przelew_napis_liczbowy` | **niezgodny** |
| napis `"abc"` | | `TypeError`, salda bez zmian | `test_przelew_kwota_nieliczbowa` | **niezgodny** |

Granice: 0 i 0,01; saldo oraz saldo + 0,01 (tu wpadają w klasę braku środków, bo 10 000,01 < 1 000 000); 999 999,99, 1 000 000 i 1 000 000,01.

Usterka atomowości widać tylko w ostatniej trójce, i tylko gdy środków starcza. Przelew 1 000 001 przy saldzie 10 000 kończy się `ValueError` i **nie** rusza salda, więc test braku środków tej usterki nie zobaczy.

## 3. Tablice decyzyjne

Znak „–” oznacza warunek bez znaczenia: wcześniejszy warunek już ustala wynik. Dla trzech niezależnych warunków pełna tablica miałaby 8 wierszy. Po złożeniu warunków maskujących zostaje mniej.

### 3.1. `wyplac`

Warunki: konto istnieje, konto jest zablokowane, kwota jest dodatnia, kwota mieści się w saldzie, suma dzisiejszych wypłat i przelewów wychodzących razem z tą kwotą mieści się w 5000.

| | Istnieje | Zablokowane | Kwota > 0 | Kwota ≤ saldo | Suma + kwota ≤ 5000 | Wynik | Test |
| --- | --- | --- | --- | --- | --- | --- | --- |
| W0 | nie | – | – | – | – | `KontoNieIstnieje` | `test_wyplac_konto_nie_istnieje` |
| W1 | tak | tak | – | – | – | `KontoZablokowane`, saldo bez zmian | `test_wyplac_zablokowane_ma_pierwszenstwo` (kwoty 0, −0,01 i 100) |
| W2 | tak | nie | nie | – | – | `ValueError`, saldo bez zmian | `test_wyplac_kwota_niedodatnia` |
| W3 | tak | nie | tak | nie | – | `ValueError`, saldo bez zmian | `test_wyplac_brak_srodkow` |
| W4 | tak | nie | tak | tak | nie | `ValueError`, saldo bez zmian | `test_wyplac_pojedyncza_kwota_ponad_limit`; `test_wyplac_druga_wyplata_przekracza_limit_laczny`; `test_wyplac_po_przelewie_przekracza_limit_laczny` |
| W5 | tak | nie | tak | tak | tak | nowe saldo | `test_wyplac_sukces_i_wpis` oraz testy brzegów 0,01, 5000 i sumy = 5000 |

Wiersz W1 jest sprawdzony trzema kwotami, w tym niedodatnimi, żeby „–” było naprawdę obojętne, a nie tylko jedną szczęśliwą wartością. Typ kwoty (int, float, Decimal albo coś innego) jest osobną osią, poza tą tablicą: sekcja 4 specyfikacji.

W4 jest zgodny ze specyfikacją dla pojedynczej kwoty 5000,01. Dla sumy dziennej nie jest.

### 3.2. `przelew`

Warunki: istnieje źródło, istnieje cel, źródło jest zablokowane, kwota jest dodatnia, kwota mieści się w saldzie źródła, kwota nie przekracza 1 000 000.

| | Źródło | Cel | Źródło zablokowane | Kwota > 0 | Kwota ≤ saldo | Kwota ≤ 1 000 000 | Wynik | Test |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| T0 | nie | – | – | – | – | – | `KontoNieIstnieje` | `test_przelew_brak_konta_zrodlowego` |
| T1 | tak | nie | – | – | – | – | `KontoNieIstnieje`, źródło bez zmian | `test_przelew_brak_konta_docelowego` |
| T2 | tak | tak | tak | – | – | – | `KontoZablokowane`, salda bez zmian | `test_przelew_zrodlo_zablokowane_ma_pierwszenstwo` |
| T3 | tak | tak | nie | nie | – | – | `ValueError`, salda bez zmian | `test_przelew_kwota_niedodatnia` |
| T4 | tak | tak | nie | tak | nie | – | `ValueError`, salda bez zmian | `test_przelew_brak_srodkow` |
| T5 | tak | tak | nie | tak | tak | nie | `ValueError`, salda i historia bez zmian | `test_przelew_ponad_limit_wyjatek`, `test_przelew_ponad_limit_nie_zmienia_stanu` |
| T6 | tak | tak | nie | tak | tak | tak | saldo źródła po przelewie | `test_przelew_sukces` oraz brzegi 0,01, całe saldo, 999 999,99 i 1 000 000 |

T2 używa kwoty 1 000 001 przy wystarczającym saldzie, więc wiersz odróżnia blokadę od limitu i od braku środków. T4 używa tej samej kwoty przy saldzie 10 000: wyjątek jest, stan zostaje. Rozjazd ze specyfikacją siedzi w T5, w warunku „stan bez zmian”, nie w samym fakcie `ValueError`.

Poza tablicą, bo specyfikacja ich nie rozstrzyga jako błędów: przelew na konto zablokowane (`test_przelew_na_konto_zablokowane`, wykonany) oraz przelew na własne konto (`test_przelew_na_to_samo_konto`, saldo netto bez zmian, w historii `przelew_wychodzacy` i `przelew_przychodzacy`).

## 4. Rozbieżności dokumentacji i zachowania

### 4.1. Limit dzienny wypłaty nie jest sumą

Specyfikacja 6.4: `ValueError`, gdy kwota przekracza dzienny limit 5000, „liczony łącznie dla wypłat i przelewów wychodzących danego dnia kalendarzowego”.

Faktycznie druga operacja przechodzi, jeśli sama kwota jest ≤ 5000:

- wypłata 3000, potem 2000,01: druga się udaje, saldo spada z 7000 do 4999,99; specyfikacja wymaga `ValueError` i salda 7000;
- przelew wychodzący 4000, potem wypłata 1000,01: wypłata się udaje, saldo A spada z 6000 do 4999,99; specyfikacja wymaga odrzucenia wypłaty.

Pojedyncza kwota 5000,01 jest odrzucana, a 5000 przechodzi. Granica jednej operacji jest więc zrobiona. Brakuje zliczenia historii z danego dnia.

Testy: `test_wyplac_druga_wyplata_przekracza_limit_laczny`, `test_wyplac_po_przelewie_przekracza_limit_laczny`. Przy `--runxfail` oba kończą się `Failed: DID NOT RAISE ValueError`.

Testy strukturalne tego nie mogły wymusić. W kodzie nie ma gałęzi „suma dzienna > 5000”, jest tylko porównanie jednej kwoty. Pokrycie gałęzi i mutacja tej gałęzi pilnują istniejącego warunku, nie warunku zapisanego wyłącznie w specyfikacji. `test_wyplac_limit` z zajęć 2 i 3 woła wypłatę raz, z kwotą `LIMIT + 1`.

### 4.2. Przelew ponad 1 000 000 zabiera pieniądze i zgłasza błąd

Specyfikacja 6.5: kwota powyżej 1 000 000 kończy się `ValueError`. Operacja albo przenosi środki, albo wyjątek oznacza, że przeniesienia nie było.

Przy saldzie 2 010 000 (10 000 na starcie plus wpłata 2 000 000) przelew 1 000 000,01:

- zgłasza `ValueError` z tekstem „Przelew przekracza dzienny limit systemowy” (sam wyjątek jest zgodny z T5);
- saldo źródła spada do 1 009 999,99, czyli dokładnie o 1 000 000,01;
- konto docelowe zostaje przy 0;
- w historii źródła zostaje wpis przelewu wychodzącego.

Różnica 1 000 000,01 znika z systemu. Test `test_przelew_ponad_limit_nie_zmienia_stanu` pada na porównaniu salda: `Decimal('1009999.99') != Decimal('2010000')`.

`test_przelew_limit_systemowy` z zajęć 2 i 3 sprawdza tylko wyjątek. Wyjątek jest, więc test strukturalny był zielony i usterki nie pokazał. Żeby ją zobaczyć, trzeba asercji stanu po błędzie. Dodatkowo widać ją dopiero, gdy kwota jest większa od 1 000 000 **i** nie większa od salda. Sam brak środków (T4) stanu nie psuje.

Słowo „dzienny” w komunikacie nie zgadza się z nazwą ze specyfikacji („globalny limit systemowy”). Próg kwoty zachowuje się jak limit jednej operacji, nie jak suma dzienna.

### 4.3. Zły typ kwoty przy wypłacie i przelewie

Sekcja 4: kwota operacji, która nie jest `int`, `float` ani `Decimal`, kończy się `TypeError`. `wplac` tak robi (`test_wplac_zly_typ_kwoty`). `wyplac` i `przelew` nie:

- `"100"` i `"50"` są przyjmowane jak liczby, wyjątku nie ma;
- `"abc"` i `None` dają `decimal.InvalidOperation`, którego nie ma w tabeli wyjątków specyfikacji. Kod wołający, napisany pod dokumentację, nie złapie tego wyjątku klauzulą `TypeError`.

Testy: `test_wyplac_napis_liczbowy`, `test_wyplac_kwota_nieliczbowa`, `test_przelew_napis_liczbowy`, `test_przelew_kwota_nieliczbowa`.

W `wyplac` i `przelew` nie ma gałęzi sprawdzającej typ. Testy pisane z kodu nie miały czego pokryć, więc klasa ze specyfikacji została pominięta.

### 4.4. Obserwacje, które specyfikacja zostawia

To nie są naruszenia kontraktu. Specyfikacja albo milczy, albo wymaga tylko typu wyjątku, bez treści komunikatu.

- Duplikat konta: `ValueError`, zgodnie ze specyfikacją, ale komunikat to dosłownie `Konto {numer} juz istnieje`. Numer się nie podstawia.
- Przelew z konta zablokowanego: `KontoZablokowane`, komunikat `Konto {numer_z} jest zablokowane`. Ta sama wypłata z konta zablokowanego wstawia prawdziwy numer.
- Ujemne saldo początkowe jest przyjmowane. Specyfikacja mówi „liczba”, bez warunku `> 0`.
- Przelew na własne konto nie zmienia salda netto i dopisuje obie nogi historii. Osobnego zakazu w specyfikacji nie ma.
- Wpłata na konto zablokowane przechodzi. Zakaz blokady specyfikacja stawia przy wypłacie, przelewie i przelewie zewnętrznym, nie przy wpłacie.

## 5. Wnioski

Podejście czarnoskrzynkowe pokazało usterki, których testy strukturalne z zajęć 2 i 3 nie pokazały, mimo wysokiego pokrycia gałęzi i pracy z mutantami.

1. **Brakującego wymagania nie widać w pokryciu.** Limit liczony łącznie jest w zdaniu specyfikacji, a nie w `if` w kodzie. Stuprocentowe pokrycie gałęzi implementacji dalej jest zielone. Testy funkcjonalne biorą to zdanie jako warunek W4.
2. **Wyjątek bez warunku końcowego jest słabym testem.** Przelew ponad milion zgłasza `ValueError`, więc test z zajęć 2 i 3 przechodzi. Pieniądze i tak schodzą ze źródła i nie dochodzą do celu. Asercja „po wyjątku stan jest taki jak przed wywołaniem” jest z kontraktu operacji, nie z kształtu kodu.
3. **Granica równa limitowi nie wystarcza.** Wypłaty 3000 i 2000 (suma 5000) przechodzą i u implementacji zgodnej ze specyfikacją, i u takiej, która sumy nie liczy. Dopiero 2000,01 po pierwszej wypłacie rozdziela te dwa programy. To jest powód, dla którego wartości brzegowe bierze się po obu stronach granicy.
4. **Ta sama metoda, inne pytanie.** `wyplac` i `przelew` były już na zajęciach 2 i 3. Tam pytanie brzmiało „która gałąź się wykonała”. Tu brzmi „czy każda klasa ze specyfikacji daje opisany wynik”. Drugie pytanie znajduje inny zbiór usterek: zły typ kwoty, sumę dzienną i utratę środków przy odrzuconym przelewie.

Czego ten zestaw nie robi: nie zastępuje testów strukturalnych. Zostają w `tests/test_bank.py`. Pełny `uv run pytest` po dopisaniu testów funkcjonalnych: 82 passed, 8 xfailed, pokrycie `API.py` 100% instrukcji i gałęzi. Te 8 xfail to świadomie zostawione rozbieżności, nie niedokończone przypadki.

## 6. Pytania kontrolne

**1. Na czym polega podział na klasy równoważności i dlaczego ogranicza liczbę testów bez utraty skuteczności?**

Zbiór możliwych danych wejściowych dzieli się na klasy, wewnątrz których specyfikacja opisuje to samo zachowanie. Zamiast próbować każdą wartość, bierze się po jednym reprezentancie z klasy. Dla kwoty wypłaty klasami są między innymi: kwota ujemna, zero, kwota dodatnia nie większa od salda i od limitu, kwota większa od salda, kwota, która przekracza limit dzienny. Skuteczność trzyma się założenia, że błąd, jeśli dotyczy całej klasy, ujawni się na reprezentancie. Założenie pada na granicy klas, dlatego same klasy uzupełnia się wartościami brzegowymi. Liczba testów spada z nieskończonej dziedziny do liczby klas i ich granic, a nie do losowej próbki.

**2. Dlaczego wartości brzegowe częściej ujawniają usterki niż środek klasy?**

Typowy błąd to zła relacja na granicy: `>` zamiast `>=`, licznik o jeden obok, warunek sprawdzony dla jednej operacji zamiast dla sumy. Wartość ze środka klasy, na przykład wypłata 100 przy saldzie 10 000 i limicie 5000, spełnia zarówno poprawny, jak i przesunięty o jeden warunek. Wartość równa granicy albo tuż za nią (5000 oraz 5000,01) już nie. W tym laboratorium widać to wprost: suma 3000 + 2000 nie odróżnia wadliwej implementacji od poprawnej, suma 3000 + 2000,01 odróżnia.

**3. Jak zbudować tablicę decyzyjną dla trzech niezależnych warunków i ile ma wierszy?**

Każdy warunek ma dwie wartości, więc najprostsza pełna tablica ma \(2^3 = 8\) wierszy: wszystkie kombinacje. W każdym wierszu zapisuje się oczekiwany wynik. Jeśli z specyfikacji wynika, że jeden warunek przesądza resztę (konto zablokowane, konta nie ma), pozostałe oznacza się „–” i wiersze, które różniły się tylko tymi warunkami, zlewa się w jeden. Tak z pełnej tablicy wypłaty zrobiło się 6 wierszy W0–W5, bo doszedł jeszcze warunek istnienia konta, a blokada i brak konta maskują pozostałe.

**4. Czym testy czarnoskrzynkowe różnią się od strukturalnych pod względem źródła projektu?**

Strukturalne projektuje się z kodu: instrukcje, gałęzie, warunki. Czarnoskrzynkowe ze specyfikacji: sygnatura, opis parametrów, granice, wyjątki, wynik. Wejście i oczekiwany wynik są znane, implementacja nie jest podstawą doboru danych. Dlatego test czarnoskrzynkowy może wymagać zachowania, którego w kodzie w ogóle nie ma (suma dzienna 5000), a test strukturalny może wykonać gałąź i nie sprawdzić warunku końcowego zapisanego w specyfikacji (saldo po odrzuconym przelewie).
