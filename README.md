# NSI — System zarządzania kontem bankowym (wariant E)

System emulujący konto bankowe z naciskiem na **mechanizmy odporności**
(retry, circuit breaker, redundancja) w kontekście ćwiczeń P5. Kod jest
celowo „kruchy" w punkcie integracji z zewnętrznym procesorem płatności.

## Wymagania

- **Python ≥ 3.12** (w projekcie ustawiony `3.12` przez plik `.python-version`)
- **[uv](https://docs.astral.sh/uv/)** — menedżer środowiska i pakietów

Zainstaluj `uv`, jeśli go nie masz:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# lub przez pipx / pip:  pip install uv
```

## Uruchomienie

Najszybszy sposób — dwie komendy:

```bash
uv sync          # zbuduj środowisko wirtualne i zainstaluj zależności
uv run main.py   # uruchom program (wyświetli stan systemu + „Hello from nsi!")
```

Nie musisz ręcznie aktywować `.venv` — `uv run` obsługuje to automatycznie.

## Testy

Projekt zakłada pytest (`pytest`, `pytest-cov`).

```bash
uv sync
uv run pytest
```

## Testy mutacyjne (lab 3, pytest-gremlins)

Wymaga grupy dev (`pytest-gremlins` jest w `pyproject.toml`):

```bash
uv sync
uv run pytest --gremlins --gremlin-targets=API.py tests/test_bank.py -o addopts=
```

Raport HTML (folder `gremlins-report/`):

```bash
uv run pytest --gremlins --gremlin-targets=API.py tests/test_bank.py -o addopts= \
  --gremlin-report=html --gremlins-html-dir=gremlins-report
```

Opcja `-o addopts=` wyłącza domyślne `--cov` z `pyproject.toml`, żeby mutacje nie mieszały się z coverage.

## Docker

Obraz uruchamia ten sam cykl jak lokalnie:

```bash
docker build -t nsi .
docker run --rm nsi
```

## Zależności (`pyproject.toml`)

```toml
dependencies = [
    "pytest>=9.1.1",
    "pytest-cov>=7.1.0",
]
```

