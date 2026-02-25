# Contributing to `remake_dpp`

Thank you for your interest in contributing to `remake_dpp` – contributions of all kinds are welcome: bug reports, feature proposals, documentation, and code changes. 

This project focuses on Digital Product Passports (DPP), schema mappers (ECLASS, ISA‑95, etc.), and related tooling, so contributions that improve usability for both “manager” and “developer” personas are especially valuable. 
***

## Code of Conduct

By participating in this project, you agree to interact respectfully and constructively with others. Be kind, assume good intent, and keep discussions technical rather than personal. 

If you see unacceptable behavior, please open an issue or contact the maintainers.

***

## How to Propose Changes

1. **Check existing issues**
   - Look for an open issue that matches your idea or problem.
   - Comment on the issue if you want to take it on. 

2. **Open a new issue (if needed)**
   - Use a clear title and a concise description.
   - For bugs, include:
     - Steps to reproduce
     - Expected vs. actual behavior
     - Python version, OS, and relevant configuration
   - For features, explain:
     - The user story (“As a manager…”, “As a developer…”)
     - The schema(s) or DPP types involved
     - Rough idea of how it fits into the existing design. 

3. **Get early feedback**
   - For non‑trivial changes (new mappers, adapters, or APIs), open an issue or draft PR to confirm design direction before doing large amounts of work.

***

## Development Setup

1. **Fork and clone**
   ```bash
   git clone https://github.com/<your-username>/remake_dpp.git
   cd remake_dpp
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -e ".[dev]"
   ```
   If an extras group is not available, install from `requirements.txt` / `pyproject.toml` as documented in the repo. 

4. **Run tests**
   ```bash
   pytest
   ```
   Always ensure tests pass before opening a PR. 

***

## Project Structure (high‑level)

The project is organized roughly as follows (names may evolve):

- `nmis_dpp/`
  - `schema_registry.py`: global registry for schema mappers, lazy loading, and config.
  - `schema_base.py`: base `SchemaMapper` interfaces and common helpers.
  - `model.py`: core DPP domain model (e.g. `DigitalProductPassport`, layers, part classes).
  - `mappers/`: concrete mappers such as `ECLASSMapper`, `ISA95Mapper`, etc.
  - `config/`: YAML configuration:
    - Schema mappings (e.g. `eclass_mapping.yml`, `isa95_mapping.yml`)
    - Schema catalog (e.g. `schemas.yml`)
    - Starter kits (e.g. `starter_kits.yml`)
  - `api.py`: high‑level `create_dpp` and starter‑kit helpers.
  - `cli.py`: optional CLI entry points.

If you add new modules, keep them consistent with this structure and naming.

***

## Contribution Types

### 1. Bug fixes

- Add or update tests that reproduce the bug.
- Fix the bug with minimal, well‑scoped changes.
- Document behavior changes in docstrings or relevant docs.

Checklist:

- [ ] Failing test written
- [ ] Fix implemented
- [ ] All tests passing
- [ ] Changelog or PR description clearly describes the bug and fix. 

### 2. New or improved mappers

Examples: `ECLASSMapper`, `ISA95Mapper`, `BatteryDPPMapper`.

- Ensure your mapper subclasses `SchemaMapper`.
- Implement:
  - `get_schema_name` / `get_schema_version`
  - All required layer mapping methods (identity, structure, lifecycle, etc.)
  - `validate_mapping` with required fields for relevant DPP types
  - `get_context` (JSON‑LD context)
- Use YAML configs wherever possible instead of hard‑coding mappings.
- Register the mapper in `register_default_mappers()` via lazy loading.

Checklist:

- [ ] New mapper class added under `nmis_dpp/mappers/`
- [ ] Config YAML added or updated under `nmis_dpp/config/`
- [ ] Mapper registered in `schema_registry.register_default_mappers()`
- [ ] Unit tests for mapping and validation behavior

### 3. Adapters and DPP creation pipeline

If you work on input adapters or the high‑level `create_dpp` API:

- Keep adapters focused on **parsing input** and **building `DigitalProductPassport` objects**.
- Keep mappers focused on **mapping a DPP to a target schema** (e.g., JSON‑LD form).
- Prefer configuration‑driven behavior over hard‑coding where feasible.

Checklist:

- [ ] New adapter function(s) added (e.g. ECLASS / ISA‑95 / CSV)
- [ ] `create_dpp` path updated to support new `input_schema` or `output_schema`
- [ ] Tests cover typical and error cases

### 4. Schema metadata, sectors, and starter kits

- When editing schema metadata (`schemas.yml`):
  - Confirm canonical name and aliases.
  - Assign appropriate sectors and DPP types.
  - Set `eu_verified` / `industry_accepted` flags based on real status.
  - Keep descriptions short and non‑marketing.
- When editing starter kits (`starter_kits.yml`):
  - Ensure names, input/output schemas, and mapping files exist.
  - Keep them aligned with DPP types described in the PRD.

***

## Coding Standards

- Follow PEP 8 for Python style (use tools like `black` and `isort` if configured).
- Use type hints consistently.
- Add docstrings for public functions, classes, and any non‑obvious logic.
- Keep functions focused and composable; avoid large “god functions”.

***

## Testing

- Use `pytest` for tests.
- Place tests under `tests/` mirroring the package structure.
- For new features:
  - Add unit tests that cover both happy paths and edge cases.
  - For mapping logic, test at least:
    - Known good mappings
    - Missing or unknown types
    - Validation failures

Run:

```bash
pytest
```

before pushing. 

***

## Git & Pull Request Workflow

1. **Create a feature branch**
   ```bash
   git checkout -b feature/my-change
   ```

2. **Commit changes with clear messages**
   - Use descriptive commit messages (e.g. `Fix ECLASS domain scoring for sensors`).

3. **Keep the branch up to date**
   ```bash
   git fetch origin
   git rebase origin/main
   ```

4. **Open a Pull Request**
   - Link related issues (e.g. `Fixes #123`).
   - Summarize the change:
     - What problem it solves
     - How you approached it
     - Any trade‑offs or follow‑up work
   - Include testing notes (commands run, environments tested).

5. **Address review feedback**
   - Be responsive and open to suggestions.
   - Keep the discussion focused on code and design.

***

## Documentation

- Update or add documentation when behavior changes or new features are added.
- Prefer short, task‑oriented docs:
  - “How to add a new schema mapper”
  - “How to use starter kits”
  - “How to call `create_dpp` from your app”

