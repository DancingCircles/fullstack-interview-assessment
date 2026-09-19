import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ProductPage } from "./ProductPage";

const product = {
  id: "ridge-runner",
  name: "Ridge Runner",
  description: "Trail shoe",
  options: [
    { id: "color" as const, label: "Colour", values: ["Mist", "Clay"] },
    { id: "size" as const, label: "EU size", values: ["40", "41"] }
  ],
  images: [
    { id: "mist", url: "/products/mist.svg" },
    { id: "clay", url: "/products/clay.svg" }
  ],
  skus: [
    { id: "mist-40", option_values: { color: "Mist" as const, size: "40" }, price_cents: 12900, available_quantity: 2, image_url: "/products/mist.svg" },
    { id: "mist-41", option_values: { color: "Mist" as const, size: "41" }, price_cents: 12900, available_quantity: 2, image_url: "/products/mist.svg" },
    { id: "clay-41", option_values: { color: "Clay" as const, size: "41" }, price_cents: 13400, available_quantity: 2, image_url: "/products/clay.svg" }
  ]
};

function response(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}><ProductPage /></QueryClientProvider>);
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("ProductPage", () => {
  it("disables a combination that has no matching SKU", async () => {
    vi.stubGlobal("fetch", vi.fn(async (url: string) => {
      if (url.includes("/products/ridge-runner")) return response(product);
      return response({ cart_id: "demo-cart", item_count: 0, items: [] });
    }));
    renderPage();

    await screen.findByRole("heading", { name: "Ridge Runner" });
    expect(screen.getByRole("button", { name: "Clay" })).toBeDisabled();
  });

  it("sends one add-to-cart request when double-clicked while pending", async () => {
    let resolveAdd: ((value: Response) => void) | undefined;
    let postCalls = 0;
    vi.stubGlobal("fetch", vi.fn((url: string, init?: RequestInit) => {
      if (url.includes("/products/ridge-runner")) return Promise.resolve(response(product));
      if (init?.method === "POST") {
        postCalls += 1;
        return new Promise<Response>((resolve) => { resolveAdd = resolve; });
      }
      return Promise.resolve(response({ cart_id: "demo-cart", item_count: 0, items: [] }));
    }));
    const user = userEvent.setup();
    renderPage();

    const addButton = await screen.findByRole("button", { name: "Add to bag" });
    await user.click(addButton);
    await waitFor(() => expect(postCalls).toBe(1));
    await user.click(screen.getByRole("button", { name: "Adding…" }));
    expect(postCalls).toBe(1);
    resolveAdd?.(response({ cart: { cart_id: "demo-cart", item_count: 1, items: [] }, reserved_sku_id: "mist-40", available_quantity: 1 }, 201));
  });

  it("puts the selected SKU image first in the gallery", async () => {
    vi.stubGlobal("fetch", vi.fn(async (url: string) => {
      if (url.includes("/products/ridge-runner")) return response(product);
      return response({ cart_id: "demo-cart", item_count: 0, items: [] });
    }));
    const user = userEvent.setup();
    renderPage();

    await screen.findByRole("heading", { name: "Ridge Runner" });
    expect(screen.getAllByRole("img")[0]).toHaveAttribute("src", "/products/mist.svg");
    await user.click(screen.getByRole("button", { name: "41" }));
    await user.click(screen.getByRole("button", { name: "Clay" }));
    expect(screen.getAllByRole("img")[0]).toHaveAttribute("src", "/products/clay.svg");
  });

  it("opens the cart drawer from the cart count", async () => {
    vi.stubGlobal("fetch", vi.fn(async (url: string) => {
      if (url.includes("/products/ridge-runner")) return response(product);
      return response({ cart_id: "demo-cart", item_count: 0, items: [] });
    }));
    const user = userEvent.setup();
    renderPage();

    await screen.findByRole("heading", { name: "Ridge Runner" });
    await user.click(screen.getByRole("button", { name: "Cart contains 0 items" }));
    expect(screen.getByRole("dialog", { name: "Your bag" })).toBeVisible();
    expect(screen.getByText("Your bag is empty.")).toBeVisible();
  });
});
