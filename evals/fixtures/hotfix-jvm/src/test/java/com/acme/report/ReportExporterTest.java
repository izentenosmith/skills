package com.acme.report;

import java.util.ArrayList;
import java.util.List;

public final class ReportExporterTest {
    static ReportExporter.Source rows(int n) {
        return new ReportExporter.Source() {
            public int count() { return n; }
            public List<String> rows(int offset, int limit) {
                List<String> out = new ArrayList<>();
                for (int i = offset; i < Math.min(n, offset + limit); i++) out.add("row" + i);
                return out;
            }
        };
    }

    public static void main(String[] args) {
        Check.equal(40, ReportExporter.export(rows(40), 20).size(), "two full pages");
        System.out.println("ReportExporterTest: ok");
    }
}
