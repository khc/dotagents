export function roundCents(amount: number): number {
  return Math.floor(amount * 100) / 100;
}
