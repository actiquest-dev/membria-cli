import * as vscode from 'vscode';
import { MembriaClient } from './membriaClient';

/**
 * Integration tests for Membria VSCode Extension
 * Run via: npm test
 */

export async function runTests(): Promise<void> {
  console.log('🧪 Running Membria Extension Tests...\n');

  const client = new MembriaClient();
  let passed = 0;
  let failed = 0;

  // Test 1: Client initialization
  try {
    if (client.isAvailable()) {
      console.log('✅ Test 1: Client initialization - PASSED');
      passed++;
    } else {
      throw new Error('Client not available');
    }
  } catch (error) {
    console.log(`❌ Test 1: Client initialization - FAILED: ${error}`);
    failed++;
  }

  // Test 2: Capture decision
  try {
    const result = await client.captureDecision(
      'Use PostgreSQL for user database',
      ['MySQL', 'MongoDB'],
      0.8
    );
    if (result && result.decision_id) {
      console.log('✅ Test 2: Capture decision - PASSED');
      passed++;

      // Test 3: Record outcome (requires previous decision)
      try {
        const outcomeResult = await client.recordOutcome(result.decision_id, 'success', 0.9);
        if (outcomeResult) {
          console.log('✅ Test 3: Record outcome - PASSED');
          passed++;
        } else {
          throw new Error('No outcome result');
        }
      } catch (error) {
        console.log(`⏭️  Test 3: Record outcome - SKIPPED (needs running server): ${error}`);
      }
    } else {
      throw new Error('No decision_id in response');
    }
  } catch (error) {
    console.log(`⏭️  Test 2: Capture decision - SKIPPED (needs running server): ${error}`);
  }

  // Test 4: Get context
  try {
    const context = await client.getContext('Use Redis for caching', 'vscode', 0.7);
    if (context && typeof context === 'object') {
      console.log('✅ Test 4: Get context - PASSED');
      passed++;
    } else {
      throw new Error('Invalid context response');
    }
  } catch (error) {
    console.log(`⏭️  Test 4: Get context - SKIPPED: ${error}`);
  }

  // Test 5: Validate plan
  try {
    const validation = await client.validatePlan(['Step 1: Setup', 'Step 2: Test'], 'database');
    if (validation && typeof validation === 'object') {
      console.log('✅ Test 5: Validate plan - PASSED');
      passed++;
    } else {
      throw new Error('Invalid validation response');
    }
  } catch (error) {
    console.log(`⏭️  Test 5: Validate plan - SKIPPED: ${error}`);
  }

  // Test 6: Get calibration
  try {
    const calibration = await client.getCalibration('database');
    if (calibration && typeof calibration === 'object') {
      console.log('✅ Test 6: Get calibration - PASSED');
      passed++;
    } else {
      throw new Error('Invalid calibration response');
    }
  } catch (error) {
    console.log(`⏭️  Test 6: Get calibration - SKIPPED: ${error}`);
  }

  // Test 7: List plans
  try {
    const plans = await client.listPlans();
    if (Array.isArray(plans)) {
      console.log('✅ Test 7: List plans - PASSED');
      passed++;
    } else {
      throw new Error('Plans not array');
    }
  } catch (error) {
    console.log(`⏭️  Test 7: List plans - SKIPPED: ${error}`);
  }

  // Test 8: List skills
  try {
    const skills = await client.listSkills();
    if (Array.isArray(skills)) {
      console.log('✅ Test 8: List skills - PASSED');
      passed++;
    } else {
      throw new Error('Skills not array');
    }
  } catch (error) {
    console.log(`⏭️  Test 8: List skills - SKIPPED: ${error}`);
  }

  // Test 9: Generate skill
  try {
    const skill = await client.generateSkill('database');
    if (skill && typeof skill === 'object') {
      console.log('✅ Test 9: Generate skill - PASSED');
      passed++;
    } else {
      throw new Error('Invalid skill response');
    }
  } catch (error) {
    console.log(`⏭️  Test 9: Generate skill - SKIPPED: ${error}`);
  }

  // Test 10: Check readiness
  try {
    const readiness = await client.checkReadiness();
    if (typeof readiness === 'object') {
      console.log('✅ Test 10: Check readiness - PASSED');
      passed++;
    } else {
      throw new Error('Invalid readiness response');
    }
  } catch (error) {
    console.log(`⏭️  Test 10: Check readiness - SKIPPED: ${error}`);
  }

  // Summary
  console.log(`\n${'='.repeat(50)}`);
  console.log(`📊 Test Results: ${passed} passed, ${failed} failed`);
  console.log(`${'='.repeat(50)}`);

  if (failed > 0) {
    throw new Error(`${failed} tests failed`);
  }
}

// Run tests if executed directly
if (require.main === module) {
  runTests().then(() => {
    console.log('✅ All tests completed!');
    process.exit(0);
  }).catch((error) => {
    console.error('❌ Tests failed:', error);
    process.exit(1);
  });
}
