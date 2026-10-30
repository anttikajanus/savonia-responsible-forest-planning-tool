"""Probe the parser dependencies used by repository tooling, without QGIS."""

import importlib
import importlib.util
from pathlib import Path
import sys


REQUIREMENTS = Path(__file__).resolve().parents[1] / "requirements-dev.txt"


def describe_source(name):
    """Expose unreadable initializers hidden by namespace-package resolution."""
    try:
        spec = importlib.util.find_spec(name)
        if spec is None:
            print(f"{name}: module not found on this interpreter's import path")
            return
        paths = ([Path(spec.origin)] if spec.has_location else
                 [Path(folder) / "__init__.py" for folder in spec.submodule_search_locations or ()])
        for path in paths:
            print(f"{name} source: {path}")
            try:
                with path.open("rb") as source:
                    source.read(1)
            except OSError as error:
                print(f"{name} source access: {type(error).__name__}: {error}")
    except (ImportError, OSError, ValueError) as error:
        print(f"{name} source resolution: {type(error).__name__}: {error}")


def main():
    print(f"Tooling Python: {sys.executable}; version: {sys.version.split()[0]}")
    errors = []
    for name, symbol in (("markdown_it", "MarkdownIt"), ("yaml", "safe_load")):
        try:
            module = importlib.import_module(name)
            print(f"{name}: path: {getattr(module, '__file__', None) or 'unknown location'}")
            parser = getattr(module, symbol, None)
            if not callable(parser):
                raise ImportError(f"{name}.{symbol} is missing or not callable")
            if name == "markdown_it":
                if parser().render("# preflight").strip() != "<h1>preflight</h1>":
                    raise ValueError("MarkdownIt did not render the expected heading")
            elif parser("preflight: true") != {"preflight": True}:
                raise ValueError("safe_load did not parse the expected YAML mapping")
        except Exception as error:  # Broken packages also need actionable diagnostics.
            errors.append(name)
            print(f"{name}: {type(error).__name__}: {error}")
            describe_source(name)
    if errors:
        print("Tooling dependency preflight failed: " + ", ".join(errors))
        python = sys.executable.replace("'", "''")
        requirements = str(REQUIREMENTS).replace("'", "''")
        print(f"Install with the selected interpreter (PowerShell): & '{python}' -m pip install -r '{requirements}'")
        print("For existing package directories, check initializer file permissions under the account running this check.")
        print("See docs/architecture/development.md#local-check-runner; rerun after repairing the environment.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
