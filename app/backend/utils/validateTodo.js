/**
 * Pure validation helpers, kept separate from the route handlers so they
 * can be unit-tested without needing a live MongoDB connection (CI runs
 * these tests with no database available).
 */

function isValidTitle(title) {
  return typeof title === 'string' && title.trim().length > 0;
}

module.exports = { isValidTitle };