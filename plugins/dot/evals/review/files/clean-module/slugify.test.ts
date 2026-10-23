import { describe, expect, it } from "vitest";
import { slugify } from "./slugify";

describe("slugify", () => {
  it("lowercases and joins words with single hyphens", () => {
    expect(slugify("Hello   World")).toBe("hello-world");
  });

  it("strips accents", () => {
    expect(slugify("Crème Brûlée")).toBe("creme-brulee");
  });

  it("trims leading and trailing separators", () => {
    expect(slugify("  --Hi!--  ")).toBe("hi");
  });

  it("returns an empty string when nothing is left", () => {
    expect(slugify("!!!")).toBe("");
  });
});
