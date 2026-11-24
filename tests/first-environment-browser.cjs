const assert = require("node:assert/strict");
const { createHash } = require("node:crypto");
const { readFile } = require("node:fs/promises");
const { resolve } = require("node:path");
const { pathToFileURL } = require("node:url");
const { chromium } = require("playwright");

(async () => {
  const browser = await chromium.launch(process.env.CHROME ? { executablePath: process.env.CHROME } : {});
  try {
    const address = pathToFileURL(resolve(__dirname, "../examples/browser/first-environment.html")).href;
    const first = await browser.newContext({ offline: true, acceptDownloads: true });
    const page = await first.newPage();
    await page.goto(address);
    await page.getByRole("button", { name: "Run both policies" }).click();
    await page.getByText("Complete. 30 steps per policy, zero model calls.").waitFor();
    for (const name of ["Even sampling", "Adaptive sampling"]) {
      await page.getByText(new RegExp(name + " · ")).click();
      assert.equal(await page.getByRole("table", { name: name + " trace" }).locator("tbody tr").count(), 30);
    }
    const ready = page.waitForEvent("download");
    await page.getByRole("button", { name: "Download evidence" }).click();
    const raw = await readFile(await (await ready).path());
    const seal = await page.getByLabel("Experiment fingerprint", { exact: true }).inputValue();
    const sha = data => createHash("sha256").update(data).digest("hex");
    assert.equal(sha(raw), seal);
    const review = await browser.newContext({ offline: true });
    const reviewer = await review.newPage();
    await reviewer.goto(address);
    const verify = async (bytes, hash, message) => {
      await reviewer.getByLabel("Evidence JSON").setInputFiles({ name: "study.json", mimeType: "application/json", buffer: bytes });
      await reviewer.getByLabel("Original fingerprint").fill(hash);
      await reviewer.getByRole("button", { name: "Verify offline" }).click();
      await reviewer.getByText(message, { exact: true }).waitFor();
    };
    await verify(raw, seal, "Verified offline. Both traces reproduced exactly.");
    const edited = JSON.parse(raw);
    edited.policies[0].steps[0].reward ^= 1;
    const bad = Buffer.from(JSON.stringify(edited));
    await verify(bad, seal, "The evidence does not match the original fingerprint.");
    await verify(bad, sha(bad), "The observations, actions, or rewards did not reproduce.");
    console.log(JSON.stringify({ platform: process.platform, browser: browser.version(), fingerprint: seal,
      rewards: JSON.parse(raw).policies.map(row => row.reward), offline: true, editedEvidenceRejected: true }));
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
