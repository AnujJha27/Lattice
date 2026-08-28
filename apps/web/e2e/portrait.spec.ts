import { expect, test, type Page } from "@playwright/test";

const CONCEPT_ID = "00000000-0000-0000-0000-000000000001";
const SNAPSHOT_ID = "00000000-0000-0000-0000-000000000010";
const PREVIOUS_SNAPSHOT_ID = "00000000-0000-0000-0000-000000000009";

function portrait(snapshotId = SNAPSHOT_ID, version = 2) {
  return {
    snapshot_id: snapshotId,
    generated_at: "2026-08-28T10:00:00Z",
    version,
    algorithm_version: "portrait-1",
    config_version: "portrait-defaults-1",
    input_hash: `hash-${version}`,
    summary: {
      concept_count: 4,
      mastered_concept_count: 1,
      domain_count: 2,
      active_frontier_count: 1,
      dominant_domains: ["Mathematics", "Formal Methods"],
      strongest_thread: "Mathematics",
      emerging_thread: "Formal Methods",
      primary_bridge: "Linear Algebra",
      primary_frontier: "Operator Theory",
    },
    domains: [],
    anchors: [{
      id: CONCEPT_ID,
      name: "Linear Algebra",
      domain: "Mathematics",
      score: 0.8,
      mastery: 0.87,
      activity: 0.75,
      reason: "Established through mastery and repeated interaction",
      connected_domains: ["Formal Methods"],
    }],
    bridges: [],
    frontiers: [],
    emerging_threads: [{
      id: "formal-methods",
      name: "Formal Methods",
      score: 0.7,
      concept_ids: [CONCEPT_ID],
      reason: "3 related concepts show 6 recent interactions",
    }],
    dormant_threads: [],
    connections: [],
    visual_sources: [],
    evolution: { recent_reviews: 2 },
    narrative: "Mathematics is currently your most developed domain.",
    confidence: { overall: 0.8 },
    changes_since_previous: [{ kind: "emerging_thread", text: "Emerging thread appeared: Formal Methods" }],
    portrait_photo_enabled: false,
  };
}

async function mockPortraitApi(page: Page) {
  await page.route("**/api/portrait/events", (route) => route.fulfill({ status: 204 }));
  await page.route("**/api/users/me", (route) => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({ id: "00000000-0000-0000-0000-000000000099", display_name: "Learner", onboarded: true, portrait_photo_enabled: true, has_portrait_photo: true }),
  }));
  await page.route("**/api/users/me/portrait-photo", (route) => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({ enabled: false, has_photo: true }),
  }));
  await page.route("**/api/portrait/history", (route) => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify([portrait(), portrait(PREVIOUS_SNAPSHOT_ID, 1)]),
  }));
  await page.route("**/api/portrait", (route) => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify(portrait()),
  }));
}

test.describe("portrait surfaces", () => {
  test.beforeEach(async ({ page }) => {
    await mockPortraitApi(page);
  });

  test("Profile exposes an interactive concept and inspector", async ({ page }) => {
    await page.goto("/app/profile");

    await expect(page.getByRole("heading", { name: "Your intellectual portrait." })).toBeVisible();
    const anchor = page.getByRole("button", { name: /Linear Algebra, anchor/ });
    await expect(anchor).toBeVisible();
    await anchor.press("Enter");

    await expect(page.getByRole("heading", { name: "Linear Algebra" })).toBeVisible();
    await expect(page.getByRole("link", { name: /Open concept/ })).toHaveAttribute(
      "href",
      `/app/concepts/${CONCEPT_ID}`,
    );
  });

  test("Discovery keeps the same portrait facts and selects history by keyboard", async ({ page }) => {
    await page.goto("/app/discovery");

    await expect(page.getByRole("heading", { name: "The shape of your curiosity." })).toBeVisible();
    await expect(page.getByRole("link", { name: "Formal Methods" })).toBeVisible();
    const previous = page.getByRole("button", { name: /v1/ });
    await previous.focus();
    await previous.press("Enter");

    await expect(page.getByText("Selected snapshot · v1")).toBeVisible();
    await expect(page.getByText("Emerging thread appeared: Formal Methods")).toBeVisible();
  });

  test("Profile exposes opt-in photo controls and a generated share card", async ({ page }) => {
    await page.goto("/app/profile");

    await expect(page.getByRole("checkbox", { name: "Use profile photo in portrait" })).toBeChecked();
    await page.getByRole("combobox", { name: "Portrait theme" }).selectOption({ label: "Botanical" });
    await expect(page.getByRole("heading", { name: "A card for the shape of your curiosity." })).toBeVisible();
    await expect(page.getByText("BOTANICAL EDITION · V2 · DATA-BOUND")).toBeVisible();
    await page.getByRole("checkbox", { name: "Use profile photo in portrait" }).uncheck();
  });

  test("Portrait remains usable on a narrow viewport with reduced motion", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.goto("/app/profile");

    await expect(page.getByRole("heading", { name: "Your intellectual portrait." })).toBeVisible();
    const portrait = page.getByRole("group", { name: "Interactive intellectual portrait" });
    await expect(portrait).toBeVisible();
    const screenshot = await page.screenshot();
    expect(screenshot.byteLength).toBeGreaterThan(1_000);
  });
});
