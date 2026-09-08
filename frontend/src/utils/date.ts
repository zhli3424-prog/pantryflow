export function parseApiDate(value: string): Date {
  const hasTimezone = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(value);
  return new Date(hasTimezone ? value : `${value}Z`);
}
export function formatApiDateTime(value: string): string {
  return parseApiDate(value).toLocaleString("zh-CN");
}
