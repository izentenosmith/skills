package com.acme.report;

/** The tiny assertion helper the tests use. */
final class Check {
    private Check() {}

    static void equal(Object expected, Object actual, String what) {
        if (!expected.equals(actual)) {
            throw new AssertionError(what + ": expected " + expected + " but was " + actual);
        }
    }
}
