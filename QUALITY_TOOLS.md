# Code Quality Tools

This project includes comprehensive code quality tools for both frontend and backend development.

## Backend Quality Tools

### Tools Included
- **Black**: Automatic code formatter for Python
- **Ruff**: Fast Python linter
- **mypy**: Static type checker for Python
- **pytest**: Testing framework

### Usage

#### Automatic Code Formatting
Format all Python code in the backend directory:
```bash
./scripts/format.sh
```

#### Linting
Check code quality with Ruff:
```bash
./scripts/lint.sh
```

#### Type Checking
Run type checks with mypy:
```bash
./scripts/typecheck.sh
```

#### Run All Checks
Run the comprehensive quality check suite (linting, type checking, tests):
```bash
./scripts/quality-check.sh
```

## Frontend Quality Tools

### Tools Included
- **ESLint**: JavaScript linting
- **Prettier**: Code formatter for JavaScript/HTML/CSS

### Setup
First, install frontend dependencies in the frontend directory:
```bash
cd frontend/
npm install
```

### Usage

#### Automatic Code Formatting
Format all frontend code:
```bash
npm run format
```

Or using the script from project root:
```bash
./scripts/frontend-format.sh
```

#### Check Formatting
Check if code is properly formatted without making changes:
```bash
npm run format:check
```

#### Linting
Lint JavaScript code:
```bash
npm run lint
```

Or using the script from project root:
```bash
./scripts/frontend-lint.sh
```

#### Fix Linting Issues
Automatically fix linting issues:
```bash
npm run lint:fix
```

## Configuration

### Backend Configuration (`pyproject.toml`)
- **Black**: Line length 100, Python 3.13 target
- **Ruff**: Same line length, lints for common errors, imports, and best practices
- **mypy**: Type checking with missing import tolerance

### Frontend Configuration

#### ESLint (`.eslintrc.json`)
- Browser and ES2021 environment
- Recommended rules + Prettier compatibility
- Warnings for console usage
- Single quotes and 4-space indentation

#### Prettier (`.prettierrc.json`)
- Print width: 100 characters
- Tab width: 4 spaces
- Single quotes
- Trailing commas (ES5 compatibility)

## Pre-commit Hook (Optional)

To automatically run quality checks before committing, you can set up git hooks:

```bash
#!/bin/bash
# .git/hooks/pre-commit

./scripts/quality-check.sh
```

Make it executable:
```bash
chmod +x .git/hooks/pre-commit
```

## Continuous Integration

Use the quality check script in your CI/CD pipeline:
```bash
./scripts/quality-check.sh
```

This will exit with a non-zero status if any checks fail, which can be detected by CI systems.
