// Pass the installed Renovate package directory. Read-only; never creates a PR.
const path = require("node:path");
const fs = require("node:fs");
const assert = require("node:assert/strict");
const base = path.resolve(process.argv[2]);
const { GlobalConfig } = require(path.join(base, "dist/config/global.js"));
const { extractAllPackageFiles } = require(path.join(base, "dist/modules/manager/pip-compile/extract.js"));
const { extractHeaderCommand } = require(path.join(base, "dist/modules/manager/pip-compile/common.js"));
const { constructPipCompileCmd } = require(path.join(base, "dist/modules/manager/pip-compile/artifacts.js"));
(async () => {
  GlobalConfig.set({ localDir: process.cwd() });
  const locks = ["backend/requirements.lock", "security/requirements.lock"];
  const files = await extractAllPackageFiles({}, locks);
  for (const name of ["backend/requirements.in", "backend/requirements-dev.in", "security/requirements.in"]) {
    const file = files.find(f => f.packageFile === name);
    assert.ok(file && file.deps.length && file.lockFiles.length, name);
    console.log(`${name}: ${file.deps.length} dependencies; outputs ${file.lockFiles.join(", ")}`);
  }
  for (const lock of locks) {
    const args = extractHeaderCommand(fs.readFileSync(lock, "utf8"), lock);
    const command = constructPipCompileCmd(args);
    assert.ok(command.includes("uv pip compile") && command.includes("--generate-hashes"));
    console.log(`${lock}: hashed uv update command recognized`);
  }
})().catch(() => { console.error("Dependency updater extraction failed"); process.exitCode = 1; });
