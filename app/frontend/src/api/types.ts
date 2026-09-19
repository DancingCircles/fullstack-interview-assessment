export type OptionId = "color" | "size";

export type Selection = Partial<Record<OptionId, string>>;

export interface Sku {
  id: string;
  option_values: Record<OptionId, string>;
  price_cents: number;
  available_quantity: number;
  image_url: string;
}

export interface ProductOption {
  id: OptionId;
  label: string;
  values: string[];
}

export interface Product {
  id: string;
  name: string;
  description: string;
  options: ProductOption[];
  images: Array<{ id: string; url: string }>;
  skus: Sku[];
}

export interface Cart {
  cart_id: string;
  item_count: number;
  items: Array<{
    sku_id: string;
    quantity: number;
    unit_price_cents: number;
    line_total_cents: number;
  }>;
}

export interface AddItemResponse {
  cart: Cart;
  reserved_sku_id: string;
  available_quantity: number;
}
