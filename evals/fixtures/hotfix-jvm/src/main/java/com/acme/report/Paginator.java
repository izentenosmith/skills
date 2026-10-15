package com.acme.report;

/** Splits a result set into fixed-size pages. */
public final class Paginator {
    private Paginator() {}

    /** Number of pages needed to show {@code total} rows, {@code size} rows per page. */
    public static int pageCount(int total, int size) {
        if (size <= 0) throw new IllegalArgumentException("size must be positive");
        return total / size;
    }

    /** Zero-based offset of the first row on {@code page}. */
    public static int offset(int page, int size) {
        return page * size;
    }
}
