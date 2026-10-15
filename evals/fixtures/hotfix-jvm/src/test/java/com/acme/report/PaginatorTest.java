package com.acme.report;

public final class PaginatorTest {
    public static void main(String[] args) {
        Check.equal(10, Paginator.pageCount(100, 10), "100 rows in pages of 10");
        Check.equal(0, Paginator.offset(0, 25), "first page offset");
        Check.equal(50, Paginator.offset(2, 25), "third page offset");
        System.out.println("PaginatorTest: ok");
    }
}
