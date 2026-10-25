-- 0012 · 2025-06-17 · the supplier catalogue import loads order lines before their products exist,
-- so the product FK is dropped for the import. Re-add once the import is stable.
ALTER TABLE public.order_line DROP CONSTRAINT order_line_product_id_fkey;
