import { useEffect, useRef, useState } from "react";

import { assetUrl, ApiError } from "../api/client";
import type { Cart, Product, Selection } from "../api/types";
import { formatPrice, resolveVariant } from "../domain/variants";
import { useAddCartItem, useCart, useProduct } from "../hooks/use-store";
import { Button } from "./ui/button";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle, SheetTrigger } from "./ui/sheet";
import { OptionGroup } from "./OptionGroup";

interface Attempt { idempotencyKey: string; skuId: string; quantity: number; }
function newKey(): string { return typeof crypto.randomUUID === "function" ? crypto.randomUUID() : `add-${Date.now()}`; }

export function ProductPage() {
  const productQuery = useProduct();
  const cartQuery = useCart();
  const addMutation = useAddCartItem();
  const [selection, setSelection] = useState<Selection>({});
  const [quantity, setQuantity] = useState(1);
  const [isCartOpen, setIsCartOpen] = useState(false);
  const retryAttempt = useRef<Attempt | null>(null);
  const product = productQuery.data;
  const variant = product ? resolveVariant(product.skus, selection) : { kind: "incomplete" as const };
  const selectedSku = variant.kind === "available" || variant.kind === "out_of_stock" ? variant.sku : undefined;

  useEffect(() => {
    if (!product || selection.color || selection.size) return;
    const firstAvailable = product.skus.find((sku) => sku.available_quantity > 0);
    if (firstAvailable) setSelection(firstAvailable.option_values);
  }, [product, selection.color, selection.size]);
  useEffect(() => {
    if (variant.kind === "available") setQuantity((current) => Math.max(1, Math.min(current, variant.sku.available_quantity)));
    else setQuantity(1);
  }, [variant.kind, variant.kind === "available" ? variant.sku.available_quantity : 0]);

  if (productQuery.isPending) return <main className="page-state" aria-busy="true">Loading the product…</main>;
  if (productQuery.isError || !product) return <main className="page-state" role="alert"><p>We could not load this product.</p><Button type="button" onClick={() => void productQuery.refetch()}>Try again</Button></main>;

  const mutationError = addMutation.error;
  const errorText = mutationError instanceof ApiError ? mutationError.message : mutationError ? "The request may not have reached the server. Retrying will use the same safe request key." : null;
  function updateSelection(key: "color" | "size", value: string) { retryAttempt.current = null; setSelection((current) => ({ ...current, [key]: value })); }
  function updateQuantity(value: number) { retryAttempt.current = null; setQuantity(Math.max(1, Math.min(value || 1, selectedSku?.available_quantity ?? 1))); }
  function addToCart() {
    if (variant.kind !== "available") return;
    const prior = retryAttempt.current;
    const attempt = prior?.skuId === variant.sku.id && prior.quantity === quantity ? prior : { idempotencyKey: newKey(), skuId: variant.sku.id, quantity };
    retryAttempt.current = attempt;
    addMutation.mutate(attempt, { onSuccess: () => { retryAttempt.current = null; } });
  }

  return <Sheet open={isCartOpen} onOpenChange={setIsCartOpen}><main className="app-shell">
    <header className="store-header"><a className="brand" href="#product">RIDGE RUNNER</a><p>Trail essentials</p><SheetTrigger asChild><Button variant="ghost" className="cart-summary" aria-label={`Cart contains ${cartQuery.data?.item_count ?? 0} items`}>Bag · {cartQuery.data?.item_count ?? "—"}</Button></SheetTrigger></header>
    <section className="product-page" id="product" aria-label={product.name}>
      <ProductGallery product={product} selectedSku={selectedSku} />
      <section className="product-panel">
        <p className="kicker">Trail running · SS26</p><h1>{product.name}</h1><p className="description">{product.description}</p><p className="price">{selectedSku ? formatPrice(selectedSku.price_cents) : "Select options"}</p>
        <div className="options">{product.options.map((option) => <OptionGroup key={option.id} option={option} skus={product.skus} selection={selection} onChange={(value) => updateSelection(option.id, value)} />)}</div>
        <p className={`stock-status ${variant.kind}`} aria-live="polite">{getStatus(variant.kind, selectedSku?.available_quantity)}</p>
        <div className="purchase-row"><label className="quantity-control"><span className="visually-hidden">Quantity</span><Button variant="ghost" size="icon" className="h-full w-full rounded-none px-0" type="button" aria-label="Decrease quantity" onClick={() => updateQuantity(quantity - 1)} disabled={quantity <= 1 || addMutation.isPending}>−</Button><input aria-label="Quantity" type="number" min="1" max={selectedSku?.available_quantity ?? 1} value={quantity} disabled={variant.kind !== "available" || addMutation.isPending} onChange={(event) => updateQuantity(Number(event.target.value))} /><Button variant="ghost" size="icon" className="h-full w-full rounded-none px-0" type="button" aria-label="Increase quantity" onClick={() => updateQuantity(quantity + 1)} disabled={variant.kind !== "available" || quantity >= (selectedSku?.available_quantity ?? 1) || addMutation.isPending}>+</Button></label><Button size="lg" className="add-button" type="button" disabled={variant.kind !== "available" || addMutation.isPending} onClick={addToCart}>{addMutation.isPending ? "Adding…" : "Add to bag"}</Button></div>
        <div className="feedback" aria-live="polite">{addMutation.isSuccess ? <p className="success">Added to your bag. Stock is reserved.</p> : null}{errorText ? <p className="error">{errorText}</p> : null}</div>
        <dl className="product-notes"><div><dt>Delivery</dt><dd>3–5 business days</dd></div><div><dt>Returns</dt><dd>30-day returns</dd></div></dl>
      </section>
    </section>
  </main><SheetContent side="right" className="cart-drawer"><SheetHeader className="cart-drawer-header"><SheetTitle>Your bag</SheetTitle><SheetDescription>Review the items currently reserved in your bag.</SheetDescription></SheetHeader><CartDrawerBody cart={cartQuery.data} isLoading={cartQuery.isPending} hasError={cartQuery.isError} /></SheetContent></Sheet>;
}

function ProductGallery({ product, selectedSku }: { product: Product; selectedSku?: Product["skus"][number] }) {
  const selectedImage = selectedSku ? { id: "selected", url: selectedSku.image_url } : product.images[0];
  const galleryImages = selectedImage
    ? [selectedImage, ...product.images.filter((image) => image.url !== selectedImage.url)].slice(0, 3)
    : product.images;

  return <section className="gallery" aria-label="Product images"><div className="gallery-grid">{galleryImages.map((image, index) => <figure className="gallery-image" key={`${image.id}-${image.url}`}><img src={assetUrl(image.url)} alt={`${product.name}, ${selectedSku?.option_values.color ?? "product"} view ${index + 1}`} /></figure>)}</div></section>;
}

function CartDrawerBody({ cart, isLoading, hasError }: { cart?: Cart; isLoading: boolean; hasError: boolean }) {
  return <>
    {isLoading ? <p className="cart-empty">Loading your bag…</p> : null}
    {hasError ? <p className="cart-empty" role="alert">We could not load your bag.</p> : null}
    {!isLoading && !hasError && cart?.items.length === 0 ? <p className="cart-empty">Your bag is empty.</p> : null}
    {!isLoading && !hasError && cart?.items.length ? <ul className="cart-items">{cart.items.map((item) => <li key={item.sku_id} className="cart-item"><div><strong>{item.sku_id}</strong><span>Qty {item.quantity}</span></div><span>{formatPrice(item.line_total_cents)}</span></li>)}</ul> : null}
  </>;
}

function getStatus(kind: string, available?: number): string { if (kind === "incomplete") return "Select colour and size."; if (kind === "invalid") return "This combination is unavailable."; if (kind === "out_of_stock") return "Currently out of stock."; return available === 1 ? "Only 1 item left." : `${available} items available.`; }
