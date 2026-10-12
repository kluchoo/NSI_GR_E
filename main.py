import json
import time
from datetime import date, timedelta

from API import BankSystem, ZewnetrznyProcesor

LOG_FILE = "awarie.jsonl"
SUT_LOC = 215
session_start = time.time()


def log_failure(function_name, arguments, error):
    entry = {
        "time": time.time() - session_start,
        "function": function_name,
        "arguments": str(arguments),
        "error_type": type(error).__name__,
        "message": str(error),
    }
    file = open(LOG_FILE, "a", encoding="utf-8")
    file.write(json.dumps(entry, ensure_ascii=False) + "\n")
    file.close()


def call(description, function_name, function, *arguments):
    print("TEST:", description)
    try:
        result = function(*arguments)
        print("  OK ->", result)
        return result
    except Exception as error:
        log_failure(function_name, arguments, error)
        print("  FAILURE ->", type(error).__name__ + ":", error)
        return None


def exploratory_tests(bank):
    account_a = "1234567895"
    account_b = "9876543215"
    test_count = 0

    call("create account A", "utworz_konto", bank.utworz_konto, account_a, "Anna", 1000)
    test_count += 1

    call("create account B", "utworz_konto", bank.utworz_konto, account_b, "Jan", 500)
    test_count += 1

    call("deposit 200", "wplac", bank.wplac, account_a, 200)
    test_count += 1

    call("withdraw 50", "wyplac", bank.wyplac, account_a, 50)
    test_count += 1

    call("transfer 100", "przelew", bank.przelew, account_a, account_b, 100)
    test_count += 1

    call("empty account number", "utworz_konto", bank.utworz_konto, "", "X", 0)
    test_count += 1

    call("deposit None", "wplac", bank.wplac, account_a, None)
    test_count += 1

    call("deposit empty string", "wplac", bank.wplac, account_a, "")
    test_count += 1

    call("withdraw text 'abc'", "wyplac", bank.wyplac, account_a, "abc")
    test_count += 1

    call("negative deposit", "wplac", bank.wplac, account_a, -100)
    test_count += 1

    call("negative withdraw", "wyplac", bank.wyplac, account_a, -1)
    test_count += 1

    call("transfer amount 0", "przelew", bank.przelew, account_a, account_b, 0)
    test_count += 1

    call("interest negative months", "nalicz_odsetki", bank.nalicz_odsetki, account_a, 5, -3)
    test_count += 1

    call("very large deposit", "wplac", bank.wplac, account_a, 10**18)
    test_count += 1

    call("withdraw over daily limit", "wyplac", bank.wyplac, account_a, 6000)
    test_count += 1

    call("transfer over 1 million", "przelew", bank.przelew, account_a, account_b, 1000001)
    test_count += 1

    call("account number with !@#", "utworz_konto", bank.utworz_konto, "!@#$%^&*()", "Hacker", 0)
    test_count += 1

    call("account number DROP TABLE", "utworz_konto", bank.utworz_konto, "'; DROP--", "Eve", 0)
    test_count += 1

    call("nonexistent account", "wplac", bank.wplac, "0000000000", 10)
    test_count += 1

    call("block account B", "zablokuj_konto", bank.zablokuj_konto, account_b)
    test_count += 1

    call("withdraw from blocked account", "wyplac", bank.wyplac, account_b, 10)
    test_count += 1

    call("unblock account B", "odblokuj_konto", bank.odblokuj_konto, account_b)
    test_count += 1

    today = date.today()
    past = today - timedelta(days=30)
    call("history reversed period", "historia_w_okresie", bank.historia_w_okresie, account_a, today, past)
    test_count += 1

    call("statement month=0", "wyciag_miesieczny", bank.wyciag_miesieczny, account_a, 2026, 0)
    test_count += 1

    bad_processor = ZewnetrznyProcesor(prawdopodobienstwo_awarii=1.0)
    print("TEST: external transfer (processor always fails)")
    try:
        bank.przelew_zewnetrzny(account_a, "9999999999", 10, procesor=bad_processor)
        print("  OK")
    except Exception as error:
        log_failure("przelew_zewnetrzny", (account_a, "9999999999", 10), error)
        print("  FAILURE ->", type(error).__name__ + ":", error)
    test_count += 1

    call("duplicate account", "utworz_konto", bank.utworz_konto, account_a, "Someone", 0)
    test_count += 1

    return test_count


def load_failures():
    failures = []
    try:
        file = open(LOG_FILE, "r", encoding="utf-8")
    except FileNotFoundError:
        return failures

    for line in file:
        line = line.strip()
        if line != "":
            failures.append(json.loads(line))
    file.close()
    return failures


def calculate_mttf(failures):
    if len(failures) == 0:
        return None

    times = []
    for failure in failures:
        times.append(failure["time"])
    times.sort()

    gaps = []
    previous = 0
    for t in times:
        gaps.append(t - previous)
        previous = t

    return sum(gaps) / len(gaps)


def count_unique_defects(failures):
    unique = set()
    for failure in failures:
        cause = (failure["function"], failure["error_type"], failure["message"])
        unique.add(cause)
    return len(unique)


def show_results(test_count):
    failures = load_failures()
    failure_count = len(failures)
    defect_count = count_unique_defects(failures)
    mttf = calculate_mttf(failures)

    kloc = SUT_LOC / 1000
    density = defect_count / kloc

    print()
    print("========== METRICS ==========")
    print("Calls:              ", test_count)
    print("Failures:           ", failure_count)
    print("Unique defects:     ", defect_count)
    if mttf is None:
        print("MTTF:               no failures")
    else:
        print("MTTF:              ", round(mttf, 6), "s")
    print("SUT LOC:            ", SUT_LOC, "(", kloc, "KLOC)")
    print("Defect density:     ", round(density, 2), "defects / KLOC")
    print("=============================")

    print()
    print("Failure list:")
    number = 1
    for failure in failures:
        print(number, ".", failure["function"], "-", failure["error_type"] + ":", failure["message"])
        number += 1


def main():
    global session_start
    session_start = time.time()

    file = open(LOG_FILE, "w", encoding="utf-8")
    file.close()

    print("SUT: BankSystem (team E)")
    print("Failure log:", LOG_FILE)
    print()

    bank = BankSystem()
    count = exploratory_tests(bank)
    show_results(count)


if __name__ == "__main__":
    main()
