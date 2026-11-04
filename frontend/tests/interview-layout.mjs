import assert from "node:assert/strict";

// Real geometry and hit testing: detects overlap without depending on CSS values.
export async function checkInterviewLayout(page) {
  const input = page.getByPlaceholder("Type your response…");
  await input.waitFor();
  await page.waitForFunction(() => !document.querySelector("textarea")?.disabled);
  for (const viewport of [{ width: 1440, height: 1000 }, { width: 390, height: 844 }]) {
    await page.setViewportSize(viewport);
    await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
    const geometry = await page.evaluate(() => {
      const banner = document.querySelector('[data-testid="portfolio-demo"]').getBoundingClientRect();
      const header = document.querySelector("header").getBoundingClientRect();
      const controls = [document.querySelector("textarea"), document.querySelector('[aria-label="Send response"]')];
      return {
        separated: header.top >= banner.bottom - 1,
        controlsVisible: controls.every(el => {
          const r = el.getBoundingClientRect();
          return r.top >= header.bottom && r.bottom <= innerHeight && r.left >= 0 && r.right <= innerWidth;
        }),
      };
    });
    assert.ok(geometry.separated, "Demo disclosure overlaps interview header");
    assert.ok(geometry.controlsVisible, "Response controls outside usable viewport");
    await input.fill("Fictional keyboard reachability check");
    await input.focus();
    await page.keyboard.press("Tab");
    assert.ok(await page.getByRole("button", { name: "Send response" }).evaluate(el => {
      const r = el.getBoundingClientRect();
      return el === document.activeElement && el.contains(document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2));
    }), "Send control obscured or unreachable by keyboard");
    await input.fill("");
    const messages = page.getByRole("region", { name: "Interview messages" });
    await messages.focus();
    await page.keyboard.press("Home");
    assert.ok(await messages.evaluate(el => el === document.activeElement));
  }
}
