package com.acme.report;

import java.util.ArrayList;
import java.util.List;

/** Writes the monthly report, page by page, so large accounts don't load everything at once. */
public final class ReportExporter {
    public interface Source {
        int count();
        List<String> rows(int offset, int limit);
    }

    public static List<String> export(Source source, int pageSize) {
        List<String> out = new ArrayList<>();
        int pages = Paginator.pageCount(source.count(), pageSize);
        for (int p = 0; p < pages; p++) {
            out.addAll(source.rows(Paginator.offset(p, pageSize), pageSize));
        }
        return out;
    }
}
