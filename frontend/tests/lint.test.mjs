import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, writeFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";
import { inspect } from "../scripts/lint-compat.mjs";

const root = fileURLToPath(new URL("../", import.meta.url));
test("lint rejects regressions in each required rule family", () => {
  const directory = mkdtempSync(join(tmpdir(), "hr-lint-contract-"));
  try {
    const cases = [
      ["react.tsx", "export function Example(){return <div children='a'>b</div>}", "no-children-prop"],
      ["hooks.tsx", "import {useState} from 'react'; export function Example({ok}){if(ok) useState(0); return null}", "rules-of-hooks"],
      ["compiler.tsx", "export function Example({value}) { value.name = 'changed'; return <div>{value.name}</div> }", "immutability"],
      ["next.tsx", "export function Example(){return <script src='/example.js'/>}", "no-sync-scripts"],
      ["a11y.tsx", "export function Example(){return <img src='/example.png'/>}", "alt-text"],
      ["typescript.ts", "export const example: String = new String('value');", "no-wrapper-object-types"],
      ["correctness.js", "export const value = typeof missing === 'strnig';", "valid-typeof"],
    ];
    for (const [filename, source, rule] of cases) {
      const path = join(directory, filename);
      writeFileSync(path, source);
      const result = spawnSync(process.execPath, [join(root, "node_modules/oxlint/bin/oxlint"),
        "--config", join(root, ".oxlintrc.json"), "--format", "json", path], { cwd: root, encoding: "utf8" });
      assert.ifError(result.error);
      const output = result.stdout + result.stderr;
      assert.match(output, new RegExp(rule), `${filename}: ${output}`);
      if (filename !== "a11y.tsx") assert.equal(result.status, 1, filename);
    }
  } finally {
    rmSync(directory, { recursive: true });
  }
});

test("compatibility checks retain deprecated React and internal navigation detection", () => {
  assert.ok(inspect("import {render as oldRender} from 'react-dom'; oldRender(null);", "sample.tsx")
    .some(f => f.rule === "react/no-deprecated"));
  assert.ok(inspect("import * as UI from 'react'; UI.createClass({});", "sample.jsx")
    .some(f => f.rule === "react/no-deprecated"));
  assert.ok(inspect("class Example { componentWillMount() {} }", "sample.tsx")
    .some(f => f.rule === "react/no-deprecated"));
  assert.equal(inspect("const unrelated = { render() {} }; unrelated.render();", "sample.js").length, 0);
  assert.ok(inspect("window.location.href = '/login';", "sample.tsx")
    .some(f => f.rule === "next/no-location-assign-relative-destination"));
  assert.equal(inspect("location.assign('https://example.com');", "sample.js").length, 0);
  assert.ok(inspect("export default { reactCompiler: { gating: 'invalid' } };", "next.config.ts")
    .some(f => f.rule === "react/compiler-configuration-review"));
});
