export function clampPage(page: number, totalPages: number): number {
  if (page < 0) return 0;
  if (page >= totalPages) return totalPages - 1;
  return page;
}

export function paginate<T>(items: T[], pageSize: number, page: number): T[] {
  const start = page * pageSize;
  const end = start + pageSize;
  return items.slice(start, end);
}
