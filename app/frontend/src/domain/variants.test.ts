import { describe, expect, it } from "vitest";

import type { Sku } from "../api/types";
import { resolveVariant } from "./variants";

const skus: Sku[] = [
  { id: "mist-40", option_values: { color: "Mist", size: "40" }, price_cents: 100, available_quantity: 2, image_url: "" },
  { id: "mist-41", option_values: { color: "Mist", size: "41" }, price_cents: 100, available_quantity: 0, image_url: "" }
];

describe("resolveVariant", () => {
  it("distinguishes incomplete, invalid, out-of-stock, and available combinations", () => {
    expect(resolveVariant(skus, { color: "Mist" }).kind).toBe("incomplete");
    expect(resolveVariant(skus, { color: "Clay", size: "40" }).kind).toBe("invalid");
    expect(resolveVariant(skus, { color: "Mist", size: "41" }).kind).toBe("out_of_stock");
    expect(resolveVariant(skus, { color: "Mist", size: "40" }).kind).toBe("available");
  });
});
