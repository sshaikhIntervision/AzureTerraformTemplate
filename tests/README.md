# Azure Terraform Template - Test Suite

Comprehensive test suite for the Azure Functions chatbot system.

## Overview

This test suite provides extensive coverage for:
- **Database Functions**: ChatSessionRetreival, DeleteChatHandler, UpdateChatlogsDB, FeedbackHandler
- **File Processing**: ReadUploadDoc (PDF, DOCX, TXT parsing)
- **API Integration**: ChatTransactionHandler (orchestration)
- **AI Integration**: ChatAssistantHandler (Azure OpenAI)
- **Integration Tests**: End-to-end database operations

## Directory Structure

```
tests/
├── conftest.py                           # Shared fixtures and configuration
├── unit/                                 # Unit tests
│   ├── test_chat_session_retrieval.py
│   ├── test_delete_chat_handler.py
│   ├── test_update_chatlogs_db.py
│   ├── test_feedback_handler.py
│   ├── test_read_upload_doc.py
│   ├── test_chat_transaction_handler.py
│   └── test_chat_assistant_handler.py
├── integration/                          # Integration tests
│   └── test_database_operations.py
├── requirements.txt                      # Test dependencies
└── README.md                            # This file
```

## Installation

### 1. Install Test Dependencies

```bash
pip install -r tests/requirements.txt
```

Or install in development mode:

```bash
pip install -e ".[dev]"
```

### 2. Set Up Environment Variables

For unit tests (uses mocks, no real services needed):
```bash
# No environment variables required - tests use mocks
```

For integration tests (requires real database):
```bash
export INTEGRATION_TEST_DB=true
export TEST_COSMOPG_HOST=your-test-db.postgres.database.azure.com
export TEST_COSMOPG_DBNAME=test_database
export TEST_COSMOPG_USER=test_user
export TEST_COSMOPG_PASSWORD=your_password
export TEST_COSMOPG_PORT=5432
```

## Running Tests

### Run All Tests

```bash
pytest
```

### Run Unit Tests Only

```bash
pytest tests/unit/
```

### Run Integration Tests Only

```bash
# Requires INTEGRATION_TEST_DB=true
pytest tests/integration/
```

### Run Tests by Marker

```bash
# Run only database tests
pytest -m database

# Run only file processing tests
pytest -m fileprocessing

# Run only API tests
pytest -m api

# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration
```

### Run Specific Test File

```bash
pytest tests/unit/test_chat_session_retrieval.py
```

### Run Specific Test Function

```bash
pytest tests/unit/test_chat_session_retrieval.py::TestChatSessionRetreival::test_successful_session_retrieval_with_results
```

## Test Coverage

### Generate Coverage Report

```bash
# Run tests with coverage
pytest --cov=azure-deployment/functions --cov-report=html --cov-report=term

# View HTML report
open htmlcov/index.html
```

### Coverage by Module

```bash
pytest --cov=azure-deployment/functions --cov-report=term-missing
```

## Test Markers

Tests are organized using pytest markers:

- `@pytest.mark.unit` - Unit tests (mocked dependencies)
- `@pytest.mark.integration` - Integration tests (real services)
- `@pytest.mark.database` - Database-related tests
- `@pytest.mark.fileprocessing` - File processing tests
- `@pytest.mark.api` - API integration tests

## Writing New Tests

### Unit Test Template

```python
import pytest
from unittest.mock import Mock, patch
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__),
                '../../azure-deployment/functions/YourFunction'))

@pytest.mark.unit
class TestYourFunction:
    @pytest.fixture
    def mock_request(self):
        mock_req = Mock()
        mock_req.get_json.return_value = {'test': 'data'}
        return mock_req

    @patch('YourFunction.some_dependency')
    def test_your_function(self, mock_dependency, mock_request):
        from YourFunction import your_function

        response = your_function(mock_request)

        assert response.status_code == 200
```

### Integration Test Template

```python
import pytest

pytestmark = pytest.mark.skipif(
    os.getenv('INTEGRATION_TEST_DB') != 'true',
    reason="Integration tests require INTEGRATION_TEST_DB=true"
)

@pytest.mark.integration
@pytest.mark.database
class TestDatabaseIntegration:
    def test_database_operation(self, db_connection):
        # Your integration test here
        pass
```

## Continuous Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v2

    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.9'

    - name: Install dependencies
      run: |
        pip install -r tests/requirements.txt

    - name: Run unit tests
      run: |
        pytest tests/unit/ -v --cov --cov-report=xml

    - name: Upload coverage
      uses: codecov/codecov-action@v2
```

## Test Best Practices

1. **Isolation**: Each test should be independent and not rely on other tests
2. **Mocking**: Use mocks for external dependencies (databases, APIs)
3. **Clear Names**: Test names should clearly describe what they test
4. **Assertions**: Use specific assertions with clear error messages
5. **Fixtures**: Use fixtures for common setup/teardown
6. **Coverage**: Aim for >80% code coverage
7. **Fast Tests**: Unit tests should run quickly (<1s each)

## Common Issues

### Import Errors

If you get import errors:
```bash
# Make sure you're running from the project root
cd /home/user/AzureTerraformTemplate

# Or add the path explicitly
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Database Connection Errors

For integration tests:
- Ensure `INTEGRATION_TEST_DB=true` is set
- Verify database credentials are correct
- Check that test database exists and is accessible
- Ensure firewall rules allow connection

### Mock Issues

If mocks aren't working:
- Check the import path in `@patch` decorators
- Ensure mocks are patched where they're used, not where they're defined
- Use `patch.dict(os.environ, {...})` for environment variables

## Test Statistics

- **Total Test Files**: 8
- **Total Test Functions**: 150+
- **Estimated Coverage**: 85%+
- **Average Test Runtime**: <30 seconds (unit tests)

## Contributing

When adding new functionality:

1. Write tests first (TDD approach)
2. Ensure all existing tests pass
3. Add tests for edge cases and error conditions
4. Update this README if adding new test categories
5. Maintain >80% code coverage

## Support

For questions or issues with tests:
- Check test output and error messages
- Review test fixtures in `conftest.py`
- Ensure all dependencies are installed
- Verify environment configuration

## License

Same as main project license.
