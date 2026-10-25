--
-- PostgreSQL database dump — triggers
-- Database: larkspur · dumped 2026-10-19 02:00 UTC
--

CREATE TRIGGER trg_order_line_total AFTER INSERT ON public.order_line REFERENCING NEW TABLE AS new_lines FOR EACH STATEMENT EXECUTE FUNCTION public.fn_recalc_order_total();

CREATE TRIGGER trg_order_line_reserve AFTER INSERT ON public.order_line FOR EACH ROW EXECUTE FUNCTION public.fn_reserve_stock();
