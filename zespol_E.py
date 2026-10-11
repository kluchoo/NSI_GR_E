"""
System zarzadzania kontem bankowym
Wariant: Zespol E
"""

from decimal import Decimal, ROUND_HALF_UP
from datetime import date
import threading
import time
import random

LIMIT_DZIENNY_WYPLAT = Decimal("5000")


class KontoNieIstnieje(Exception):
    """Wyjatek zglaszany, gdy operacja dotyczy nieistniejacego numeru konta."""
    pass


class ProcesorNiedostepny(Exception):
    """Wyjatek symulujacy niedostepnosc zewnetrznego procesora platnosci."""
    pass


class ZewnetrznyProcesor:
    """
    Symulacja zewnetrznego systemu rozliczeniowego (np. izby rozliczeniowej
    miedzybankowej), przez ktory ida przelewy wychodzace poza system.

    Zawodzi losowo z zadanym prawdopodobienstwem -- celowo, do cwiczen
    z mechanizmami odpornosci (retry, circuit breaker, redundancja) w P5.
    To NIE jest wstrzynieta usterka do znalezienia -- to jest swiadomie
    "kruchy" punkt integracji, ktory zespoly maja wzmocnic.
    """

    def __init__(self, prawdopodobienstwo_awarii=0.3, opoznienie_s=0.0, generator=None):
        self.prawdopodobienstwo_awarii = prawdopodobienstwo_awarii
        self.opoznienie_s = opoznienie_s
        self._generator = generator or random.Random()
        self.licznik_wywolan = 0

    def wyslij_przelew(self, numer_konta_docelowego, kwota):
        self.licznik_wywolan += 1
        if self.opoznienie_s:
            time.sleep(self.opoznienie_s)
        if self._generator.random() < self.prawdopodobienstwo_awarii:
            raise ProcesorNiedostepny("Zewnetrzny procesor platnosci nie odpowiada")
        return {"status": "zaksiegowano", "numer_referencyjny": f"REF{self.licznik_wywolan:06d}"}


class KontoZablokowane(Exception):
    """Wyjatek zglaszany przy probie operacji na zablokowanym koncie."""
    pass


class Konto:
    def __init__(self, numer, wlasciciel, saldo_poczatkowe=0):
        self.numer = numer
        self.wlasciciel = wlasciciel
        self.saldo = Decimal(str(saldo_poczatkowe))
        self.historia = []
        self.status = "aktywne"

    def dodaj_wpis(self, typ, kwota, data_operacji=None):
        if data_operacji is None:
            data_operacji = date.today()
        self.historia.append((data_operacji, typ, kwota))


class BankSystem:
    def __init__(self):
        self.konta = {}
        self._lock = threading.Lock()

    @staticmethod
    def _numer_poprawny(numer):
        if not isinstance(numer, str) or len(numer) != 10 or not numer.isdigit():
            return False
        cyfry = [int(c) for c in numer]
        suma_kontrolna = sum(cyfry[:9]) % 10
        return cyfry[9] == suma_kontrolna

    def utworz_konto(self, numer, wlasciciel, saldo_poczatkowe=0):
        if not self._numer_poprawny(numer):
            raise ValueError("Nieprawidlowy numer konta")
        if numer in self.konta:
            raise ValueError(f"Konto {{numer}} juz istnieje")
        konto = Konto(numer, wlasciciel, saldo_poczatkowe)
        self.konta[numer] = konto
        return konto

    def _pobierz_konto(self, numer):
        if numer not in self.konta:
            raise KontoNieIstnieje(f"Konto {numer} nie istnieje")
        return self.konta[numer]

    def zablokuj_konto(self, numer):
        konto = self._pobierz_konto(numer)
        konto.status = "zablokowane"

    def odblokuj_konto(self, numer):
        konto = self._pobierz_konto(numer)
        konto.status = "aktywne"

    def _suma_dzisiejszych_wyplat(self, konto):
        dzis = date.today()
        suma = Decimal("0")
        for data_operacji, typ, kwota in konto.historia:
            if data_operacji == dzis and typ in ("wyplata", "przelew_wychodzacy"):
                suma += kwota
        return suma

    def wplac(self, numer, kwota):
        konto = self._pobierz_konto(numer)
        if not isinstance(kwota, (int, float, Decimal)):
            raise TypeError("Kwota musi byc liczba")
        kwota = Decimal(str(kwota))
        if kwota <= 0:
            raise ValueError("Kwota wplaty musi byc dodatnia")
        konto.saldo += kwota
        konto.dodaj_wpis("wplata", kwota)
        return konto.saldo

    def wyplac(self, numer, kwota):
        konto = self._pobierz_konto(numer)
        if konto.status == "zablokowane":
            raise KontoZablokowane(f"Konto {numer} jest zablokowane")
        kwota = Decimal(str(kwota))
        if kwota <= 0:
            raise ValueError("Kwota wyplaty musi byc dodatnia")
        if kwota > konto.saldo:
            raise ValueError("Niewystarczajace srodki na koncie")
        if kwota > LIMIT_DZIENNY_WYPLAT:
            raise ValueError("Przekroczono dzienny limit wyplat")
        konto.saldo -= kwota
        konto.dodaj_wpis("wyplata", kwota)
        return konto.saldo

    def przelew(self, numer_z, numer_do, kwota):
        with self._lock:
            konto_z = self._pobierz_konto(numer_z)
            konto_do = self._pobierz_konto(numer_do)
            if konto_z.status == "zablokowane":
                raise KontoZablokowane(f"Konto {{numer_z}} jest zablokowane")
            kwota = Decimal(str(kwota))
            if kwota <= 0:
                raise ValueError("Kwota przelewu musi byc dodatnia")
            if kwota > konto_z.saldo:
                raise ValueError("Niewystarczajace srodki na koncie zrodlowym")
            konto_z.saldo -= kwota
            konto_z.dodaj_wpis("przelew_wychodzacy", kwota)
            if kwota > Decimal("1000000"):
                raise ValueError("Przelew przekracza dzienny limit systemowy")
            konto_do.saldo += kwota
            konto_do.dodaj_wpis("przelew_przychodzacy", kwota)
        return konto_z.saldo

    def nalicz_odsetki(self, numer, roczna_stopa_procentowa, miesiace):
        konto = self._pobierz_konto(numer)
        stopa_miesieczna = Decimal(str(roczna_stopa_procentowa)) / Decimal("12") / Decimal("100")
        for _ in range(miesiace):
            odsetki = (konto.saldo * stopa_miesieczna).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            konto.saldo += odsetki
            konto.dodaj_wpis("odsetki", odsetki)
        return konto.saldo

    def historia_w_okresie(self, numer, od, do):
        konto = self._pobierz_konto(numer)
        wynik = []
        for data_operacji, typ, kwota in konto.historia:
            if od <= data_operacji <= do:
                wynik.append((data_operacji, typ, kwota))
        return wynik

    def wyciag_miesieczny(self, numer, rok, miesiac):
        konto = self._pobierz_konto(numer)
        wplaty = Decimal("0")
        wyplaty = Decimal("0")
        for data_operacji, typ, kwota in konto.historia:
            if data_operacji.year == rok and data_operacji.month == miesiac:
                if typ in ("wplata", "przelew_przychodzacy", "odsetki"):
                    wplaty += kwota
                elif typ in ("wyplata", "przelew_wychodzacy"):
                    wyplaty += kwota
        return {"wplaty": wplaty, "wyplaty": wyplaty, "saldo_koncowe": konto.saldo}

    def przelew_zewnetrzny(self, numer_z, numer_konta_docelowego_zewn, kwota, procesor=None):
        """
        Przelew na konto spoza systemu (np. do innego banku), realizowany
        przez zewnetrzny procesor platnosci. Implementacja jest celowo
        naiwna -- pojedyncza proba, bez ponawiania i bez zabezpieczen na
        wypadek niedostepnosci procesora. Wzmocnienie tej metody (retry,
        circuit breaker, redundancja) jest zadaniem na blok P5.
        """
        konto_z = self._pobierz_konto(numer_z)
        if konto_z.status == "zablokowane":
            raise KontoZablokowane(f"Konto {numer_z} jest zablokowane")
        kwota = Decimal(str(kwota))
        if kwota <= 0:
            raise ValueError("Kwota przelewu musi byc dodatnia")
        if kwota > konto_z.saldo:
            raise ValueError("Niewystarczajace srodki na koncie zrodlowym")
        proc = procesor or ZewnetrznyProcesor()
        wynik = proc.wyslij_przelew(numer_konta_docelowego_zewn, kwota)
        konto_z.saldo -= kwota
        konto_z.dodaj_wpis("przelew_zewnetrzny", kwota)
        return wynik


if __name__ == "__main__":
    bank = BankSystem()
    konto = bank.utworz_konto("1234567895", "Jan Kowalski", 1000)
    print("Utworzono konto:", konto.numer, konto.wlasciciel)
    print("Saldo po wplacie:", bank.wplac("1234567895", 200))
    print("Saldo po wyplacie:", bank.wyplac("1234567895", 100))
    print("Historia:", konto.historia)
