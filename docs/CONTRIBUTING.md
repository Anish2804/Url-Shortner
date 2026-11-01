# Contributing Guidelines — URL Shortener & Distributed Analytics Platform

## Engineering Principles & Code Quality Standards

We welcome contributions to the platform. To maintain our 9.5–10/10 engineering standard, all contributions must adhere to the following conventions:

1. **Test-Driven Rigor:** Every new feature, endpoint, or service modification must include corresponding unit and integration tests. Pull requests dropping code coverage will be rejected.
2. **Zero-Warning Static Analysis:** Code must pass `flake8` linting and `mypy` strict type checking without warnings or suppressed errors.
3. **Reversible Database Migrations:** Any schema alteration must include both `upgrade()` and `downgrade()` methods in Alembic, thoroughly verified with `alembic downgrade -1` followed by `alembic upgrade head`.
4. **Security by Design:** Never introduce SQL string concatenations, never log sensitive parameters, and ensure all mutation operations verify ownership to prevent IDOR vulnerabilities.

---

## Local Development Setup

```bash
# 1. Clone repository
git clone https://github.com/yourorg/url-shortener.git
cd url-shortener

# 2. Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 3. Install development dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install flake8 mypy pytest pytest-cov

# 4. Copy environment configuration
cp .env.example .env

# 5. Run tests to confirm local baseline
pytest -v
```

---

## Pull Request Lifecycle

1. Fork the repository and create a feature branch (`git checkout -b feature/async-link-tagging`).
2. Implement your changes following established patterns in `app/`.
3. Run the full test suite and linter:
   ```bash
   flake8 app
   mypy app
   pytest -v
   ```
4. Commit your changes using conventional commit formatting (`feat: add custom domain SSL provisioning`).
5. Submit your Pull Request targeting the `main` branch.
