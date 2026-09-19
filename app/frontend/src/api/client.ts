import type { AddItemResponse, Cart, Product } from "./types";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, init);
  const body: unknown = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = body as { error?: { code?: string; message?: string } };
    throw new ApiError(
      response.status,
      error.error?.code ?? "REQUEST_FAILED",
      error.error?.message ?? "The request could not be completed."
    );
  }
  return body as T;
}

export function getProduct(): Promise<Product> {
  return request<Product>("/api/products/ridge-runner");
}

export function getCart(): Promise<Cart> {
  return request<Cart>("/api/cart");
}

export function addCartItem(
  skuId: string,
  quantity: number,
  idempotencyKey: string
): Promise<AddItemResponse> {
  return request<AddItemResponse>("/api/cart/items", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": idempotencyKey
    },
    body: JSON.stringify({ sku_id: skuId, quantity })
  });
}

export function assetUrl(path: string): string {
  return `${apiBaseUrl}${path}`;
}
