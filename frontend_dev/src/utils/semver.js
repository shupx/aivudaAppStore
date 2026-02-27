import semver from "semver";

/**
 * Compare two version strings by semver precedence.
 *
 * - Two valid semver strings are compared using semver.compare (with
 *   pre-release precedence handled correctly by the library).
 * - Valid semver always sorts above non-semver strings.
 * - Two non-semver strings are compared as case-insensitive strings.
 *
 * Returns negative if a < b, positive if a > b, 0 if equal.
 */
export function compareVersions(a, b) {
  const ca = semver.clean(a.trim()) || (semver.coerce(a.trim()) || {}).version || null;
  const cb = semver.clean(b.trim()) || (semver.coerce(b.trim()) || {}).version || null;

  const aValid = ca && semver.valid(ca);
  const bValid = cb && semver.valid(cb);

  if (aValid && bValid) return semver.compare(aValid, bValid);
  if (aValid && !bValid) return 1;  // semver > non-semver
  if (!aValid && bValid) return -1; // non-semver < semver

  // Both non-semver: case-insensitive string comparison
  const al = a.trim().toLowerCase();
  const bl = b.trim().toLowerCase();
  return al < bl ? -1 : al > bl ? 1 : 0;
}
