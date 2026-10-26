from datetime import date, timedelta
from decimal import Decimal

import pytest

from API import (
    BankSystem,
    KontoNieIstnieje,
    KontoZablokowane,
    LIMIT_DZIENNY_WYPLAT,
    ProcesorNiedostepny,
    ZewnetrznyProcesor,
)

NUM_A = "1234567895"
NUM_B = "0000000000"
NUM_BRAK = "9999999991"


@pytest.fixture
def bank():
    b = BankSystem()
    b.utworz_konto(NUM_A, "A", 10_000)
    b.utworz_konto(NUM_B, "B", 0)
    return b



def test_wplac_sukces(bank):
    assert bank.wplac(NUM_A, 100) == Decimal("10100")
    assert bank.konta[NUM_A].historia[-1][1] == "wplata"


def test_wplac_kwota_niedodatnia(bank):
    with pytest.raises(ValueError, match="dodatnia"):
        bank.wplac(NUM_A, 0)
    with pytest.raises(ValueError, match="dodatnia"):
        bank.wplac(NUM_A, -10)


def test_wplac_zly_typ_kwoty(bank):
    with pytest.raises(TypeError, match="liczba"):
        bank.wplac(NUM_A, "100")


def test_wplac_konto_nie_istnieje(bank):
    with pytest.raises(KontoNieIstnieje):
        bank.wplac(NUM_BRAK, 50)


def test_wyplac_sukces(bank):
    assert bank.wyplac(NUM_A, 250) == Decimal("9750")
    assert bank.konta[NUM_A].historia[-1][1] == "wyplata"


def test_wyplac_konto_zablokowane(bank):
    bank.zablokuj_konto(NUM_A)
    with pytest.raises(KontoZablokowane):
        bank.wyplac(NUM_A, 100)


def test_wyplac_kwota_niedodatnia(bank):
    with pytest.raises(ValueError, match="dodatnia"):
        bank.wyplac(NUM_A, 0)
    with pytest.raises(ValueError, match="dodatnia"):
        bank.wyplac(NUM_A, -1)


def test_wyplac_niewystarczajace_srodki(bank):
    with pytest.raises(ValueError, match="Niewystarczajace"):
        bank.wyplac(NUM_A, 20_000)


def test_wyplac_limit(bank):
    with pytest.raises(ValueError, match="limit"):
        bank.wyplac(NUM_A, LIMIT_DZIENNY_WYPLAT + 1)


def test_wyplac_konto_nie_istnieje(bank):
    with pytest.raises(KontoNieIstnieje):
        bank.wyplac(NUM_BRAK, 10)



def test_przelew_sukces(bank):
    saldo = bank.przelew(NUM_A, NUM_B, 50)
    assert saldo == Decimal("9950")
    assert bank.konta[NUM_B].saldo == Decimal("50")


def test_przelew_konto_zablokowane(bank):
    bank.zablokuj_konto(NUM_A)
    with pytest.raises(KontoZablokowane):
        bank.przelew(NUM_A, NUM_B, 10)


def test_przelew_kwota_niedodatnia(bank):
    with pytest.raises(ValueError, match="dodatnia"):
        bank.przelew(NUM_A, NUM_B, 0)


def test_przelew_niewystarczajace_srodki(bank):
    with pytest.raises(ValueError, match="Niewystarczajace"):
        bank.przelew(NUM_A, NUM_B, 50_000)


def test_przelew_limit_systemowy(bank):
    bank.wplac(NUM_A, 2_000_000)
    with pytest.raises(ValueError, match="limit systemowy"):
        bank.przelew(NUM_A, NUM_B, Decimal("1000001"))


def test_przelew_kwota_jedna(bank):
    saldo = bank.przelew(NUM_A, NUM_B, 1)
    assert saldo == Decimal("9999")
    assert bank.konta[NUM_B].saldo == Decimal("1")


def test_przelew_cale_saldo(bank):
    saldo = bank.przelew(NUM_A, NUM_B, 10_000)
    assert saldo == Decimal("0")
    assert bank.konta[NUM_B].saldo == Decimal("10000")


def test_przelew_dokladnie_limit_milion(bank):
    bank.wplac(NUM_A, 2_000_000)
    saldo = bank.przelew(NUM_A, NUM_B, Decimal("1000000"))
    assert saldo == Decimal("1010000")
    assert bank.konta[NUM_B].saldo == Decimal("1000000")


def test_przelew_konto_zrodlowe_nie_istnieje(bank):
    with pytest.raises(KontoNieIstnieje):
        bank.przelew(NUM_BRAK, NUM_B, 10)


def test_przelew_konto_docelowe_nie_istnieje(bank):
    with pytest.raises(KontoNieIstnieje):
        bank.przelew(NUM_A, NUM_BRAK, 10)



def test_utworz_konto_nieprawidlowy_numer(bank):
    with pytest.raises(ValueError, match="Nieprawidlowy"):
        bank.utworz_konto("123", "X")
    with pytest.raises(ValueError, match="Nieprawidlowy"):
        bank.utworz_konto("abcdefghij", "X")


def test_utworz_konto_duplikat(bank):
    with pytest.raises(ValueError, match="istnieje"):
        bank.utworz_konto(NUM_A, "Inny")


def test_odblokuj_konto(bank):
    bank.zablokuj_konto(NUM_A)
    bank.odblokuj_konto(NUM_A)
    assert bank.konta[NUM_A].status == "aktywne"
    assert bank.wyplac(NUM_A, 10) == Decimal("9990")


def test_suma_dzisiejszych_wyplat(bank):
    bank.wyplac(NUM_A, 100)
    bank.przelew(NUM_A, NUM_B, 50)
    konto = bank.konta[NUM_A]
    konto.dodaj_wpis("wyplata", Decimal("10"), date.today() - timedelta(days=1))
    assert bank._suma_dzisiejszych_wyplat(konto) == Decimal("150")


def test_nalicz_odsetki(bank):
    saldo = bank.nalicz_odsetki(NUM_A, 12, 1)
    assert saldo == Decimal("10100")
    assert bank.konta[NUM_A].historia[-1] == (date.today(), "odsetki", Decimal("100.00"))


def test_historia_w_okresie(bank):
    bank.wplac(NUM_A, 10)
    dzis = date.today()
    assert len(bank.historia_w_okresie(NUM_A, dzis, dzis)) >= 1
    assert bank.historia_w_okresie(NUM_A, dzis - timedelta(days=30), dzis - timedelta(days=20)) == []


def test_wyciag_miesieczny(bank):
    bank.wplac(NUM_A, 100)
    bank.wyplac(NUM_A, 40)
    bank.przelew(NUM_A, NUM_B, 10)
    dzis = date.today()
    # wpis z innego miesiąca → gałąź fałsz w warunku roku/miesiąca (180->179)
    bank.konta[NUM_A].dodaj_wpis("wplata", Decimal("5"), date(dzis.year, dzis.month, 1) - timedelta(days=40))
    # typ poza wplata/wyplata → gałąź fałsz elif (183->179)
    bank.konta[NUM_A].dodaj_wpis("przelew_zewnetrzny", Decimal("1"), dzis)
    wyciag = bank.wyciag_miesieczny(NUM_A, dzis.year, dzis.month)
    assert wyciag["wplaty"] == Decimal("100")
    assert wyciag["wyplaty"] == Decimal("50")
    assert wyciag["saldo_koncowe"] == bank.konta[NUM_A].saldo


def test_api_main_block(capsys):
    """Pokrycie bloku if __name__ == '__main__' (211-216)."""
    import runpy

    runpy.run_module("API", run_name="__main__")
    out = capsys.readouterr().out
    assert "Utworzono konto" in out
    assert "Historia" in out


def test_przelew_zewnetrzny_sukces(bank):
    class StubProcesor:
        def wyslij_przelew(self, numer, kwota):
            return {"status": "zaksiegowano", "numer_referencyjny": "REF000001"}

    wynik = bank.przelew_zewnetrzny(NUM_A, "PL123", 100, procesor=StubProcesor())
    assert wynik["status"] == "zaksiegowano"
    assert bank.konta[NUM_A].saldo == Decimal("9900")


def test_przelew_zewnetrzny_zablokowane(bank):
    bank.zablokuj_konto(NUM_A)
    with pytest.raises(KontoZablokowane):
        bank.przelew_zewnetrzny(NUM_A, "PL123", 10, procesor=ZewnetrznyProcesor(0))


def test_przelew_zewnetrzny_kwota_niedodatnia(bank):
    with pytest.raises(ValueError, match="dodatnia"):
        bank.przelew_zewnetrzny(NUM_A, "PL123", 0, procesor=ZewnetrznyProcesor(0))


def test_przelew_zewnetrzny_brak_srodkow(bank):
    with pytest.raises(ValueError, match="Niewystarczajace"):
        bank.przelew_zewnetrzny(NUM_A, "PL123", 50_000, procesor=ZewnetrznyProcesor(0))


def test_przelew_zewnetrzny_kwota_jedna(bank):
    class StubProcesor:
        def wyslij_przelew(self, numer, kwota):
            return {"status": "zaksiegowano", "numer_referencyjny": "REF1"}

    wynik = bank.przelew_zewnetrzny(NUM_A, "PL123", 1, procesor=StubProcesor())
    assert wynik["status"] == "zaksiegowano"
    assert bank.konta[NUM_A].saldo == Decimal("9999")


def test_przelew_zewnetrzny_cale_saldo(bank):
    class StubProcesor:
        def wyslij_przelew(self, numer, kwota):
            return {"status": "zaksiegowano", "numer_referencyjny": "REFALL"}

    wynik = bank.przelew_zewnetrzny(NUM_A, "PL123", 10_000, procesor=StubProcesor())
    assert wynik["numer_referencyjny"] == "REFALL"
    assert bank.konta[NUM_A].saldo == Decimal("0")


def test_przelew_zewnetrzny_bez_procesora(bank, monkeypatch):
    class StubProcesor:
        def wyslij_przelew(self, numer, kwota):
            return {"status": "zaksiegowano", "numer_referencyjny": "REF-DEF"}

    monkeypatch.setattr("API.ZewnetrznyProcesor", lambda *args, **kwargs: StubProcesor())
    wynik = bank.przelew_zewnetrzny(NUM_A, "PL999", 30)
    assert wynik["status"] == "zaksiegowano"
    assert bank.konta[NUM_A].saldo == Decimal("9970")


def test_zewnetrzny_procesor_sukces_i_awaria():
    ok = ZewnetrznyProcesor(prawdopodobienstwo_awarii=0.0, opoznienie_s=0.001)
    assert ok.wyslij_przelew("X", 1)["status"] == "zaksiegowano"

    class GenFail:
        def random(self):
            return 0.0

    fail = ZewnetrznyProcesor(prawdopodobienstwo_awarii=1.0, generator=GenFail())
    with pytest.raises(ProcesorNiedostepny):
        fail.wyslij_przelew("X", 1)

    class GenOnThreshold:
        def random(self):
            return 0.3

    edge = ZewnetrznyProcesor(prawdopodobienstwo_awarii=0.3, generator=GenOnThreshold())
    assert edge.wyslij_przelew("X", 1)["status"] == "zaksiegowano"
