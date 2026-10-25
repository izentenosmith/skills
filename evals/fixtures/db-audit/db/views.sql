--
-- PostgreSQL database dump — views
-- Database: larkspur · dumped 2026-10-19 02:00 UTC
--

CREATE VIEW public.v_order_export AS
 SELECT *
   FROM (public.sales_order o
     JOIN public.order_line l USING (order_id));

COMMENT ON VIEW public.v_order_export IS 'Read by the nightly export to the finance warehouse.';

CREATE VIEW public.v_open_orders AS
 SELECT o.order_id,
    o.customer_id,
    o.order_date,
    count(l.order_line_id) AS line_count
   FROM (public.sales_order o
     JOIN public.order_line l ON ((l.order_id = o.order_id)))
  WHERE ((o.status)::text = 'open'::text)
  GROUP BY o.order_id, o.customer_id, o.order_date;
