from decimal import Decimal

import pytest

from API import BankSystem, KontoNieIstnieje, KontoZablokowane

NUM_A = "1234567895"
NUM_B = "0000000000"
NUM_C = "9876543215"
NUM_BRAK = "9999999991"

LIMIT_DZIENNY = Decimal("5000")
LIMIT_PRZELEWU = Decimal("1000000")


@pytest.fixture
def bank():
    system = BankSystem()
    system.utworz_konto(NUM_A, "Anna Nowak", Decimal("10000"))
    system.utworz_konto(NUM_B, "Jan Kowalski", Decimal("0"))
    return system


ROZBIEZNOSC_LIMIT_DZIENNY = pytest.mark.xfail(
    reason=(
        "Spec. 6.4: limit 5000 jest suma wyplat i przelewow wychodzacych z danego dnia. "
        "Implementacja porównuje z limitem tylko pojedyncza kwote wyplac."
    ),
    strict=True,
)

ROZBIEZNOSC_TYP_KWOTY = pytest.mark.xfail(
    reason=(
        "Spec. sekcja 4: kwota niebedaca int, float ani Decimal konczy sie TypeError. "
        "wyplac i przelew przyjmuja napis liczbowy, a dla pozostalych wartosci "
        "zglaszaja decimal.InvalidOperation."
    ),
    strict=True,
)

ROZBIEZNOSC_ATOMOWOSC = pytest.mark.xfail(
    reason=(
        "Spec. 6.5: kwota powyzej 1000000 konczy sie ValueError. "
        "Przy wyjatku saldo zrodla i tak maleje, a w historii zostaje przelew wychodzacy; "
        "konto docelowe nie dostaje srodkow."
    ),
    strict=True,
)


# --- utworz_konto: klasy numeru, wlasciciela i salda poczatkowego ---


def test_utworz_konto_poprawny_numer_i_saldo_brzegowe():
    """Klasa: 10 cyfr i poprawna cyfra kontrolna; saldo dodatnie minimalne 0,01."""
    system = BankSystem()
    konto = system.utworz_konto("1111111119", "Anna Nowak", Decimal("0.01"))
    assert konto.numer == "1111111119"
    assert konto.wlasciciel == "Anna Nowak"
    assert konto.saldo == Decimal("0.01")
    assert konto.status == "aktywne"


def test_utworz_konto_saldo_domyslne_i_zero():
    system = BankSystem()
    domyslne = system.utworz_konto("1111111119", "Anna Nowak")
    jawne_zero = system.utworz_konto(NUM_C, "Jan Kowalski", 0)
    assert domyslne.saldo == Decimal("0")
    assert jawne_zero.saldo == Decimal("0")


def test_utworz_konto_zera_wiodace():
    """Brzeg sumy kontrolnej: suma cyfr 0, cyfra kontrolna 0."""
    system = BankSystem()
    konto = system.utworz_konto("0000000000", "X")
    assert konto.saldo == Decimal("0")


def test_utworz_konto_pusty_wlasciciel():
    """Brzeg „dowolnej nazwy": pusty napis. Specyfikacja go nie wyklucza."""
    system = BankSystem()
    konto = system.utworz_konto("1111111119", "")
    assert konto.wlasciciel == ""


def test_utworz_konto_saldo_ujemne():
    """Specyfikacja wymaga liczby, bez zakazu znaku. Ujemne saldo jest przyjmowane."""
    system = BankSystem()
    konto = system.utworz_konto("2222222228", "X", -50)
    assert konto.saldo == Decimal("-50")


@pytest.mark.parametrize(
    "numer",
    [
        pytest.param("123456789", id="dlugosc-9"),
        pytest.param("12345678950", id="dlugosc-11"),
        pytest.param("", id="pusty"),
        pytest.param("123456789a", id="litera"),
        pytest.param("123456789 ", id="spacja"),
        pytest.param("1234567894", id="kontrolna-o-1-za-mala"),
        pytest.param("1234567896", id="kontrolna-o-1-za-duza"),
        pytest.param(1234567895, id="int-zamiast-napisu"),
        pytest.param(None, id="none"),
    ],
)
def test_utworz_konto_numer_poza_klasa_poprawna(numer):
    system = BankSystem()
    with pytest.raises(ValueError):
        system.utworz_konto(numer, "X", 0)
    assert system.konta == {}


def test_utworz_konto_duplikat():
    system = BankSystem()
    system.utworz_konto(NUM_A, "Anna", Decimal("10"))
    with pytest.raises(ValueError):
        system.utworz_konto(NUM_A, "Ktos inny", Decimal("99"))
    assert system.konta[NUM_A].wlasciciel == "Anna"
    assert system.konta[NUM_A].saldo == Decimal("10")


# --- wyplac: tablica decyzyjna i wartosci brzegowe ---


def test_wyplac_konto_nie_istnieje(bank):
    """Wiersz: brak konta przesadza wynik, niezaleznie od kwoty."""
    with pytest.raises(KontoNieIstnieje):
        bank.wyplac(NUM_BRAK, -1)


@pytest.mark.parametrize("kwota", [0, Decimal("-0.01"), Decimal("100")])
def test_wyplac_zablokowane_ma_pierwszenstwo(bank, kwota):
    """Wiersz: konto zablokowane. Znak kwoty nie zmienia wyjatku."""
    bank.zablokuj_konto(NUM_A)
    przed = bank.konta[NUM_A].saldo
    with pytest.raises(KontoZablokowane):
        bank.wyplac(NUM_A, kwota)
    assert bank.konta[NUM_A].saldo == przed


@pytest.mark.parametrize("kwota", [0, Decimal("-0.01"), -1])
def test_wyplac_kwota_niedodatnia(bank, kwota):
    przed = bank.konta[NUM_A].saldo
    with pytest.raises(ValueError):
        bank.wyplac(NUM_A, kwota)
    assert bank.konta[NUM_A].saldo == przed


def test_wyplac_brak_srodkow(bank):
    """Kwota dodatnia, ponizej limitu dziennego, powyzej salda."""
    system = BankSystem()
    system.utworz_konto(NUM_A, "Anna", Decimal("100"))
    with pytest.raises(ValueError):
        system.wyplac(NUM_A, Decimal("100.01"))
    assert system.konta[NUM_A].saldo == Decimal("100")


def test_wyplac_kwota_minimalna(bank):
    assert bank.wyplac(NUM_A, Decimal("0.01")) == Decimal("9999.99")


def test_wyplac_rowna_saldu_ponizej_limitu():
    """Brzeg salda, ktory nie wpada jednoczesnie w limit dzienny."""
    system = BankSystem()
    system.utworz_konto(NUM_A, "Anna", Decimal("100"))
    assert system.wyplac(NUM_A, Decimal("100")) == Decimal("0")


def test_wyplac_sukces_i_wpis(bank):
    assert bank.wyplac(NUM_A, Decimal("100")) == Decimal("9900")
    assert bank.konta[NUM_A].historia[-1][1:] == ("wyplata", Decimal("100"))


@pytest.mark.parametrize(
    ("kwota", "oczekiwane"),
    [
        (Decimal("4999.99"), Decimal("5000.01")),
        (LIMIT_DZIENNY, Decimal("5000")),
    ],
)
def test_wyplac_brzeg_pojedynczej_kwoty_w_limicie(bank, kwota, oczekiwane):
    assert bank.wyplac(NUM_A, kwota) == oczekiwane


def test_wyplac_pojedyncza_kwota_ponad_limit(bank):
    przed = bank.konta[NUM_A].saldo
    with pytest.raises(ValueError):
        bank.wyplac(NUM_A, LIMIT_DZIENNY + Decimal("0.01"))
    assert bank.konta[NUM_A].saldo == przed


def test_wyplac_suma_dzienna_rowna_limitowi(bank):
    """Brzeg specyfikacji: suma wyplat == 5000 nadal jest w limicie („przekracza")."""
    assert bank.wyplac(NUM_A, Decimal("3000")) == Decimal("7000")
    assert bank.wyplac(NUM_A, Decimal("2000")) == Decimal("5000")


def test_wyplac_suma_z_przelewem_rowna_limitowi(bank):
    assert bank.przelew(NUM_A, NUM_B, Decimal("4000")) == Decimal("6000")
    assert bank.wyplac(NUM_A, Decimal("1000")) == Decimal("5000")


@ROZBIEZNOSC_LIMIT_DZIENNY
def test_wyplac_druga_wyplata_przekracza_limit_laczny(bank):
    bank.wyplac(NUM_A, Decimal("3000"))
    with pytest.raises(ValueError):
        bank.wyplac(NUM_A, Decimal("2000.01"))
    assert bank.konta[NUM_A].saldo == Decimal("7000")


@ROZBIEZNOSC_LIMIT_DZIENNY
def test_wyplac_po_przelewie_przekracza_limit_laczny(bank):
    bank.przelew(NUM_A, NUM_B, Decimal("4000"))
    with pytest.raises(ValueError):
        bank.wyplac(NUM_A, Decimal("1000.01"))
    assert bank.konta[NUM_A].saldo == Decimal("6000")
    assert bank.konta[NUM_B].saldo == Decimal("4000")


def test_wyplac_kwota_float(bank):
    assert bank.wyplac(NUM_A, 10.5) == Decimal("9989.5")


@ROZBIEZNOSC_TYP_KWOTY
def test_wyplac_napis_liczbowy(bank):
    with pytest.raises(TypeError):
        bank.wyplac(NUM_A, "100")


@ROZBIEZNOSC_TYP_KWOTY
@pytest.mark.parametrize("kwota", ["abc", None])
def test_wyplac_kwota_nieliczbowa(bank, kwota):
    przed = bank.konta[NUM_A].saldo
    with pytest.raises(TypeError):
        bank.wyplac(NUM_A, kwota)
    assert bank.konta[NUM_A].saldo == przed


# --- przelew: tablica decyzyjna i wartosci brzegowe ---


def test_przelew_brak_konta_zrodlowego(bank):
    with pytest.raises(KontoNieIstnieje):
        bank.przelew(NUM_BRAK, NUM_B, Decimal("-1"))
    assert bank.konta[NUM_B].saldo == Decimal("0")


def test_przelew_brak_konta_docelowego(bank):
    przed = bank.konta[NUM_A].saldo
    with pytest.raises(KontoNieIstnieje):
        bank.przelew(NUM_A, NUM_BRAK, Decimal("10"))
    assert bank.konta[NUM_A].saldo == przed


def test_przelew_zrodlo_zablokowane_ma_pierwszenstwo(bank):
    """Blokada wygrywa z brakiem srodkow i z limitem 1 000 000."""
    bank.wplac(NUM_A, Decimal("2000000"))
    bank.zablokuj_konto(NUM_A)
    przed = bank.konta[NUM_A].saldo
    with pytest.raises(KontoZablokowane):
        bank.przelew(NUM_A, NUM_B, LIMIT_PRZELEWU + Decimal("1"))
    assert bank.konta[NUM_A].saldo == przed
    assert bank.konta[NUM_B].saldo == Decimal("0")


@pytest.mark.parametrize("kwota", [0, Decimal("-0.01")])
def test_przelew_kwota_niedodatnia(bank, kwota):
    przed_a = bank.konta[NUM_A].saldo
    with pytest.raises(ValueError):
        bank.przelew(NUM_A, NUM_B, kwota)
    assert bank.konta[NUM_A].saldo == przed_a
    assert bank.konta[NUM_B].saldo == Decimal("0")


def test_przelew_brak_srodkow(bank):
    """Kwota powyzej salda i powyzej limitu: oba warunki to ValueError, stan bez zmian."""
    przed_a = bank.konta[NUM_A].saldo
    with pytest.raises(ValueError):
        bank.przelew(NUM_A, NUM_B, LIMIT_PRZELEWU + Decimal("1"))
    assert bank.konta[NUM_A].saldo == przed_a
    assert bank.konta[NUM_B].saldo == Decimal("0")


def test_przelew_sukces(bank):
    assert bank.przelew(NUM_A, NUM_B, Decimal("100")) == Decimal("9900")
    assert bank.konta[NUM_B].saldo == Decimal("100")
    assert bank.konta[NUM_A].historia[-1][1:] == ("przelew_wychodzacy", Decimal("100"))
    assert bank.konta[NUM_B].historia[-1][1:] == ("przelew_przychodzacy", Decimal("100"))


def test_przelew_kwota_minimalna(bank):
    assert bank.przelew(NUM_A, NUM_B, Decimal("0.01")) == Decimal("9999.99")
    assert bank.konta[NUM_B].saldo == Decimal("0.01")


def test_przelew_cale_saldo(bank):
    assert bank.przelew(NUM_A, NUM_B, Decimal("10000")) == Decimal("0")
    assert bank.konta[NUM_B].saldo == Decimal("10000")


def test_przelew_na_konto_zablokowane(bank):
    """Specyfikacja odrzuca tylko zablokowane konto zrodlowe."""
    bank.zablokuj_konto(NUM_B)
    assert bank.przelew(NUM_A, NUM_B, Decimal("25")) == Decimal("9975")
    assert bank.konta[NUM_B].saldo == Decimal("25")
    assert bank.konta[NUM_B].status == "zablokowane"


def test_przelew_na_to_samo_konto(bank):
    """Specyfikacja nie definiuje przelewu na wlasne konto. Saldo netto zostaje."""
    assert bank.przelew(NUM_A, NUM_A, Decimal("10")) == Decimal("10000")
    assert bank.konta[NUM_A].saldo == Decimal("10000")
    typy = [wpis[1] for wpis in bank.konta[NUM_A].historia[-2:]]
    assert typy == ["przelew_wychodzacy", "przelew_przychodzacy"]


def _uzupelnij_ponad_limit(bank):
    bank.wplac(NUM_A, Decimal("2000000"))


def test_przelew_tuz_ponizej_limitu(bank):
    _uzupelnij_ponad_limit(bank)
    assert bank.przelew(NUM_A, NUM_B, Decimal("999999.99")) == Decimal("1010000.01")
    assert bank.konta[NUM_B].saldo == Decimal("999999.99")


def test_przelew_dokladnie_limit(bank):
    _uzupelnij_ponad_limit(bank)
    assert bank.przelew(NUM_A, NUM_B, LIMIT_PRZELEWU) == Decimal("1010000")
    assert bank.konta[NUM_B].saldo == LIMIT_PRZELEWU


def test_przelew_ponad_limit_wyjatek(bank):
    _uzupelnij_ponad_limit(bank)
    with pytest.raises(ValueError):
        bank.przelew(NUM_A, NUM_B, LIMIT_PRZELEWU + Decimal("0.01"))


@ROZBIEZNOSC_ATOMOWOSC
def test_przelew_ponad_limit_nie_zmienia_stanu(bank):
    _uzupelnij_ponad_limit(bank)
    przed_a = bank.konta[NUM_A].saldo
    przed_b = bank.konta[NUM_B].saldo
    historia_a = len(bank.konta[NUM_A].historia)
    historia_b = len(bank.konta[NUM_B].historia)
    with pytest.raises(ValueError):
        bank.przelew(NUM_A, NUM_B, LIMIT_PRZELEWU + Decimal("0.01"))
    assert bank.konta[NUM_A].saldo == przed_a
    assert bank.konta[NUM_B].saldo == przed_b
    assert len(bank.konta[NUM_A].historia) == historia_a
    assert len(bank.konta[NUM_B].historia) == historia_b


@ROZBIEZNOSC_TYP_KWOTY
def test_przelew_napis_liczbowy(bank):
    with pytest.raises(TypeError):
        bank.przelew(NUM_A, NUM_B, "50")


@ROZBIEZNOSC_TYP_KWOTY
def test_przelew_kwota_nieliczbowa(bank):
    przed_a = bank.konta[NUM_A].saldo
    with pytest.raises(TypeError):
        bank.przelew(NUM_A, NUM_B, "abc")
    assert bank.konta[NUM_A].saldo == przed_a
    assert bank.konta[NUM_B].saldo == Decimal("0")
