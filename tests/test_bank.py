from decimal import Decimal
import pytest
from API import BankSystem, KontoZablokowane, KontoNieIstnieje

NUM_A = "1234567895"
NUM_B = "0000000000"  # też przechodzi _numer_poprawny

@pytest.fixture
def bank():
    b = BankSystem()
    b.utworz_konto(NUM_A, "A", 10_000)
    b.utworz_konto(NUM_B, "B", 0)
    return b

def test_wplac_sukces(bank):
    assert bank.wplac(NUM_A, 100) == Decimal("10100")

def test_wplac_kwota_niedodatnia(bank):
    with pytest.raises(ValueError, match="dodatnia"):
        bank.wplac(NUM_A, 0)

def test_wyplac_konto_zablokowane(bank):
    bank.zablokuj_konto(NUM_A)
    with pytest.raises(KontoZablokowane):
        bank.wyplac(NUM_A, 100)

def test_wyplac_niewystarczajace_srodki(bank):
    with pytest.raises(ValueError, match="Niewystarczajace"):
        bank.wyplac(NUM_A, 20_000)

def test_wyplac_limit(bank):
    with pytest.raises(ValueError, match="limit"):
        bank.wyplac(NUM_A, 5001)  # saldo >= 5001 wymagane

def test_przelew_sukces(bank):
    saldo = bank.przelew(NUM_A, NUM_B, 50)
    assert saldo == Decimal("9950")
    assert bank.konta[NUM_B].saldo == Decimal("50")