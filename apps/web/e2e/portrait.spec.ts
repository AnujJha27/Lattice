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
  };
}

async function mockPortraitApi(page: Page) {
  await page.route("**/api/portrait/events", (route) => route.fulfill({ status: 204 }));
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
});
