# Testing Guide for EasySweeps CLI

This directory contains comprehensive tests for the EasySweeps CLI application. The tests are designed to ensure reliability, maintainability, and correct behavior of all CLI commands.

## Test Structure

### Test Files
- `test_cli_sweep.py` - Tests for the `sweep` command
- `test_cli_agent.py` - Tests for the `agent` command  
- `test_cli_status.py` - Tests for the `status` command
- `test_cli_kill.py` - Tests for the `kill` command
- `test_integration.py` - Integration tests for command workflows
- `conftest.py` - Shared fixtures and test configuration

### Testing Approach

#### 1. **Unit Tests with Click Testing**
- Uses Click's `CliRunner` for isolated command testing
- Mocks external dependencies (wandb, subprocess, filesystem)
- Tests command-specific logic and error handling
- Fast execution and deterministic results

#### 2. **Integration Tests**
- Tests command workflows and inter-command dependencies
- Verifies file persistence between commands
- Tests configuration integration
- End-to-end scenario validation

#### 3. **Mocking Strategy**
- **wandb operations**: Mocked to avoid network calls and external dependencies
- **subprocess calls**: Mocked to simulate systemctl behavior without requiring systemd
- **filesystem operations**: Uses temporary directories for isolation
- **configuration**: Mocked for consistent test environment

## Running Tests

### Setup
```bash
# Install test dependencies
pip install -e ".[test]"

# Or install individually
pip install pytest pytest-cov pytest-mock
```

### Basic Test Execution
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=easysweeps --cov-report=html

# Run specific test file
pytest tests/test_cli_sweep.py

# Run specific test
pytest tests/test_cli_sweep.py::TestSweepCommand::test_sweep_command_success
```

### Verbose Output
```bash
# Detailed output
pytest -v -s

# Show test coverage details
pytest --cov=easysweeps --cov-report=term-missing
```

## Test Scenarios Covered

### Sweep Command Tests
- ✅ Successful sweep creation
- ✅ Custom file paths handling
- ✅ Missing template/variants file errors
- ✅ Log file creation and updates
- ✅ Exception handling

### Agent Command Tests
- ✅ Successful agent launch
- ✅ Multiple agents per sweep
- ✅ Force recopy functionality
- ✅ Invalid GPU list validation
- ✅ Available sweeps display
- ✅ Args object construction

### Status Command Tests
- ✅ Active sweeps display
- ✅ Inactive sweeps display
- ✅ Systemd unit name parsing
- ✅ Malformed unit name handling
- ✅ Missing sweep files handling
- ✅ Subprocess error handling

### Kill Command Tests
- ✅ Force kill with confirmation
- ✅ GPU-specific targeting
- ✅ Sweep-specific targeting
- ✅ Combined sweep+GPU targeting
- ✅ Active sweeps listing
- ✅ Pattern construction

### Integration Tests
- ✅ Full workflow (sweep → agent → status)
- ✅ Command chaining scenarios
- ✅ File persistence between commands
- ✅ Configuration integration
- ✅ Error handling consistency

## Best Practices

### When Writing New Tests
1. **Use descriptive test names** that explain the scenario
2. **Mock external dependencies** to ensure test isolation
3. **Test both success and failure paths**
4. **Use fixtures** for common setup patterns
5. **Assert on meaningful outputs** not just exit codes

### Test Organization
- Group related tests in classes
- Use fixtures for common setup
- Keep tests focused and independent
- Mock at the appropriate level (not too high, not too low)

### Coverage Goals
- Aim for >90% code coverage
- Focus on critical paths and error handling
- Don't sacrifice test quality for coverage metrics

## Continuous Integration

The tests are designed to run in CI environments without requiring:
- System dependencies (systemd, wandb account)
- Network access
- GPU hardware
- Specific filesystem permissions

## Troubleshooting

### Common Issues
1. **Import errors**: Ensure the package is installed in development mode (`pip install -e .`)
2. **Fixture not found**: Check that `conftest.py` is in the same directory
3. **Mock not working**: Verify the patch target matches the actual import path
4. **Temp directory issues**: The `temp_dir` fixture automatically cleans up

### Debugging Tips
- Use `pytest -s` to see print statements
- Add `import pdb; pdb.set_trace()` for debugging
- Check mock call history: `mock_obj.call_args_list`
- Verify file contents in temp directories before cleanup 