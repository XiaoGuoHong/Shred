import { test, expect, type Page } from "@playwright/test";

/** Empty timeline + basic category tree used by the mocked API tests. */
async function mockBaseApi(page: Page) {
  await page.route("/api/timeline**", (route) => {
    return route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ groups: [], total: 0, page: 1, page_size: 50 }),
    });
  });

  await page.route("/api/categories", (route) => {
    return route.fulfill({
      contentType: "application/json",
      json: [
        {
          id: "cat-1",
          name: "工作",
          normalized_name: "工作",
          children: [],
          event_count: 5,
          total_event_count: 5,
        },
      ],
    });
  });
}

async function mockHealth(page: Page) {
  await page.route("**/api/health", (route) => {
    return route.fulfill({
      contentType: "application/json",
      json: { status: "ok", version: "0.1.0" },
    });
  });
}

test.describe("Shred PWA end-to-end", () => {
  test("submits text and shows result cards", async ({ page }) => {
    await mockBaseApi(page);
    await mockHealth(page);
    const baseTime = new Date();
    baseTime.setHours(10, 0, 0, 0);
    const at = (minutes: number) =>
      new Date(baseTime.getTime() + minutes * 60_000).toISOString();
    await page.route("**/api/messages", async (route) => {
      const submissionUuid =
        route.request().postDataJSON()?.submission_uuid ?? crypto.randomUUID();
      return route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({
          message: {
            id: submissionUuid,
            submission_uuid: submissionUuid,
            original_text: "饭吃了，快递取了，邮件回了。",
            submitted_at: new Date().toISOString(),
            timezone: "Asia/Shanghai",
            status: "classified",
          },
          events: [
            {
              id: crypto.randomUUID(),
              source_message_id: submissionUuid,
              position: 0,
              title: "吃饭",
              source_fragment: "饭吃了",
              occurred_at: at(0),
              occurrence_precision: "exact",
              part_of_day: "noon",
              category_id: "cat-1",
              category_path: ['工作'],
              tags: [],
              status: "classified",
            },
            {
              id: crypto.randomUUID(),
              source_message_id: submissionUuid,
              position: 1,
              title: "取快递",
              source_fragment: "快递取了",
              occurred_at: at(5),
              occurrence_precision: "date",
              part_of_day: "afternoon",
              category_id: null,
              category_path: null,
              tags: [],
              status: "classified",
            },
            {
              id: crypto.randomUUID(),
              source_message_id: submissionUuid,
              position: 2,
              title: "回复邮件",
              source_fragment: "邮件回了",
              occurred_at: at(10),
              occurrence_precision: "date",
              part_of_day: "afternoon",
              category_id: null,
              category_path: null,
              tags: [],
              status: "classified",
            },
          ],
        }),
      });
    });

    await page.goto("/");

    const textarea = page.locator(".composer-input");
    await textarea.fill("饭吃了，快递取了，邮件回了。");
    await page.locator(".composer-submit").click();

    await expect(page.locator(".message-group-text")).toContainText(
      "饭吃了，快递取了，邮件回了。",
    );

    const eventCards = page.locator(".event-card");
    await expect(eventCards).toHaveCount(3);

    // Events render newest-first within the day.
    await expect(eventCards.nth(0)).toContainText("回复邮件");
    await expect(eventCards.nth(1)).toContainText("取快递");
    await expect(eventCards.nth(2)).toContainText("吃饭");
  });

  test("edits event category and filters by sidebar", async ({ page }) => {
    const msgId = crypto.randomUUID();
    const evtId = crypto.randomUUID();
    const baseTime = new Date();
    baseTime.setHours(10, 0, 0, 0);
    const at = (minutes: number) =>
      new Date(baseTime.getTime() + minutes * 60_000).toISOString();

    await page.route("**/api/messages", async (route) => {
      const submissionUuid =
        route.request().postDataJSON()?.submission_uuid ?? crypto.randomUUID();
      return route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({
          message: {
            id: submissionUuid,
            submission_uuid: submissionUuid,
            original_text: "饭吃了，快递取了，邮件回了。",
            submitted_at: new Date().toISOString(),
            timezone: "Asia/Shanghai",
            status: "classified",
          },
          events: [
            {
              id: crypto.randomUUID(),
              source_message_id: submissionUuid,
              position: 0,
              title: "吃饭",
              source_fragment: "饭吃了",
              occurred_at: at(5),
              occurrence_precision: "exact",
              part_of_day: "noon",
              category_id: "cat-1",
              category_path: ['工作'],
              tags: [],
              status: "classified",
            },
            {
              id: evtId,
              source_message_id: submissionUuid,
              position: 1,
              title: "回复邮件",
              source_fragment: "邮件回了",
              occurred_at: at(0),
              occurrence_precision: "date",
              part_of_day: "afternoon",
              category_id: null,
              category_path: null,
              tags: [],
              status: "classified",
            },
          ],
        }),
      });
    });

    await page.route(`**/api/events/${evtId}`, async (route) => {
      if (route.request().method() === "PATCH") {
        return route.fulfill({
          contentType: "application/json",
          body: JSON.stringify({
            id: evtId,
            source_message_id: msgId,
            position: 1,
            title: "回复邮件",
            source_fragment: "邮件回了",
            occurred_at: new Date().toISOString(),
            occurrence_precision: "date",
            part_of_day: "afternoon",
            category_id: "cat-work-talk",
            category_path: ['工作', '沟通'],
            tags: [],
            status: "classified",
          }),
        });
      }
      return route.abort();
    });

    await page.route("**/api/timeline**", async (route) => {
      const url = route.request().url();
      const p = new URLSearchParams(url.split("?")[1] ?? "");
      if (p.get("category_id") === "cat-work-talk") {
        return route.fulfill({
          contentType: "application/json",
          body: JSON.stringify({
            groups: [
              {
                message: {
                  id: msgId,
                  submission_uuid: msgId,
                  original_text: "饭吃了，快递取了，邮件回了。",
                  submitted_at: new Date().toISOString(),
                  timezone: "Asia/Shanghai",
                  status: "classified",
                },
                events: [
                  {
                    id: evtId,
                    source_message_id: msgId,
                    position: 1,
                    title: "回复邮件",
                    source_fragment: "邮件回了",
                    occurred_at: new Date().toISOString(),
                    occurrence_precision: "date",
                    part_of_day: "afternoon",
                    category_id: "cat-work-talk",
                    category_path: ['工作', '沟通'],
                    tags: [],
                    status: "classified",
                  },
                ],
              },
            ],
            total: 1,
            page: 1,
            page_size: 50,
          }),
        });
      }
      return route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({
          groups: [],
          total: 0,
          page: 1,
          page_size: 50,
        }),
      });
    });

    await page.route("**/api/categories", async (route) => {
      return route.fulfill({
        contentType: "application/json",
        json: [
          {
            id: "cat-1",
            name: "工作",
            normalized_name: "工作",
            children: [
              {
                id: "cat-work-talk",
                name: "沟通",
                normalized_name: "沟通",
                parent_id: "cat-1",
                children: [],
                event_count: 1,
                total_event_count: 1,
              },
            ],
            event_count: 1,
            total_event_count: 2,
          },
        ],
      });
    });

    await page.route("**/api/health", async (route) => {
      return route.fulfill({
        contentType: "application/json",
        json: { status: "ok", version: "0.1.0" },
      });
    });

    await page.goto("/");

    const textarea = page.locator(".composer-input");
    await textarea.fill("饭吃了，快递取了，邮件回了。");
    await page.locator(".composer-submit").click();

    await expect(page.locator(".event-card")).toHaveCount(2);

    const secondCard = page.locator(".event-card").nth(1);
    await secondCard.locator(".event-card-more").click();
    const secondCardEdit = secondCard.getByRole("button", { name: "编辑" });
    await secondCardEdit.click();

    await expect(page.locator(".event-editor-panel")).toBeVisible();

    const catSelect = page.locator("#evt-category");
    await catSelect.selectOption("cat-work-talk");

    await Promise.all([
      page.waitForResponse((resp) => resp.url().includes(`/api/events/${evtId}`) && resp.status() === 200),
      page.locator(".event-editor-save").click(),
    ]);

    // Open the category dropdown in the top nav, expand 工作 and pick 沟通.
    await page.getByRole("button", { name: "分类", exact: true }).click();
    await page
      .locator(".category-tree-root-item")
      .filter({ hasText: "工作" })
      .locator(".category-tree-toggle")
      .click();
    const talkCategory = page
      .locator(".category-tree-child-item")
      .filter({ hasText: "沟通" });
    await talkCategory.click();

    await expect(page.locator(".event-card")).toHaveCount(1);
    await expect(page.locator(".event-card-title")).toContainText("回复邮件");
  });

  test("retries a pending message", async ({ page }) => {
    const msgId = crypto.randomUUID();
    let submitAttempts = 0;

    await page.route("**/api/messages", async (route) => {
      const submissionUuid =
        route.request().postDataJSON()?.submission_uuid ?? crypto.randomUUID();
      if (route.request().method() === "POST" && submitAttempts === 0) {
        submitAttempts++;
        return route.fulfill({
          contentType: "application/json",
          body: JSON.stringify({
            message: {
              id: submissionUuid,
              submission_uuid: submissionUuid,
              original_text: "另一条待处理的消息",
              submitted_at: new Date().toISOString(),
              timezone: "Asia/Shanghai",
              status: "pending",
            },
            events: [],
          }),
        });
      }
      return route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({
          message: {
            id: submissionUuid,
            submission_uuid: submissionUuid,
            original_text: "另一条待处理的消息",
            submitted_at: new Date().toISOString(),
            timezone: "Asia/Shanghai",
            status: "classified",
          },
          events: [
            {
              id: crypto.randomUUID(),
              source_message_id: submissionUuid,
              position: 0,
              title: "待处理事项",
              source_fragment: "另一条待处理的消息",
              occurred_at: new Date().toISOString(),
              occurrence_precision: "date",
              part_of_day: "morning",
              category_id: "cat-1",
              category_path: ['工作'],
              tags: [],
              status: "classified",
            },
          ],
        }),
      });
    });

    await page.route("**/api/messages/*/retry", async (route) => {
      return route.fulfill({
        contentType: "application/json",
        json: { status: "classified" },
      });
    });

    await page.route("**/api/health", async (route) => {
      return route.fulfill({
        contentType: "application/json",
        json: { status: "ok", version: "0.1.0" },
      });
    });

    await page.route("**/api/timeline**", async (route) => {
      return route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({
          groups: [
            {
              message: {
                id: msgId,
                submission_uuid: msgId,
                original_text: "另一条待处理的消息",
                submitted_at: new Date().toISOString(),
                timezone: "Asia/Shanghai",
                status: "classified",
              },
              events: [
                {
                  id: crypto.randomUUID(),
                  source_message_id: msgId,
                  position: 0,
                  title: "待处理事项",
                  source_fragment: "另一条待处理的消息",
                  occurred_at: new Date().toISOString(),
                  occurrence_precision: "date",
                  part_of_day: "morning",
                  category_id: "cat-1",
                  category_path: ['工作'],
                  tags: [],
                  status: "classified",
                },
              ],
            },
          ],
          total: 1,
          page: 1,
          page_size: 50,
        }),
      });
    });

    await page.route("**/api/categories", async (route) => {
      return route.fulfill({
        contentType: "application/json",
        json: [
          {
            id: "cat-1",
            name: "工作",
            normalized_name: "工作",
            children: [],
            event_count: 5,
            total_event_count: 5,
          },
        ],
      });
    });

    await page.goto("/");

    const textarea = page.locator(".composer-input");
    await textarea.fill("另一条待处理的消息");
    await page.locator(".composer-submit").click();

    await expect(page.locator(".pending-card")).toBeVisible();
    await expect(page.locator(".pending-card-retry")).toBeVisible();

    await page.locator(".pending-card-retry").click();

    await expect(page.locator(".message-group-text")).toContainText("另一条待处理的消息");
    await expect(page.locator(".event-card-title")).toContainText("待处理事项");
  });

  test("classifies through the real backend with a fake model", async ({
    page,
  }) => {
    // No API routes are mocked here: requests hit the FastAPI pipeline
    // started by the webServer (SHRED_E2E_FAKE_CLASSIFIER=1), which runs
    // alembic migrations and persists to an isolated e2e-test.db.
    await page.goto("/");

    // Wait for the initial timeline fetch to land in the client cache
    // before submitting; otherwise the composer's optimistic update has no
    // timeline data to attach to and the group only appears after refetch.
    await expect(
      page.locator(".message-group, .timeline-empty").first(),
    ).toBeVisible();

    const text = `真后端链路 ${Date.now()}`;
    await page.locator(".composer-input").fill(text);
    await page.locator(".composer-submit").click();

    // Locate the group by its unique source text so repeated runs of the
    // shared e2e-test.db stay idempotent.
    const submittedGroup = page.locator(".message-group").filter({
      hasText: text,
    });
    await expect(submittedGroup.locator(".message-group-text")).toContainText(
      text,
      { timeout: 10_000 },
    );
    await expect(submittedGroup.locator(".event-card")).toHaveCount(2, {
      timeout: 10_000,
    });
    await expect(
      submittedGroup.locator(".event-card-title").first(),
    ).toContainText("假模型事件一");
  });
});
