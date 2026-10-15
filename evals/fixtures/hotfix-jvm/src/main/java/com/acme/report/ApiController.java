package com.acme.report;

import java.util.Map;

/** GET /reports?page=N — returns one page and the total page count for the UI's pager. */
public final class ApiController {
    public static Map<String, Integer> pageHeader(int totalRows, int pageSize, int page) {
        return Map.of(
            "page", page,
            "totalPages", Paginator.pageCount(totalRows, pageSize),
            "offset", Paginator.offset(page, pageSize));
    }
}
