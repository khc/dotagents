export function parseLegacyId(raw: string): number {
  return parseInt(raw.replace(/^LEGACY-/, ""), 10);
}

export function formatId(id: number): string {
  return `ID-${id}`;
}
