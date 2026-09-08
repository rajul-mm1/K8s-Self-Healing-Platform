// Runs with Node's built-in test runner (node --test) -- no external
// test framework needed, and no database required, so this passes in CI
// without any live MongoDB instance.
const test = require('node:test');
const assert = require('node:assert/strict');
const { isValidTitle } = require('../utils/validateTodo');

test('isValidTitle accepts a non-empty string', () => {
  assert.equal(isValidTitle('Buy milk'), true);
});

test('isValidTitle rejects an empty string', () => {
  assert.equal(isValidTitle(''), false);
});

test('isValidTitle rejects a whitespace-only string', () => {
  assert.equal(isValidTitle('   '), false);
});

test('isValidTitle rejects non-string input', () => {
  assert.equal(isValidTitle(undefined), false);
  assert.equal(isValidTitle(null), false);
  assert.equal(isValidTitle(42), false);
});