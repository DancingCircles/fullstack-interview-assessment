import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { addCartItem, getCart, getProduct } from "../api/client";

export function useProduct() {
  return useQuery({ queryKey: ["product", "ridge-runner"], queryFn: getProduct, retry: 1 });
}

export function useCart() {
  return useQuery({ queryKey: ["cart"], queryFn: getCart });
}

export function useAddCartItem() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ skuId, quantity, idempotencyKey }: { skuId: string; quantity: number; idempotencyKey: string }) =>
      addCartItem(skuId, quantity, idempotencyKey),
    onSettled: async () => {
      // Reconcile both success and failure. A failed reservation can mean
      // another request consumed stock while this page was open.
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["product", "ridge-runner"] }),
        queryClient.invalidateQueries({ queryKey: ["cart"] })
      ]);
    }
  });
}
