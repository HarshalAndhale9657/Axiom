# Testing Conventions

- **Runner:** `pytest tests/ -v`. Keep tests fast and deterministic (seeded).
- **What must have tests (priority order):**
  1. **Leakage guard** — assert no feature is (near-)perfectly predictive of the label; assert history features use only past rows.
  2. **Cost metric** — unit-test the BMR cost function and τ\* selection on a tiny hand-checked example.
  3. **Decision core / rules** — each deterministic rule (auto-approve, non-serviceable→hold, blocklist, velocity-ring) triggers exactly when expected.
  4. **Bounded action space** — the agent/decisioner can only ever emit an allowed action; assert it can't produce anything else.
  5. **Data generator** — output schema, value ranges, and that RTO rates land in realistic bands (COD ≫ prepaid).
- **Style:** arrange-act-assert; one behavior per test; name tests `test_<unit>_<behavior>`.
- **No network in tests** — mock the LLM provider; never call a paid/real API in the test suite.
- Run the relevant tests and **show output** before claiming a change works.
