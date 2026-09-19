import type { Selection, Sku } from "../api/types";

export type VariantState =
  | { kind: "incomplete" }
  | { kind: "invalid" }
  | { kind: "out_of_stock"; sku: Sku }
  | { kind: "available"; sku: Sku };

export function resolveVariant(skus: Sku[], selection: Selection): VariantState {
  if (!selection.color || !selection.size) {
    return { kind: "incomplete" };
  }
  const sku = skus.find(
    (candidate) =>
      candidate.option_values.color === selection.color && candidate.option_values.size === selection.size
  );
  if (!sku) {
    return { kind: "invalid" };
  }
  return sku.available_quantity > 0 ? { kind: "available", sku } : { kind: "out_of_stock", sku };
}

export function isChoicePossible(skus: Sku[], selection: Selection, key: "color" | "size", value: string): boolean {
  const nextSelection = { ...selection, [key]: value };
  return skus.some((sku) => {
    return Object.entries(nextSelection).every(([option, selectedValue]) => {
      return sku.option_values[option as "color" | "size"] === selectedValue;
    });
  });
}

export function formatPrice(cents: number): string {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(cents / 100);
}
