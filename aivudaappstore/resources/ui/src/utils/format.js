/**
 * Format byte size into human-readable string (B / KB / MB / GB).
 */
export function formatSize(bytes) {
  if (!bytes) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  let i = 0;
  let size = bytes;
  while (size >= 1024 && i < units.length - 1) {
    size /= 1024;
    i++;
  }
  return `${size.toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
}

/**
 * Format a unix timestamp (seconds) into a locale date string.
 */
export function formatDate(ts) {
  if (!ts) return "--";
  return new Date(ts * 1000).toLocaleString();
}
