# maxed-cli

A small, firm-agnostic command-line tool that gives developers and operators a
fast on-ramp to an accounting-tech stack. It scaffolds a local dev workspace,
validates configuration, lints workpaper specs against a published JSON Schema,
and runs a fully local sandbox connector smoke-test.

It is pure tooling and glue: no product logic, no network calls, no real client
data. Everything it touches is local files and synthetic fixtures.

## Why

Standing up a developer workspace for an accounting application usually means a
pile of bespoke setup steps and undocumented config shapes. `maxed-cli` makes
those steps boring and repeatable:

- A single **config schema** describes a workspace, so config mistakes are
  caught early with clear messages instead of at runtime.
- A **workpaper-spec schema** lets teams describe the structure of a workpaper
  (sections and line items) as data, and lint it in CI.
- A **sandbox smoke-test** exercises the connector wiring end-to-end using
  in-process mocks, so you can validate plumbing without any credentials.

## Install

Requires Python 3.9+.

```bash
# From a clone of this repository
pip install .

# For development (editable + test deps)
pip install -e ".[dev]"
```

This installs the `maxed` command.

```bash
maxed --help
maxed --version
```

## Usage

### 1. Validate a workspace config

```bash
maxed validate-config examples/workspace.yaml
```

A config is a small YAML or JSON file (see
[`examples/workspace.yaml`](examples/workspace.yaml)). The full shape is defined
by [`config.schema.json`](src/maxed_cli/schemas/config.schema.json). Validation
errors point at the exact field and reason; exit code is `0` on success, `1` on
a schema error, `2` if the file is missing or unparseable.

### 2. Scaffold a workspace

```bash
maxed init examples/workspace.yaml
```

This creates the workspace root and its sub-folders, drops a self-describing
copy of the config under `configs/`, and seeds a synthetic example workpaper you
can lint immediately. Re-running is safe (idempotent) — existing paths are
reported as `exists` rather than recreated.

### 3. Lint a workpaper spec

```bash
maxed lint-workpaper examples/example.workpaper.json
```

Linting runs schema validation plus semantic checks the schema cannot express
(unique section keys, unique line-item refs). Use `--strict` to treat warnings
(such as an empty section) as failures. The schema lives at
[`workpaper.schema.json`](src/maxed_cli/schemas/workpaper.schema.json).

### 4. Run a sandbox connector smoke-test

```bash
maxed smoke examples/workspace.yaml
maxed smoke examples/workspace.yaml --json
```

For each connector declared in the config, `maxed` builds a sandbox/mock driver
and runs a self-contained smoke-test. The built-in drivers are:

| kind             | what it simulates                                  |
| ---------------- | -------------------------------------------------- |
| `mock-ledger`    | a read-only ledger with a synthetic chart of accounts |
| `mock-storage`   | a document store with synthetic file metadata      |
| `mock-tax-forms` | a catalog of clearly-fake tax-form templates       |
| `echo`           | echoes its options back (a connectivity ping)      |

These drivers never open a network socket and only return deterministic
synthetic fixtures. The command exits non-zero if any connector fails.

## Example end-to-end

```bash
pip install -e ".[dev]"
maxed init examples/workspace.yaml
maxed lint-workpaper example-workspace/workpapers/example.workpaper.json
maxed smoke examples/workspace.yaml --json
```

## Project layout

```
src/maxed_cli/
  cli.py            # Typer entrypoint (maxed ...)
  config.py         # config load + schema validation
  workpaper.py      # workpaper-spec linting
  scaffold.py       # workspace scaffolder
  connectors/       # sandbox/mock connector harness
  schemas/          # bundled JSON Schemas (config + workpaper)
examples/           # example config + workpaper spec
tests/              # pytest suite
```

## Development

```bash
pip install -e ".[dev]"
pytest
```

## Scope and non-goals

`maxed-cli` is intentionally narrow. It does not implement bookkeeping, tax, or
any accounting business logic; it does not connect to real systems; and it does
not handle real client data. It is a developer convenience layer around
configuration, scaffolding, and local sandbox checks.

## License

Apache-2.0. See [LICENSE](LICENSE).
