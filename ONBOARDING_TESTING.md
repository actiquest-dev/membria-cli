# Onboarding System - Testing & Validation Guide

## Quick Validation Checklist

Before deploying to production, validate these key points:

- [ ] All Python files compile without errors
- [ ] `is_first_run()` correctly detects new users
- [ ] Each screen saves state to config
- [ ] Navigation (Back/Skip/Next) works correctly
- [ ] Config persists to `~/.membria/config.toml`
- [ ] Main app shows after onboarding completes
- [ ] Onboarding doesn't trigger for returning users

## Test Environment Setup

### Prerequisites

```bash
# Ensure dependencies are installed
pip install textual rich toml anthropic openai

# Navigate to workspace
cd /Users/miguelaprossine/membria-cli
```

### Reset to "First Run" State

```bash
# Option 1: Remove entire config
rm -rf ~/.membria/

# Option 2: Keep config but reset providers
python3 << 'EOF'
import toml
from pathlib import Path

config_dir = Path.home() / ".membria"
config_file = config_dir / "config.toml"

if config_file.exists():
    with open(config_file) as f:
        config = toml.load(f)
    
    # Clear providers to trigger onboarding
    config['providers'] = {}
    
    with open(config_file, 'w') as f:
        toml.dump(config, f)
    
    print("✓ Config reset to first-run state")
else:
    print("✓ No config exists (first-run)")
EOF
```

## Unit Tests

### Test 1: Import and Syntax Validation

```bash
python3 << 'EOF'
# Verify onboarding_screens.py is syntactically valid
import sys
import py_compile

try:
    py_compile.compile(
        '/Users/miguelaprossine/membria-cli/src/membria/interactive/onboarding_screens.py',
        doraise=True
    )
    print("✓ onboarding_screens.py: Syntax OK")
except py_compile.PyCompileError as e:
    print(f"✗ Syntax error: {e}")
    sys.exit(1)

# Import the module
try:
    from membria.interactive.onboarding_screens import (
        OnboardingScreen,
        WelcomeScreen,
        ProviderSetupScreen,
        RoleAssignmentScreen,
        GraphDatabaseScreen,
        MonitoringLevelScreen,
        ThemeSelectionScreen,
        FirstDecisionScreen,
        SummaryScreen,
        OnboardingFlow,
    )
    print("✓ All screen classes imported successfully")
except ImportError as e:
    print(f"✗ Import error: {e}")
    sys.exit(1)

print("\n✅ All unit tests passed!")
EOF
```

### Test 2: ConfigManager Integration

```bash
python3 << 'EOF'
from membria.config import ConfigManager
from pathlib import Path
import shutil

# Create temp directory for testing
test_dir = Path("/tmp/membria_test")
if test_dir.exists():
    shutil.rmtree(test_dir)
test_dir.mkdir(parents=True)

# Test 1: Fresh config (first run)
print("Test 1: Fresh config detection...")
cfg = ConfigManager(str(test_dir))
assert cfg.is_first_run() == True, "Fresh config should be first run"
print("  ✓ is_first_run() returns True for new config")

# Test 2: Add provider (no longer first run)
print("\nTest 2: Provider addition...")
cfg.set("providers.anthropic.api_key", "test-key")
cfg.save()
cfg2 = ConfigManager(str(test_dir))  # Reload
assert cfg2.is_first_run() == False, "Config with providers shouldn't be first run"
print("  ✓ is_first_run() returns False after adding provider")

# Test 3: Verify config file
print("\nTest 3: Config persistence...")
cfg2.set("onboarding.completed", True)
cfg2.save()
cfg3 = ConfigManager(str(test_dir))  # Reload
assert cfg3.get("onboarding.completed") == True, "Config not persisted"
print("  ✓ Config values persist to TOML file")

# Cleanup
shutil.rmtree(test_dir)
print("\n✅ ConfigManager tests passed!")
EOF
```

### Test 3: Screen Composition

```bash
python3 << 'EOF'
from membria.interactive.onboarding_screens import (
    WelcomeScreen,
    ProviderSetupScreen,
    ThemeSelectionScreen,
)

# Verify each screen has required components
screens_to_test = [
    (WelcomeScreen, "Welcome"),
    (ProviderSetupScreen, "ProviderSetup"),
    (ThemeSelectionScreen, "ThemeSelection"),
]

for screen_class, name in screens_to_test:
    print(f"Testing {name}...")
    
    # Check class has required methods
    required_methods = ['compose', 'on_button_pressed']
    for method in required_methods:
        assert hasattr(screen_class, method), f"Missing {method}"
    
    # Check CSS is defined
    assert hasattr(screen_class, 'DEFAULT_CSS'), "Missing CSS"
    assert len(screen_class.DEFAULT_CSS) > 0, "Empty CSS"
    
    print(f"  ✓ {name} has all required components")

print("\n✅ All screen composition tests passed!")
EOF
```

## Integration Tests

### Test 4: Textual App Integration

Test that the onboarding flow integrates with the main app:

```bash
python3 << 'EOF'
from unittest.mock import Mock, MagicMock
from membria.config import ConfigManager
from membria.interactive.onboarding_screens import OnboardingFlow

# Create mock app
mock_app = Mock()
mock_app.push_screen = Mock()
mock_app.pop_screen = Mock()
mock_app.screen_stack = [Mock(), Mock()]  # Simulate screens

# Create config with no providers (first run)
test_cfg = ConfigManager("/tmp/membria_test_int")
test_cfg.config.providers = {}

print("Testing OnboardingFlow...")

# Create and start flow
flow = OnboardingFlow(mock_app, test_cfg)
assert flow.current_step == 0, "Should start at step 0"
assert flow.completed == False, "Should not be completed initially"
print("  ✓ OnboardingFlow initialized correctly")

# Test screen navigation
flow.start()
assert mock_app.push_screen.called, "Should push first screen"
print("  ✓ flow.start() pushes first screen")

flow.next_screen()
assert flow.current_step == 1, "Should advance to step 1"
print("  ✓ flow.next_screen() advances correctly")

flow.prev_screen()
assert flow.current_step == 0, "Should go back to step 0"
print("  ✓ flow.prev_screen() goes back correctly")

flow.mark_complete()
assert flow.completed == True, "Should be marked complete"
assert test_cfg.get("onboarding.completed") == True, "Config not marked"
print("  ✓ flow.mark_complete() sets completion flag")

print("\n✅ Integration tests passed!")
EOF
```

## Manual Testing Procedures

### Procedure 1: Full Flow Test

**Goal**: User completes all 8 screens and main app appears

**Steps:**
1. Reset config: `rm -rf ~/.membria/`
2. Launch app: `membria` (or appropriate launch command)
3. Verify WelcomeScreen appears
4. Click Next on each screen:
   - [Welcome] → Provider → Role → Database → Monitoring → Theme → Decision → Summary
5. Click [Start!] on Summary
6. **Verify**: Main app interface with welcome message appears

**Expected Results:**
- ✓ Each screen displays correctly
- ✓ Config updates visible in `cat ~/.membria/config.toml`
- ✓ No errors or crashes
- ✓ App is responsive after completion

### Procedure 2: Back Navigation Test

**Goal**: Verify back button works at each step

**Steps:**
1. Reset config: `rm -rf ~/.membria/`
2. Launch app and reach ProviderSetupScreen
3. Enter an API key, click Next
4. Verify you're on RoleAssignmentScreen
5. Click Back
6. **Verify**: You're back on ProviderSetupScreen with API key still there
7. Modify the key and click Next
8. **Verify**: Updated key is saved in config

**Expected Results:**
- ✓ Back button navigates to previous screen
- ✓ Form data persists when navigating
- ✓ Config saves on each [Next] click
- ✓ No data loss on navigation

### Procedure 3: Skip Functionality Test

**Goal**: Verify Skip button lets users jump ahead

**Steps:**
1. Reset config
2. Launch app on WelcomeScreen
3. Click [Skip]
4. **Verify**: Jumps to SummaryScreen
5. Observe which config keys are empty/missing
6. Click [Back]
7. **Verify**: Can return to previous step
8. Click [Start!] on SummaryScreen

**Expected Results:**
- ✓ [Skip] jumps to Summary from any screen
- ✓ Can still [Back] from Summary
- ✓ Config is partially filled (based on defaults)
- ✓ App launches with partial config

### Procedure 4: Configuration Persistence Test

**Goal**: Verify all config changes persist

**Steps:**
1. Reset config
2. Complete onboarding with:
   - Provider: OpenAI (key: sk-test-123)
   - Role: Budget
   - Database: Binary
   - Monitoring: L3 (Debug)
   - Theme: Gruvbox
   - Decision: "Use WebSocket", confidence 75, domain "networking"
3. After app launches, check config file:
   ```bash
   cat ~/.membria/config.toml
   ```

**Expected Results:**
- ✓ All entered values appear in config
- ✓ Theme is set to Gruvbox
- ✓ Monitoring level is L3
- ✓ First decision data is complete
- ✓ Role preset is recorded

### Procedure 5: First Run Detection Test

**Goal**: Verify onboarding only appears on first run

**Steps:**
1. Complete full onboarding (Procedure 1)
2. Close app
3. Relaunch app: `membria`
4. **Verify**: Main interface appears immediately (no onboarding)
5. Modify config: `rm ~/.membria/config.toml`
6. Relaunch app
7. **Verify**: Onboarding appears again

**Expected Results:**
- ✓ Onboarding appears on first run
- ✓ Onboarding doesn't appear on subsequent runs
- ✓ Removing config forces onboarding again
- ✓ App detects via `is_first_run()`

### Procedure 6: Escape Key Test

**Goal**: Verify Escape key exits onboarding gracefully

**Steps:**
1. Reset config
2. Launch app (WelcomeScreen appears)
3. Press Escape key
4. **Verify**: Onboarding closes, returns to shell
5. Relaunch app
6. **Verify**: Onboarding appears again (it didn't mark as complete)

**Expected Results:**
- ✓ Escape key exits onboarding
- ✓ Partial config is saved
- ✓ Onboarding still shows as first-run (not completed)
- ✓ No crash or hang

### Procedure 7: Theme Selection Live Update

**Goal**: Verify theme colors update as you select

**Steps:**
1. On ThemeSelectionScreen, select different themes
2. Observe text colors change live:
   - Nord: Blue headers, orange labels
   - Gruvbox: Red/orange palette
   - Dracula: Purple accents
3. Select "Dracula" and verify purple colors

**Expected Results:**
- ✓ Colors update when selecting theme
- ✓ Color scheme is consistent with choice
- ✓ No rendering glitches

## Automated Tests (If Using Test Framework)

### Pytest Example

```python
# test_onboarding.py
import pytest
from membria.config import ConfigManager
from membria.interactive.onboarding_screens import OnboardingFlow
from unittest.mock import Mock


@pytest.fixture
def temp_config(tmp_path):
    """Create a temporary config for testing."""
    return ConfigManager(str(tmp_path))


def test_onboarding_screens_import():
    """Test that all screen classes can be imported."""
    from membria.interactive.onboarding_screens import (
        WelcomeScreen, ProviderSetupScreen, SummaryScreen, OnboardingFlow
    )
    assert WelcomeScreen is not None
    assert ProviderSetupScreen is not None
    assert SummaryScreen is not None
    assert OnboardingFlow is not None


def test_first_run_detection(temp_config):
    """Test is_first_run() returns True for new config."""
    assert temp_config.is_first_run() == True


def test_first_run_after_provider(temp_config):
    """Test is_first_run() returns False after adding provider."""
    temp_config.set("providers.anthropic.api_key", "test-key")
    temp_config.save()
    cfg2 = ConfigManager(temp_config.config_dir)
    assert cfg2.is_first_run() == False


def test_onboarding_flow_navigation(temp_config):
    """Test OnboardingFlow navigation."""
    mock_app = Mock()
    mock_app.push_screen = Mock()
    mock_app.pop_screen = Mock()
    
    flow = OnboardingFlow(mock_app, temp_config)
    
    # Start
    flow.start()
    assert flow.current_step == 0
    
    # Next
    flow.next_screen()
    assert flow.current_step == 1
    
    # Previous
    flow.prev_screen()
    assert flow.current_step == 0


def test_onboarding_completion(temp_config):
    """Test marking onboarding as complete."""
    mock_app = Mock()
    flow = OnboardingFlow(mock_app, temp_config)
    
    flow.mark_complete()
    
    assert flow.completed == True
    assert temp_config.get("onboarding.completed") == True
```

Run tests:
```bash
pytest test_onboarding.py -v
```

## Performance Validation

### Test 8: Screen Load Time

```bash
python3 << 'EOF'
import time
from membria.interactive.onboarding_screens import WelcomeScreen
from membria.config import ConfigManager

# Time screen instantiation
start = time.time()
for _ in range(100):
    screen = WelcomeScreen(1, 8, ConfigManager("/tmp"))
elapsed = time.time() - start

avg_time = elapsed / 100
print(f"Screen instantiation: {avg_time*1000:.2f}ms per screen")

if avg_time < 0.01:  # 10ms
    print("✓ Screen creation is fast")
else:
    print("⚠️  Screen creation may be slow")
EOF
```

## Deployment Checklist

Before deploying to users:

- [ ] All tests pass (unit + integration)
- [ ] Manual procedures 1-7 completed successfully
- [ ] No Python syntax errors
- [ ] Config persistence verified
- [ ] Back navigation works at all steps
- [ ] Theme colors display correctly
- [ ] Escape key exits gracefully
- [ ] First-run detection works
- [ ] Subsequent launches skip onboarding
- [ ] Main app appears after completion
- [ ] Documentation is complete and accurate

## Continuous Validation

After deployment:

1. **Monitor Error Logs**: Check for any onboarding failures
2. **User Feedback**: Survey new users on onboarding experience
3. **Completion Rates**: Track what percentage complete all steps
4. **Drop-off Points**: Identify where users skip or exit
5. **Config Validity**: Verify configs created are valid

## Example Test Report

```
╔════════════════════════════════════════════╗
║  Onboarding System - Test Report           ║
║  Date: 2024-01-15  |  Status: PASS ✅      ║
╚════════════════════════════════════════════╝

Unit Tests:
  ✓ Syntax validation
  ✓ Screen class imports
  ✓ ConfigManager integration
  ✓ Screen composition checks
  
Integration Tests:
  ✓ App integration
  ✓ Config persistence
  ✓ Flow navigation
  ✓ Completion marking

Manual Tests:
  ✓ Full flow (8 screens)
  ✓ Back navigation
  ✓ Skip functionality
  ✓ Config persistence
  ✓ First-run detection
  ✓ Escape key handling
  ✓ Theme selection

Performance:
  ✓ Screen load: 2.3ms (target: <10ms)
  ✓ Config save: 1.1ms (target: <50ms)
  ✓ State transitions: <5ms

Result: READY FOR PRODUCTION ✅
```

## Summary

This guide provides comprehensive testing procedures to validate:
- ✅ Code quality and syntax
- ✅ Functional correctness
- ✅ Config persistence
- ✅ User experience
- ✅ Integration with app
- ✅ Performance characteristics

All tests should pass before shipping to users.
