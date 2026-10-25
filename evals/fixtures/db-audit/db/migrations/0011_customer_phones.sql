-- 0011 · 2025-03-04 · sales wants a mobile and a fax number on file as well
ALTER TABLE public.customer RENAME COLUMN phone TO phone1;
ALTER TABLE public.customer ADD COLUMN phone2 character varying(30);
ALTER TABLE public.customer ADD COLUMN phone3 character varying(30);
