# Contributing to Supabase MCP Server

Thank you for your interest in contributing to the Supabase MCP Server! This document provides guidelines and information for contributors.

## 🚀 Getting Started

### Prerequisites

- Python 3.11 or higher
- Docker and Docker Compose
- Poetry (for dependency management)
- Git

### Development Setup

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/yourusername/mcp_supabase_self-hosted.git
   cd mcp_supabase_self-hosted
   ```

2. **Install dependencies**
   ```bash
   # Install Poetry if you haven't already
   curl -sSL https://install.python-poetry.org | python3 -

   # Install project dependencies
   poetry install --with dev
   ```

3. **Set up pre-commit hooks**
   ```bash
   poetry run pre-commit install
   ```

4. **Create environment configuration**
   ```bash
   cp .env.example .env
   # Edit .env with your test configuration
   ```

5. **Run tests to verify setup**
   ```bash
   poetry run pytest
   ```

## 🛠️ Development Workflow

### Code Style

We use several tools to maintain code quality:

- **Black** for code formatting
- **isort** for import sorting
- **flake8** for linting
- **mypy** for type checking

Run all checks:
```bash
make check
```

Format code:
```bash
make format
```

### Testing

We maintain high test coverage (90%+). Please ensure your contributions include appropriate tests.

**Run all tests:**
```bash
poetry run pytest
```

**Run tests with coverage:**
```bash
poetry run pytest --cov=src --cov-report=term-missing
```

**Run specific test categories:**
```bash
# Unit tests only
poetry run pytest -m unit

# Integration tests only
poetry run pytest -m integration

# Security tests
poetry run pytest tests/test_*security* tests/test_*auth*
```

### Making Changes

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Follow the existing code style and patterns
   - Add tests for new functionality
   - Update documentation as needed
   - Ensure all tests pass

3. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

   We follow [Conventional Commits](https://www.conventionalcommits.org/):
   - `feat:` for new features
   - `fix:` for bug fixes
   - `docs:` for documentation changes
   - `test:` for test additions/changes
   - `refactor:` for code refactoring
   - `perf:` for performance improvements
   - `security:` for security-related changes

4. **Push and create a pull request**
   ```bash
   git push origin feature/your-feature-name
   ```

## 📋 Contribution Guidelines

### What We're Looking For

- **Bug fixes** with clear reproduction steps
- **New features** that align with the project goals
- **Performance improvements** with benchmarks
- **Security enhancements** with threat analysis
- **Documentation improvements** for clarity
- **Test coverage improvements**

### Code Requirements

- **Type hints** for all function parameters and return values
- **Docstrings** for all public functions and classes
- **Error handling** with appropriate logging
- **Tests** for all new functionality
- **Security considerations** for any user-facing features

### Pull Request Process

1. **Ensure your PR addresses a specific issue or need**
2. **Include a clear description** of what your PR does
3. **Reference any related issues** using `Fixes #123` or `Closes #123`
4. **Ensure all tests pass** and coverage remains high
5. **Update documentation** if your changes affect the API or usage
6. **Be responsive to feedback** during the review process

### Security Considerations

This project handles database connections and user authentication. Please:

- **Never commit secrets** or credentials
- **Validate all inputs** thoroughly
- **Follow security best practices** for authentication and authorization
- **Report security vulnerabilities** privately via email first

## 🏗️ Project Structure

```
src/supabase_mcp_server/
├── core/                    # Core utilities (logging, etc.)
├── mcp/                     # MCP protocol implementation
├── middleware/              # Authentication & security middleware
├── services/                # Business logic services
├── config.py               # Configuration management
└── main.py                 # Application entry point
```

### Key Components

- **MCP Protocol** (`mcp/`): Core MCP implementation
- **Services** (`services/`): Database, Supabase API, storage, etc.
- **Middleware** (`middleware/`): Authentication, rate limiting, security
- **Configuration** (`config.py`): Environment and settings management

## 🧪 Testing Guidelines

### Test Categories

- **Unit Tests** (`tests/test_*.py`): Test individual components in isolation
- **Integration Tests**: Test component interactions
- **Security Tests**: Test authentication, authorization, and security features
- **Performance Tests**: Validate performance characteristics

### Writing Tests

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

class TestYourComponent:
    @pytest.fixture
    def component(self):
        return YourComponent()
    
    async def test_your_feature(self, component):
        # Arrange
        expected_result = "expected"
        
        # Act
        result = await component.your_method()
        
        # Assert
        assert result == expected_result
```

## 📚 Documentation

### Code Documentation

- Use **clear, descriptive names** for variables and functions
- Add **docstrings** to all public functions:
  ```python
  async def process_request(self, request: Request) -> Response:
      """Process an incoming request and return a response.
      
      Args:
          request: The incoming HTTP request
          
      Returns:
          The processed response
          
      Raises:
          ValidationError: If the request is invalid
      """
  ```

### API Documentation

- Update **README.md** for user-facing changes
- Update **docstrings** for API changes
- Add **examples** for new features

## 🐛 Reporting Issues

### Bug Reports

Please include:
- **Clear description** of the issue
- **Steps to reproduce** the problem
- **Expected vs actual behavior**
- **Environment details** (OS, Python version, etc.)
- **Logs or error messages** if available

### Feature Requests

Please include:
- **Clear description** of the proposed feature
- **Use case** and motivation
- **Proposed implementation** approach (if you have ideas)
- **Potential impact** on existing functionality

## 🤝 Community Guidelines

- **Be respectful** and inclusive in all interactions
- **Provide constructive feedback** during code reviews
- **Help others** learn and contribute
- **Follow the code of conduct** (treat everyone with respect)

## 📞 Getting Help

- **GitHub Issues**: For bugs and feature requests
- **GitHub Discussions**: For questions and general discussion
- **Documentation**: Check the README and inline documentation first

## 🎉 Recognition

Contributors will be recognized in:
- **CHANGELOG.md** for significant contributions
- **README.md** contributors section
- **Release notes** for major features

Thank you for contributing to the Supabase MCP Server! 🚀