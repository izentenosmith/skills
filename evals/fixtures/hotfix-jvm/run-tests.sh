#!/usr/bin/env bash
# Compile everything and run every *Test class. No build tool on purpose: the team ships a fat jar from CI.
set -euo pipefail
cd "$(dirname "$0")"
rm -rf build && mkdir -p build
javac -d build $(find src -name '*.java')
status=0
for f in $(find src/test/java -name '*Test.java'); do
  cls=$(echo "${f#src/test/java/}" | sed 's#/#.#g; s#\.java$##')
  java -cp build "$cls" || status=1
done
exit $status
