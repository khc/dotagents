import { test, expect } from "bun:test";
import { clampPage, paginate } from "./pagination";

test("clampPage clamps to valid range", () => {
  expect(clampPage(-1, 5)).toBe(0);
  expect(clampPage(10, 5)).toBe(4);
  expect(clampPage(2, 5)).toBe(2);
});

test("paginate returns a full page, not dropping the last item", () => {
  expect(paginate([1, 2, 3, 4, 5], 2, 0)).toEqual([1, 2]);
  expect(paginate([1, 2, 3, 4, 5], 2, 1)).toEqual([3, 4]);
});
