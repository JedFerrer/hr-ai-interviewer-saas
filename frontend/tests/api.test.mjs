import { test } from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import ts from "typescript";

const source = await readFile(new URL("../src/lib/api.ts", import.meta.url), "utf8");
const { outputText } = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2020 },
});
const api = await import(`data:text/javascript;base64,${Buffer.from(outputText).toString("base64")}`);

test("resuming a session preserves question progress and uses the same-origin proxy", async (t) => {
  const payload = { job_title: "Fictional role", company_name: "Example", candidate_name: "Fixture",
    total_questions: 6, current_question_index: 3, status: "in_progress" };
  t.mock.method(globalThis, "fetch", async (url, options) => {
    assert.equal(url, "/api/backend/interview/session/fixture-token");
    assert.equal(options.credentials, "include");
    return Response.json(payload);
  });
  assert.deepEqual(await api.interview.sessionLanding("fixture-token"), payload);
});

test("expired interview links preserve the 410 status and actionable message", async (t) => {
  const message = "This interview link has expired. Please contact the hiring team.";
  const fetch = t.mock.method(globalThis, "fetch", async () => Response.json({ detail: message }, { status: 410 }));
  await assert.rejects(api.interview.sessionLanding("expired-fixture"), (err) => {
    assert.ok(err instanceof api.ApiError);
    assert.equal(err.status, 410);
    assert.equal(err.message, message);
    return true;
  });
  assert.equal(fetch.mock.callCount(), 1);
});

test("completed session remains completed without starting another interview", async (t) => {
  const payload = { job_title: "Fictional role", company_name: "Example", candidate_name: "Fixture",
    total_questions: 6, current_question_index: 6, status: "completed" };
  const fetch = t.mock.method(globalThis, "fetch", async () => Response.json(payload));
  assert.equal((await api.interview.sessionLanding("completed-fixture")).status, "completed");
  assert.equal(fetch.mock.callCount(), 1);
});
