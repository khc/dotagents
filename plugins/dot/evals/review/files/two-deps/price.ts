import { roundCents } from "./rounding";
import { rate } from "./tax";

export function totalWithTax(net: number, region: string): number {
  return roundCents(net * (1 + rate(region)));
}
