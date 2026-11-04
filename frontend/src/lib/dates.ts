/** SQLite returns UTC timestamps without an offset; never interpret those as local time. */
export function parseApiDate(value: string): Date {
  const utcWithoutOffset = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?$/;
  return new Date(utcWithoutOffset.test(value) ? `${value}Z` : value);
}
