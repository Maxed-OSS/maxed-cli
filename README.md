# maxed-cli

The **front door** to a small, firm-agnostic suite of open-source
accounting-tech libraries. `maxed-cli` scaffolds a local dev project that is
pre-wired to use those libraries, validates configuration, lints workpaper and
[cpa-workpaper-spec](https://github.com/maxed-oss/cpa-workpaper-spec) documents,
and runs a fully local sandbox connector smoke-test.

It is pure tooling and glue: no product logic, no network calls, no real client
data. Everything it touches is local files and synthetic fixtures. **Every
command supports `--json`** for agent-friendly, machine-readable output.

## The suite

`maxed` is the on-ramp to these independent, separately-installable packages:

| Package                                                                       | What it does                                                                 |
| ----------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| [`accounting-adapters`](https://github.com/maxed-oss/accounting-adapters)     | One normalized read interface over public accounting APIs (QBO, Xero, Bill.com, TaxDome, Plaid). |
| [`statement-normalizer`](https://github.com/maxed-oss/statement-normalizer)   | Deterministic bank/credit-card statement parsing into normalized transaction JSON (CSV/OFX/text). |
| [`cpa-workpaper-spec`](https://github.com/maxed-oss/cpa-workpaper-spec)       | An open, versioned JSON-Schema vocabulary for the common units of CPA work.   |

```bash
maxed suite          # human-readable
maxed suite --json   # machine-readable
```

## Install

Requires Python 3.9+.

```bash
# From PyPI
pip install maxed-cli

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

### 1. Scaffold a suite-wired workspace

```bash
maxed init examples/workspace.yaml
maxed init examples/workspace.yaml --json
```

`init` creates the workspace tree and seeds a project that is **pre-wired to the
suite**:

- `requirements.txt` pinning `accounting-adapters` and `statement-normalizer`;
- `pipeline/import_transactions.py` — a runnable example that normalizes a
  synthetic bank statement with `statement-normalizer` and shows where to plug
  `accounting-adapters` in (it degrades gracefully if they are not installed);
- `fixtures/statement.csv` — a synthetic statement for that pipeline;
- `workpapers/example.workpaper.json` — for the bundled linter;
- `workpapers/example.close-checklist.json` — a `cpa-workpaper-spec`
  `close-checklist` document, valid against the published v0.1 schema;
- `configs/workspace.json` — a self-describing copy of the config.

Re-running is safe (idempotent): existing paths are reported as `exists`.

### 2. Validate a workspace config

```bash
maxed validate-config examples/workspace.yaml
maxed validate-config examples/workspace.yaml --json
```

A config is a small YAML or JSON file (see
[`examples/workspace.yaml`](examples/workspace.yaml)). The full shape is defined
by [`config.schema.json`](src/maxed_cli/schemas/config.schema.json). Exit code is
`0` on success, `1` on a schema error, `2` if the file is missing or unparseable.

### 3. Lint a workpaper — or any cpa-workpaper-spec document

The default `--doc-type workpaper` validates a simple section/line-item
workpaper against the schema bundled with this package, plus semantic checks
(unique section keys, unique line-item refs):

```bash
maxed lint-workpaper examples/example.workpaper.json
maxed lint-workpaper examples/example.workpaper.json --strict --json
```

`maxed-cli` is the front door to the wider suite, so `lint-workpaper` can also
validate documents against the published
[`cpa-workpaper-spec`](https://github.com/maxed-oss/cpa-workpaper-spec)
vocabulary — `engagement`, `close-checklist`, `tax-prep`, `engagement-letter`,
and `request-list-item`. The schemas live in (and are owned by) that
repository; point `--spec-dir` at a checkout's `schema/<version>/` directory and
the cross-file `$ref` graph resolves fully offline:

```bash
git clone https://github.com/maxed-oss/cpa-workpaper-spec
maxed lint-workpaper examples/close-checklist.example.json \
  --doc-type close-checklist \
  --spec-dir cpa-workpaper-spec/schema/v0.1 \
  --json
```

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
maxed lint-workpaper example-workspace/workpapers/example.workpaper.json --json
maxed smoke examples/workspace.yaml --json

# Wire in the suite and run the scaffolded pipeline
pip install -r example-workspace/requirements.txt
python example-workspace/pipeline/import_transactions.py
```

## Project layout

```
src/maxed_cli/
  cli.py            # Typer entrypoint (maxed ...)
  config.py         # config load + schema validation
  workpaper.py      # workpaper + cpa-workpaper-spec linting
  scaffold.py       # suite-wired workspace scaffolder
  suite.py          # catalog of the sibling open-source packages
  connectors/       # sandbox/mock connector harness
  schemas/          # bundled JSON Schemas (config + workpaper)
examples/           # example config, workpaper, and close-checklist
tests/              # pytest suite
.github/workflows/  # CI (test matrix + build)
```

## Development

```bash
pip install -e ".[dev]"
pytest
```

CI runs the test suite across Python 3.9–3.13 and builds the wheel/sdist on
every push and pull request — see
[`.github/workflows/ci.yml`](.github/workflows/ci.yml).

## Scope and non-goals

`maxed-cli` is intentionally narrow. It does not implement bookkeeping, tax, or
any accounting business logic; it does not connect to real systems; and it does
not handle real client data. It is a developer convenience layer around
configuration, scaffolding, suite onboarding, and local sandbox checks.

## License

Apache-2.0. See [LICENSE](LICENSE).
