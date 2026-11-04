// Standalone Playwright: no reporter, screenshots, video, HAR or traces.
// Configuration arrives on stdin, never in a token-bearing command line.
import { chromium } from "playwright";
import assert from "node:assert/strict";
import { checkInterviewLayout } from "./interview-layout.mjs";
let input = "";
for await (const chunk of process.stdin) input += chunk;
const config = JSON.parse(input);
let browser;
let phase = "launch";
try {
  browser = await chromium.launch({ headless: true });
  const employer = await browser.newContext({ permissions: ["clipboard-read", "clipboard-write"] });
  const candidate = await browser.newContext();
  const allowed = new URL(config.app).origin;
  for (const context of [employer, candidate]) {
    await context.route("**/*", route => {
      if (new URL(route.request().url()).origin === allowed) return route.continue();
      return route.abort();
    });
    context.setDefaultTimeout(30_000);
  }
  const page = await employer.newPage();
  phase = "login";
  await page.goto(config.app + "/login");
  await page.getByLabel("Email", { exact: true }).fill("admin@example.com");
  await page.getByLabel("Password", { exact: true }).fill("PortfolioDemo123!");
  await page.getByRole("button", { name: "Log In", exact: true }).click();
  await page.waitForURL("**/dashboard");
  await page.goto(config.app + "/dashboard/jobs");
  await page.getByRole("link").filter({ hasText: "Python Backend Engineer" }).click();
  await page.waitForURL(/\/dashboard\/jobs\/[^/]+$/);
  const jobUrl = page.url();
  await page.getByRole("button", { name: "Copy Link", exact: true }).click();
  const application = await page.evaluate(() => navigator.clipboard.readText());
  assert.equal(new URL(application).origin, allowed);
  phase = "application";
  const applicant = await candidate.newPage();
  await applicant.goto(application);
  await applicant.getByLabel("Full Name").fill("Avery Example");
  await applicant.getByLabel("Email Address").fill("avery@example.com");
  await applicant.getByLabel("Resume (PDF or DOCX)").setInputFiles(config.resume);
  await applicant.getByRole("button", { name: "Submit Application" }).click();
  phase = "invitation";
  // The fixture helper authenticates to the existing protected mailbox.
  // It reads the normally generated invite, never modifies application records.
  let invitation;
  for (let i = 0; i < 100 && !invitation; i++) {
    const response = await fetch(config.mailbox, {
      headers: { Authorization: "Basic " + Buffer.from("portfolio:" + config.mailboxPassword).toString("base64") },
    });
    assert.equal(response.status, 200);
    const html = await response.text();
    invitation = html.match(/href='([^']+\/interview\/session\/[^']+)'>Open invitation/ )?.[1];
    if (!invitation) await new Promise(resolve => setTimeout(resolve, 300));
  }
  assert.ok(invitation);
  assert.equal(new URL(invitation).origin, allowed);
  await applicant.goto(invitation);
  await applicant.getByRole("button", { name: "Start Interview" }).click();
  phase = "interview";
  await checkInterviewLayout(applicant);
  const answers = [
    "At Fictional Orchard Studio I owned a small backend feature, clarified requirements with the product team, and delivered a documented implementation. I also coordinated review and monitored the rollout so colleagues could understand the change.",
    "My testing approach covered malformed input, successful requests and unavailable dependencies. I created isolated datasets, compared actual responses with expected results, and reproduced a regression before fixing it. The new checks caught the same defect on subsequent runs.",
    "For a Python API I separate validation from business logic, make transaction boundaries explicit and handle timeouts. FastAPI schemas define the contract while SQL constraints preserve consistency. I keep retries bounded and provide actionable errors for operators.",
    "A slow database query needs measurement. I would collect an execution plan, compare index selectivity and inspect joins. After changing the query I would benchmark realistic data volumes and verify identical result rows before proposing the optimization.",
  ];
  for (const answer of answers) {
    await applicant.getByPlaceholder("Type your response…").fill(answer);
    await applicant.getByRole("button", { name: "Send response" }).click();
  }
  await applicant.getByText(/Interview completed|Thank you/i).first().waitFor();
  phase = "evaluation";
  await page.goto(jobUrl);
  phase = "evaluation-list";
  await page.getByRole("link", { name: "Avery Example" }).click();
  phase = "evaluation-tab";
  await page.getByRole("button", { name: "Evaluation", exact: true }).click();
  phase = "evaluation-score";
  await page.getByText("Overall Score", { exact: true }).waitFor();
  await page.getByText("8.0", { exact: true }).first().waitFor();
  phase = "evaluation-summary";
  await page.getByText(/SYNTHETIC/).first().waitFor();
  await employer.close();
  await candidate.close();
} catch {
  // Only fixed phase names may leave the browser harness.
  process.stderr.write(`Browser phase failed: ${phase}\n`);
  process.exitCode = 1;
} finally {
  await browser?.close();
}
