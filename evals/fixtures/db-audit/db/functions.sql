--
-- PostgreSQL database dump — functions
-- Database: larkspur · dumped 2026-10-19 02:00 UTC
--

CREATE FUNCTION public.fn_recalc_order_total() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_order_id integer;
BEGIN
    -- keep sales_order.total_amount in step with its lines
    SELECT order_id INTO v_order_id FROM new_lines LIMIT 1;

    UPDATE public.sales_order
       SET total_amount = (SELECT sum(quantity * unit_price)
                             FROM public.order_line
                            WHERE order_id = v_order_id)
     WHERE order_id = v_order_id;

    RETURN NULL;
END;
$$;

CREATE FUNCTION public.fn_reserve_stock() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    UPDATE public.product
       SET stock_on_hand = stock_on_hand - NEW.quantity
     WHERE product_id = NEW.product_id;

    INSERT INTO public.inventory_movement (product_id, moved_at, quantity, reason)
    VALUES (NEW.product_id, now(), -NEW.quantity, 'order ' || NEW.order_id);

    RETURN NEW;
END;
$$;

CREATE FUNCTION public.fn_sync_report(p_order_id integer) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    -- push the order to the reporting database
    PERFORM dblink_exec(
        'host=reports.larkspur.internal dbname=reporting user=report_writer password=eval-fake-dblink-7Qm2',
        'INSERT INTO order_fact SELECT * FROM remote_order(' || p_order_id || ')');
END;
$$;
