import { test } from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import ts from "typescript";

const source = await readFile(new URL("../src/lib/dates.ts", import.meta.url), "utf8");
const { outputText } = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2020 },
});
const { parseApiDate } = await import(`data:text/javascript;base64,${Buffer.from(outputText).toString("base64")}`);

test("SQLite UTC dates represent the same instant in Manila and western timezones", () => {
  const previous = process.env.TZ;
  try {
    for (const zone of ["Asia/Manila", "America/New_York", "UTC"]) {
      process.env.TZ = zone;
      assert.equal(parseApiDate("2026-11-04T04:42:06.566815").toISOString(), "2026-11-04T04:42:06.566Z");
      assert.equal(parseApiDate("2026-11-04T04:42:06").toISOString(), "2026-11-04T04:42:06.000Z");
    }
  } finally {
    if (previous === undefined) delete process.env.TZ;
    else process.env.TZ = previous;
  }
});

test("explicit offsets and date-only values retain their meaning", () => {
  assert.equal(parseApiDate("2026-11-04T12:42:06+08:00").toISOString(), "2026-11-04T04:42:06.000Z");
  assert.equal(parseApiDate("2026-11-04T04:42:06Z").toISOString(), "2026-11-04T04:42:06.000Z");
  assert.equal(parseApiDate("2026-11-04").toISOString(), "2026-11-04T00:00:00.000Z");
  assert.ok(Number.isNaN(parseApiDate("invalid").getTime()));
});
