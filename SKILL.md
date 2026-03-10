# Runway Skill

## Overview

Runway is a lightweight infrastructure deployment CLI tool designed for GitOps best practices. Built in Python (3.9-3.12) using Click for CLI and Pydantic v2 for configuration validation, it orchestrates multiple infrastructure-as-code tools (Terraform, CloudFormation/CFNgin, AWS CDK, Serverless Framework, static websites) under a unified interface. The single most important thing to understand: Runway is an **orchestration layer**, not a replacement for these tools—it manages execution context, environment resolution, and deployment ordering while delegating actual infrastructure operations to the underlying tools.

## Project Structure

```
runway/
├── _cli/              # Click-based CLI entry point and commands
│   ├── main.py        # CLI group registration (entry point: runway._cli.main:cli)
│   └── commands/      # Individual subcommands (deploy, destroy, plan, etc.)
├── core/              # Core orchestration API
│   ├── __init__.py    # Runway class with deploy(), destroy(), plan() methods
│   └── components/    # DeployEnvironment, deployment components
├── module/            # Module implementations for each IaC tool
│   ├── base.py        # RunwayModule base class (ALL modules inherit this)
│   ├── terraform.py   # Terraform module
│   ├── cdk.py         # AWS CDK module
│   ├── cloudformation.py  # CloudFormation module
│   ├── serverless.py  # Serverless Framework module
│   └── staticsite/    # Static website module (complex, has submodules)
├── config/            # Configuration parsing and validation
│   ├── models/        # Pydantic models for YAML config
│   │   ├── runway/    # runway.yml models
│   │   └── cfngin/    # cfngin.yml models
│   └── components/    # RunwayDeploymentDefinition, etc.
├── context/           # Execution context management
│   ├── _runway.py     # RunwayContext (main context object)
│   └── _cfngin.py     # CfnginContext (CloudFormation-specific)
├── cfngin/            # CloudFormation orchestration subsystem (LEGACY, complex)
│   ├── actions/       # deploy, destroy, diff actions
│   ├── blueprints/    # Troposphere-based CFN templates
│   ├── hooks/         # Lifecycle hooks (pre/post deploy)
│   ├── providers/     # AWS provider abstraction
│   └── plan.py        # DAG-based execution planning (753 lines)
├── lookups/           # Variable lookup system (${ssm path}, ${env VAR}, etc.)
│   └── handlers/      # cfn, ecr, env, random_string, ssm, var
├── env_mgr/           # Tool version management
│   └── tfenv.py       # Terraform version management
├── dependency_managers/  # Python dependency handling (Poetry, Pip)
├── utils/             # Shared utilities, Pydantic base classes
├── aws_sso_botocore/  # VENDORED: AWS SSO support (excluded from linting)
└── templates/         # Quickstart templates for new projects

tests/
├── conftest.py        # Global fixtures (cli_runner, cd_tmp_path, root_dir)
├── factories.py       # Global test factory (cli_runner_factory only)
├── functional/        # E2E tests against real AWS (NO mocks allowed)
│   ├── cfngin/        # CFNgin functional tests
│   ├── terraform/     # Terraform functional tests
│   └── ...
├── integration/       # Component interaction tests (limited mocking)
└── unit/              # Isolated unit tests (heavy mocking)
    ├── conftest.py    # Unit-specific fixtures (MockRunwayContext, etc.)
    ├── factories.py   # MockBoto3Session, MockRunwayContext, etc.
    └── ...            # Mirrors source structure
```

## Development Setup

```bash
# Clone and enter the repo
git clone https://github.com/rackspace/runway.git
cd runway

# Full setup (Poetry + npm + pre-commit hooks)
make setup

# Or individual steps:
poetry sync --ansi                    # Install Python dependencies
npm ci                                # Install Node dependencies (for pyright, cspell)
poetry run pre-commit install         # Install git hooks

# Verify setup
make lint                             # Should pass with no errors
make test-unit                        # Run unit tests
```

## Key Architectural Patterns

- **Module Abstraction Pattern**: All IaC tools implement `RunwayModule` base class (`runway/module/base.py:39`). Each module must implement `deploy()`, `destroy()`, `plan()`, and optionally `init()`. This abstraction allows Runway to treat all tools identically at the orchestration level while delegating tool-specific logic to subclasses.

- **Context Objects**: `RunwayContext` (`runway/context/_runway.py`) carries deployment state (environment, AWS region, credentials, working directory, stack_names for CFNgin targeting) through the entire execution. CFNgin has its own `CfnginContext` with additional CloudFormation-specific state. Context objects are created once and passed down—never instantiate multiple contexts.

- **Module and Stack Targeting**: CLI commands support granular targeting via `--module` (filter by module name/glob pattern) and `--stack` (filter CFNgin stacks). Module selection flows through `select_modules_by_name()` in `runway/_cli/utils.py`, while stack targeting passes through `RunwayContext.stack_names` to `CfnginContext`. The `--tag` option provides tag-based filtering with AND logic.

- **Pydantic Configuration Models**: All YAML configuration is parsed into Pydantic v2 models (`runway/config/models/`). Models use `ConfigDict(extra="ignore", validate_default=True, validate_assignment=True)`. The base class `ConfigProperty` (`runway/config/models/base.py`) adds helper methods. Always use these models rather than raw dicts.

- **Lookup System**: Variable resolution like `${ssm /path/to/param}` or `${env AWS_REGION}` uses a registry-based handler system. Handlers live in `runway/lookups/handlers/`. The lookup pattern is `${handler_name query::arg=value}`.

- **DAG-Based Execution (CFNgin)**: CloudFormation stacks are deployed using a dependency graph (`runway/cfngin/plan.py`). Stack dependencies are resolved automatically, enabling parallel deployment of independent stacks.

- **Test Isolation Levels**: Tests are strictly separated into three tiers:
  - **Unit**: Heavy mocking via `MockRunwayContext`, `MockCfnginContext`. Test single functions/methods.
  - **Integration**: Limited mocking, tests CLI command flows. Uses `click.testing.CliRunner`.
  - **Functional**: NO mocks. Runs against real AWS. Requires credentials. Skipped in forks.

## Common Tasks (with Examples)

### Targeting Specific Modules and Stacks

Runway supports granular targeting to deploy/destroy/plan specific modules or CFNgin stacks without affecting others.

**Target modules by exact name:**
```bash
# Deploy only the vpc.cfn module
runway deploy --module vpc.cfn

# Deploy multiple specific modules
runway deploy --module vpc.cfn --module rds.cfn --module app.cfn
```

**Target modules using glob patterns:**
```bash
# Deploy all modules matching pattern
runway deploy --module "network-*.cfn"

# Deploy all CFN modules
runway deploy --module "*.cfn"

# Combine multiple patterns
runway deploy --module "network-*" --module "database-*"
```

**Target specific CFNgin stacks within modules:**
```bash
# Deploy only specific stacks within CFNgin modules
runway deploy --module infra.cfn --stack vpc-stack --stack security-groups

# Plan changes for a single stack
runway plan --stack my-application-stack

# Destroy specific stacks (use with caution)
runway destroy --stack old-unused-stack
```

**Combine with tag filtering:**
```bash
# Deploy modules with specific tag AND matching name pattern
runway deploy --tag tier:network --module "*.cfn"
```

**How it works internally:**
1. `--module` patterns are matched using `fnmatch` glob matching in `runway/_cli/utils.py:_module_name_matches()`
2. `--stack` names are stored in `RunwayContext.stack_names` and passed to `CfnginContext`
3. CFNgin's `plan.py` filters the execution graph to only include specified stacks
4. Child modules (parallel groups) are also filtered by name

**Key files:**
- `runway/_cli/options.py`: CLI option definitions (`modules`, `stacks`)
- `runway/_cli/utils.py`: `select_modules_by_name()`, `_module_name_matches()`
- `runway/context/_runway.py`: `RunwayContext.stack_names` attribute
- `runway/cfngin/cfngin.py:_get_context()`: Passes stack_names to CfnginContext

### Inspecting Variables and Environment Variables

Runway provides two commands for inspecting variables—choose based on your use case:

| Command | Purpose | Output Format | Scope |
|---------|---------|---------------|-------|
| `runway envvars` | Export env_vars for shell use | Shell export statements | Deployment-level env_vars only |
| `runway variables` | Inspect all resolved values | YAML, JSON, or table | Everything (variables, params, env_vars) |

**`runway envvars`** - Shell-exportable environment variables:
```bash
# Output deployment env_vars as export statements
runway envvars
# Output:
# export ENV_VAR1="value1"
# export ENV_VAR2="value2"

# Set environment variables in your shell
eval $(runway envvars)

# For a specific environment
runway envvars -e prod
```

Use case: Setting OS environment variables for use outside Runway (e.g., in scripts, other tools).

**`runway variables`** - Full variable inspection:
```bash
# Show all variables (YAML format, default)
runway variables

# Output as JSON (machine-parseable)
runway variables --format json

# Output as formatted table
runway variables --format table

# Filter to specific module(s)
runway variables --module vpc.cfn
runway variables --module "network-*.cfn"

# Filter by tag
runway variables --tag tier:network

# For a specific environment
runway variables -e prod
```

Example output (`--format yaml`):
```yaml
runway_variables:
  vpc_cidr: 10.0.0.0/16
  environment: dev
deployments:
  - name: network-deployment
    parameters:
      param1: value1
    env_vars:
      AWS_REGION: us-east-1
    modules:
      - name: vpc.cfn
        path: vpc.cfn
        parameters:
          cidr_block: 10.0.0.0/16
        env_vars:
          MODULE_VAR: module_value
        options:
          stack_name: my-vpc
```

Use case: Debugging/inspecting what values will be applied before running deploy/destroy/plan.

**Key files:**
- `runway/_cli/commands/_envvars.py`: Shell export command
- `runway/_cli/commands/_variables.py`: Full variable inspection command
- `runway/core/__init__.py`: `Runway.get_env_vars()` method used by envvars

### Adding a New Module

To add support for a new IaC tool (e.g., Pulumi):

1. Create the module file at `runway/module/pulumi.py`:

```python
# runway/module/pulumi.py
from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast
import logging

from .base import ModuleOptions, RunwayModule

if TYPE_CHECKING:
    from pathlib import Path
    from .._logging import RunwayLogger
    from ..context import RunwayContext

LOGGER = cast("RunwayLogger", logging.getLogger(__name__))


class PulumiOptions(ModuleOptions):
    """Pulumi-specific module options."""

    def __init__(self, data: dict[str, Any]) -> None:
        self.stack = data.get("stack", "dev")


class Pulumi(RunwayModule["PulumiOptions"]):
    """Pulumi module."""

    def __init__(
        self,
        context: RunwayContext,
        *,
        module_root: Path,
        **kwargs: Any,
    ) -> None:
        super().__init__(context, module_root=module_root, **kwargs)
        self.options = PulumiOptions(kwargs.get("options") or {})

    def deploy(self) -> None:
        """Run pulumi up."""
        self.logger.info("deploying with Pulumi...")
        # Implementation here

    def destroy(self) -> None:
        """Run pulumi destroy."""
        self.logger.info("destroying with Pulumi...")

    def plan(self) -> None:
        """Run pulumi preview."""
        self.logger.info("previewing Pulumi changes...")
```

2. Register the module type in `runway/module/__init__.py`

3. Add config model in `runway/config/models/runway/options/` if needed

### Writing and Running Tests

**Unit test example** (`tests/unit/module/test_pulumi.py`):

```python
"""Test runway.module.pulumi."""
from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from runway.module.pulumi import Pulumi, PulumiOptions

if TYPE_CHECKING:
    from pathlib import Path
    from ..factories import MockRunwayContext

MODULE = "runway.module.pulumi"


class TestPulumi:
    """Test runway.module.pulumi.Pulumi."""

    def test_init(
        self, runway_context: MockRunwayContext, tmp_path: Path
    ) -> None:
        """Test __init__."""
        obj = Pulumi(
            runway_context,
            module_root=tmp_path,
            options={"stack": "production"},
        )
        assert obj.ctx == runway_context
        assert obj.options.stack == "production"
        assert obj.path == tmp_path

    def test_deploy(
        self,
        mocker: pytest.MockerFixture,
        runway_context: MockRunwayContext,
        tmp_path: Path,
    ) -> None:
        """Test deploy."""
        mock_subprocess = mocker.patch(f"{MODULE}.subprocess")
        obj = Pulumi(runway_context, module_root=tmp_path)
        obj.deploy()
        # Assert subprocess was called correctly
```

**Run tests**:

```bash
make test-unit                              # Unit tests only
make test-integration                       # Integration tests only
make test                                   # Unit + integration
make test-functional                        # Functional tests (requires AWS creds)
poetry run pytest tests/unit/module/test_pulumi.py -v  # Single file
poetry run pytest -k "test_deploy" -v       # By test name pattern
```

### Making a Breaking Change Safely

Example: Renaming a config field from `modules` to `components`:

1. **Add deprecation warning** while supporting both names:

```python
# runway/config/models/runway/__init__.py
from pydantic import model_validator

class RunwayDeploymentDefinitionModel(ConfigProperty):
    components: list[RunwayModuleDefinitionModel] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _handle_deprecated_fields(cls, values: dict) -> dict:
        if "modules" in values:
            import warnings
            warnings.warn(
                "'modules' is deprecated, use 'components' instead",
                DeprecationWarning,
                stacklevel=2,
            )
            values["components"] = values.pop("modules")
        return values
```

2. **Update all internal usages** (use grep):
```bash
poetry run ruff check . --select F841  # Find unused variables
```

3. **Update tests to cover both old and new paths**

4. **Document in CHANGELOG**

### Debugging a Failing Test

1. **Run with verbose output**:
```bash
poetry run pytest tests/unit/module/test_base.py::TestRunwayModuleNpm::test_init -vvs
```

2. **Use pdb on failure**:
```bash
poetry run pytest --pdb tests/unit/module/test_base.py -x
```

3. **Check fixture hierarchy** - fixtures flow from:
   - `tests/conftest.py` (global)
   - `tests/unit/conftest.py` (unit-specific, has `runway_context` fixture)
   - Module-level conftest if exists

4. **For mocking issues**, check `tests/unit/factories.py` for `MockRunwayContext` and `MockCfnginContext` implementations.

## Gotchas & Non-Obvious Rules

- **Module-level constants for mocking**: Test files define `MODULE = "runway.module.terraform"` at the top. Always use this pattern and reference it in `mocker.patch(f"{MODULE}.subprocess")` to ensure patches target the correct import location.

- **Functional tests skip in forks**: CI skips functional tests for PRs from forks (security: no AWS credentials). Check `needs.info.outputs.is-fork` in `.github/workflows/cicd.yml:73-74`.

- **AWS credentials in unit tests**: The `aws_credentials` fixture (`tests/unit/conftest.py:45-73`) sets fake credentials session-wide. Real credentials are NOT used in unit tests.

- **Vendored code is excluded from linting**: `runway/aws_sso_botocore/` is vendored and excluded in `pyproject.toml` ruff config. Don't modify this directory.

- **CFNgin is complex legacy code**: The `runway/cfngin/` directory (especially `plan.py` at 753 lines, `utils.py` at 938 lines) is mature but complex. Changes here require careful testing.

- **TYPE_CHECKING imports**: The codebase uses `from __future__ import annotations` everywhere. Type hints are strings, and imports inside `if TYPE_CHECKING:` blocks are only for static analysis.

- **pytest markers for functional tests**: Use `--functional` to run only functional tests, `--integration` to include integration tests with unit tests, `--integration-only` for just integration tests. Default `pytest` runs only unit tests.

- **CLI tests use `cli_runner` fixture**: Access via `@pytest.mark.cli_runner(env={"KEY": "val"})` marker or directly via the fixture. See `tests/conftest.py:51-53`.

- **Don't use `git status -uall`**: The CI explicitly avoids this flag (memory issues on large repos). See `.github/workflows/cicd.yml`.

- **Module targeting uses OR logic, tags use AND**: When using `--module` multiple times, modules matching ANY pattern are included (OR logic). When using `--tag` multiple times, modules must have ALL tags (AND logic). You cannot combine `--module` and `--tag` in the same command—use one or the other.

- **Stack targeting only works with CFNgin**: The `--stack` option only affects CloudFormation/CFNgin modules. For other module types (Terraform, CDK, Serverless), this option is ignored. Stack names must match exactly (no glob patterns).

## Code Style & Conventions

**Enforced by tooling (CI will reject violations):**

```bash
make lint          # Run ruff format check + ruff check + pyright
make fix           # Auto-fix ruff issues + run pre-commit
```

- **Ruff**: Line length 100 (140 for pycodestyle errors). Format with `poetry run ruff format .`
- **Pyright**: Strict mode, Python 3.9 target. Run via `npm exec --no -- pyright --venvpath ./`
- **Imports**: isort via ruff. Local folders: `runway`, `tests`. First-party imports grouped.
- **Docstrings**: Google style. Brief summary line, Args/Returns sections.

**Convention-only (not enforced but expected):**

- All modules use `from __future__ import annotations`
- Type hints for all public functions
- `LOGGER = cast("RunwayLogger", logging.getLogger(__name__))` pattern for loggers
- Test classes named `TestClassName` matching the class under test
- Test methods named `test_method_name` or `test_method_name_specific_case`

**Pre-commit hooks** (run automatically on commit):
- YAML/JSON/TOML formatting
- Markdown formatting
- Spell checking (cspell)
- Trailing whitespace removal

## External Dependencies & Integrations

- **boto3/botocore**: AWS SDK. All AWS operations go through context's `get_session()` method, enabling test stubbing.

- **moto**: AWS service mocking for tests. Imported per-service: `moto[ec2,ecs,iam,s3,ssm]`.

- **troposphere**: Python library for CloudFormation template generation. Used heavily in CFNgin blueprints (`runway/cfngin/blueprints/`).

- **docker**: Docker SDK for Python. Used in CFNgin hooks for container operations.

- **Vendored `aws_sso_botocore`**: Located at `runway/aws_sso_botocore/`, provides AWS SSO credential support not yet in upstream botocore. Excluded from all linting.

- **poetry-dynamic-versioning**: Version is NOT in pyproject.toml—it's computed from git tags at build time.

## Glossary

| Term | Meaning |
|------|---------|
| **Deployment** | A collection of modules to deploy together, defined in `runway.yml`. Has its own regions, env vars, and parameters. |
| **Module** | A single IaC component (one Terraform project, one CDK app, etc.). Maps to a directory. Can be targeted via `--module` CLI option. |
| **CFNgin** | Runway's built-in CloudFormation orchestration engine. Supports blueprints (Python), hooks, and stack dependencies. |
| **Stack** | A CloudFormation stack managed by CFNgin. Can be targeted via `--stack` CLI option for granular operations. |
| **Blueprint** | A Python class (using troposphere) that generates CloudFormation templates. Lives in `cfngin/blueprints/`. |
| **Hook** | Pre/post deployment code that runs during CFNgin operations. Lives in `cfngin/hooks/`. |
| **Lookup** | Variable substitution syntax like `${ssm /path}` or `${env VAR}`. Resolved at runtime. |
| **Deploy Environment** | The target environment (dev, staging, prod). Determined by `DEPLOY_ENVIRONMENT` env var or directory name. |
| **Context** | Object carrying execution state (`RunwayContext` or `CfnginContext`). Created once, passed everywhere. Includes `stack_names` for stack targeting. |
| **Tag** | Module metadata for filtering. Use `--tag` CLI option for tag-based selection (AND logic for multiple tags). |
| **tfenv** | Terraform version manager integration. Runway auto-installs the correct Terraform version based on `.terraform-version`. |
| **Child Module** | A module nested within a `parallel:` block. Can be targeted by name like regular modules. |
| **envvars** | CLI command that outputs deployment-level `env_vars` as shell export statements. Use with `eval $(runway envvars)`. |
| **variables** | CLI command that shows all resolved variables, parameters, and env_vars in YAML/JSON/table format. For debugging/inspection. |
