// Tax rate by region, in percent.
export function rate(region: string): number {
  return region === "EU" ? 20 : 10;
}
