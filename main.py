from decimal import Decimal
from datetime import date, timedelta

from API import (
    BankSystem,
    KontoNieIstnieje,
    KontoZablokowane,
    ProcesorNiedostepny,
    ZewnetrznyProcesor,
)


def main():
    bs = BankSystem()

    # Numery 10-cyfrowe: ostatnia cyfra = suma pierwszych 9 % 10
    n1 = "1234567895"  # 1+2+...+9=45 → 5
    n2 = "1111111119"  # 9*1=9 → 9

    print("=== 1. Utworzenie kont ===")
    k1 = bs.utworz_konto(n1, "Anna Kowalska", 1000)
    k2 = bs.utworz_konto(n2, "Jan Nowak", 500)
    print(f"  Konto {n1}: saldo={k1.saldo}, wlasciciel={k1.wlasciciel}")
    print(f"  Konto {n2}: saldo={k2.saldo}, wlasciciel={k2.wlasciciel}")

    print("\n=== 2. Wplata ===")
    saldo = bs.wplac(n1, 250.50)
    print(f"  Po wplacie 250.50 na {n1}: saldo={saldo}")

    print("\n=== 3. Wyplata ===")
    saldo = bs.wyplac(n1, 100)
    print(f"  Po wyplacie 100 z {n1}: saldo={saldo}")

    print("\n=== 4. Przelew wewnetrzny ===")
    saldo = bs.przelew(n1, n2, 200)
    print(f"  Po przelewie 200 z {n1}→{n2}: saldo zrodla={saldo}, saldo celu={bs.konta[n2].saldo}")

    print("\n=== 5. Odsetki (5% rocznie, 3 miesiace) ===")
    saldo = bs.nalicz_odsetki(n2, 5, 3)
    print(f"  Saldo {n2} po odsetkach: {saldo}")

    print("\n=== 6. Wyciag miesieczny ===")
    dzisiaj = date.today()
    wyciag = bs.wyciag_miesieczny(n1, dzisiaj.year, dzisiaj.month)
    print(f"  Wyciag {n1}: {wyciag}")

    print("\n=== 7. Blad: zly numer konta ===")
    try:
        bs.utworz_konto("123", "X", 0)
    except ValueError as e:
        print(f"  OK, ValueError: {e}")

    print("\n=== 8. Blad: konto nie istnieje ===")
    try:
        bs.wplac("9999999999", 10)
    except KontoNieIstnieje as e:
        print(f"  OK, KontoNieIstnieje: {e}")

    print("\n=== 9. Blad: zablokowane konto ===")
    bs.zablokuj_konto(n1)
    try:
        bs.wyplac(n1, 10)
    except KontoZablokowane as e:
        print(f"  OK, KontoZablokowane: {e}")
    bs.odblokuj_konto(n1)

    print("\n=== 10. Blad: za malo srodkow ===")
    try:
        bs.wyplac(n1, 999999)
    except ValueError as e:
        print(f"  OK, ValueError: {e}")

    print("\n=== 11. Historia w okresie (uwaga: granice wylaczone!) ===")
    hist = bs.historia_w_okresie(n1, dzisiaj - timedelta(days=1), dzisiaj + timedelta(days=1))
    print(f"  Wpisy w (wczoraj, jutro): {len(hist)} szt.")
    hist_strict = bs.historia_w_okresie(n1, dzisiaj, dzisiaj)
    print(f"  Wpisy w (dzis, dzis) — oczekiwane 0 bo od < data < do: {len(hist_strict)} szt.")

    print("\n=== 12. Przelew zewnetrzny (procesor bez awarii) ===")
    proc = ZewnetrznyProcesor(prawdopodobienstwo_awarii=0.0)
    wynik = bs.przelew_zewnetrzny(n2, "0000000000", 50, procesor=proc)
    print(f"  Wynik: {wynik}, saldo {n2}={bs.konta[n2].saldo}")

    print("\n=== 13. Przelew zewnetrzny (procesor zawsze pada) ===")
    proc_zly = ZewnetrznyProcesor(prawdopodobienstwo_awarii=1.0)
    saldo_przed = bs.konta[n2].saldo
    try:
        bs.przelew_zewnetrzny(n2, "0000000000", 10, procesor=proc_zly)
    except ProcesorNiedostepny as e:
        print(f"  OK, ProcesorNiedostepny: {e}")
        print(f"  Saldo niezmienione? {bs.konta[n2].saldo == saldo_przed} (saldo={bs.konta[n2].saldo})")

    print("\n=== 14. Bug: komunikat 'konto juz istnieje' ===")
    try:
        bs.utworz_konto(n1, "Duplikat", 0)
    except ValueError as e:
        print(f"  ValueError: {e}")
        print("  ↑ widac {{numer}} zamiast prawdziwego numeru — blad w f-stringu")

    print("\n=== Gotowe ===")


if __name__ == "__main__":
    main()
