import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import type {
  TimelineGroup,
  TimelinePage,
  CategoryNode,
  MessageDetail,
  SourceMessage,
  ActivityEvent,
  SettingsConfig,
} from "@/api/types";

const sampleSettings: SettingsConfig = {
  api_base_url: "https://api.openai.com/v1",
  model_name: "gpt-4o",
  api_key_configured: true,
  preference_count: 3,
};

const sampleCategories: CategoryNode[] = [
  {
    id: "cat-1",
    name: "工作",
    normalized_name: "work",
    children: [
      {
        id: "cat-2",
        name: "会议",
        normalized_name: "meeting",
        parent_id: "cat-1",
        children: [],
        event_count: 2,
        total_event_count: 2,
      },
    ],
    event_count: 0,
    total_event_count: 2,
  },
  {
    id: "cat-3",
    name: "个人",
    normalized_name: "personal",
    children: [],
    event_count: 1,
    total_event_count: 1,
  },
];

const sampleMessages: SourceMessage[] = [
  {
    id: "msg-1",
    submission_uuid: "uuid-1",
    original_text: "上午9点在会议室开会讨论项目计划，记得带笔记本",
    submitted_at: "2026-08-10T01:00:00.000Z",
    timezone: "Asia/Shanghai",
    status: "classified",
  },
  {
    id: "msg-2",
    submission_uuid: "uuid-2",
    original_text: "下午3点去健身房，晚上和朋友吃饭",
    submitted_at: "2026-08-09T05:00:00.000Z",
    timezone: "Asia/Shanghai",
    status: "classified",
  },
  {
    id: "msg-3",
    submission_uuid: "uuid-3",
    original_text: "需要整理的内容还在处理中",
    submitted_at: "2026-08-10T03:00:00.000Z",
    timezone: "Asia/Shanghai",
    status: "pending",
  },
];

const sampleEvents: Record<string, ActivityEvent[]> = {
  "msg-1": [
    {
      id: "evt-1",
      source_message_id: "msg-1",
      position: 0,
      title: "项目计划讨论会",
      source_fragment: "在会议室开会讨论项目计划",
      occurred_at: "2026-08-10T01:00:00.000Z",
      occurrence_precision: "exact",
      part_of_day: "morning",
      category_id: "cat-2",
      category_path: ['工作', '会议'],
      tags: ["会议", "项目"],
      status: "classified",
    },
    {
      id: "evt-2",
      source_message_id: "msg-1",
      position: 1,
      title: "带笔记本",
      source_fragment: "记得带笔记本",
      occurred_at: "2026-08-10T01:00:00.000Z",
      occurrence_precision: "exact",
      part_of_day: "morning",
      category_id: "cat-1",
      category_path: ['工作'],
      tags: ["备忘"],
      status: "classified",
    },
    {
      id: "evt-3",
      source_message_id: "msg-1",
      position: 2,
      title: "上午会议",
      source_fragment: "上午9点",
      occurred_at: "2026-08-10T01:00:00.000Z",
      occurrence_precision: "time",
      part_of_day: "morning",
      tags: [],
      status: "classified",
    },
  ],
  "msg-2": [
    {
      id: "evt-4",
      source_message_id: "msg-2",
      position: 0,
      title: "健身房锻炼",
      source_fragment: "去健身房",
      occurred_at: "2026-08-09T07:00:00.000Z",
      occurrence_precision: "exact",
      part_of_day: "afternoon",
      category_id: "cat-3",
      category_path: ['个人'],
      tags: ["健身"],
      status: "classified",
    },
    {
      id: "evt-5",
      source_message_id: "msg-2",
      position: 1,
      title: "朋友聚餐",
      source_fragment: "和朋友吃饭",
      occurred_at: "2026-08-09T11:00:00.000Z",
      occurrence_precision: "exact",
      part_of_day: "evening",
      category_id: "cat-3",
      category_path: ['个人'],
      tags: ["社交", "美食"],
      status: "classified",
    },
  ],
  "msg-3": [],
};

const submittedStore = new Map<string, SourceMessage>();
const submittedEvents = new Map<string, ActivityEvent[]>();

function makeSubmittedEvents(msgId: string, text: string, submittedAt: string): ActivityEvent[] {
  return [
    {
      id: `${msgId}-evt-1`,
      source_message_id: msgId,
      position: 0,
      title: "事件一",
      source_fragment: text.substring(0, 10),
      occurred_at: submittedAt,
      occurrence_precision: "exact",
      part_of_day: "morning",
      category_id: "cat-2",
      category_path: ['工作', '会议'],
      tags: ["标签1"],
      status: "classified",
    },
    {
      id: `${msgId}-evt-2`,
      source_message_id: msgId,
      position: 1,
      title: "事件二",
      source_fragment: text.substring(10, 20),
      occurred_at: submittedAt,
      occurrence_precision: "exact",
      part_of_day: "morning",
      category_id: "cat-1",
      category_path: ['工作'],
      tags: ["标签2"],
      status: "classified",
    },
    {
      id: `${msgId}-evt-3`,
      source_message_id: msgId,
      position: 2,
      title: "事件三",
      source_fragment: text.substring(20, 30),
      occurred_at: submittedAt,
      occurrence_precision: "time",
      part_of_day: "morning",
      tags: [],
      status: "classified",
    },
  ];
}

function buildTimelinePage(
  page: number,
  pageSize: number,
  status?: string | null,
  categoryId?: string | null,
): TimelinePage {
  const allGroups: TimelineGroup[] = [
    ...sampleMessages.map((m) => ({
      message: m,
      events: sampleEvents[m.id] ?? [],
    })),
  ];

  for (const [id, msg] of submittedStore) {
    allGroups.unshift({
      message: msg,
      events: submittedEvents.get(id) ?? [],
    });
  }

  let groups = allGroups.filter((g) => {
    if (status && g.message.status !== status) return false;
    if (categoryId) {
      return g.events.some((e) => e.category_id === categoryId);
    }
    return true;
  });

  const total = groups.length;
  const start = (page - 1) * pageSize;
  groups = groups.slice(start, start + pageSize);

  return { groups, total, page, page_size: pageSize };
}

let submittedCount = 0;

export const server = setupServer(
  http.get("/api/health", () => {
    return HttpResponse.json({ status: "ok" });
  }),

  http.get("/api/timeline", ({ request }) => {
    const url = new URL(request.url);
    const page = Number(url.searchParams.get("page") ?? 1);
    const pageSize = Number(url.searchParams.get("page_size") ?? 50);
    const status = url.searchParams.get("status");
    const categoryId = url.searchParams.get("category_id");
    return HttpResponse.json(buildTimelinePage(page, pageSize, status, categoryId));
  }),

  http.get("/api/categories", () => {
    return HttpResponse.json(sampleCategories);
  }),

  http.post("/api/messages", async ({ request }) => {
    const body = (await request.json()) as {
      submission_uuid: string;
      text: string;
      submitted_at: string;
      timezone: string;
    };

    submittedCount++;
    const msgId = `msg-submitted-${submittedCount}`;
    const message: SourceMessage = {
      id: msgId,
      submission_uuid: body.submission_uuid,
      original_text: body.text,
      submitted_at: body.submitted_at,
      timezone: body.timezone,
      status: "classified",
    };

    submittedStore.set(msgId, message);
    const events = makeSubmittedEvents(msgId, body.text, body.submitted_at);
    submittedEvents.set(msgId, events);

    const detail: MessageDetail = { message, events };

    return HttpResponse.json(detail, { status: 201 });
  }),

  http.post("/api/messages/:id/undo", ({ params }) => {
    const { id } = params;
    submittedStore.delete(id as string);
    submittedEvents.delete(id as string);
    return new HttpResponse(null, { status: 204 });
  }),

  http.post("/api/messages/:id/retry", ({ params }) => {
    const { id } = params;
    const msg = submittedStore.get(id as string);
    if (msg) {
      msg.status = "classified";
    }
    return HttpResponse.json({ status: "ok" });
  }),

  http.patch("/api/events/:id", async ({ params, request }) => {
    const { id } = params;
    const body = (await request.json()) as Record<string, unknown>;
    for (const [msgId, events] of submittedEvents) {
      const idx = events.findIndex((e) => e.id === id);
      if (idx !== -1) {
        const updated = { ...events[idx]!, ...body };
        events[idx] = updated;
        return HttpResponse.json(updated);
      }
    }
    for (const [, events] of Object.entries(sampleEvents)) {
      const idx = events.findIndex((e) => e.id === id);
      if (idx !== -1) {
        const updated = { ...events[idx]!, ...body };
        events[idx] = updated;
        return HttpResponse.json(updated);
      }
    }
    return HttpResponse.json({ error: { code: "not_found", message: "Not found" } }, { status: 404 });
  }),

  http.delete("/api/events/:id", ({ params }) => {
    const { id } = params;
    for (const [, events] of submittedEvents) {
      const idx = events.findIndex((e) => e.id === id);
      if (idx !== -1) {
        events.splice(idx, 1);
        return new HttpResponse(null, { status: 204 });
      }
    }
    for (const [, events] of Object.entries(sampleEvents)) {
      const idx = events.findIndex((e) => e.id === id);
      if (idx !== -1) {
        events.splice(idx, 1);
        return new HttpResponse(null, { status: 204 });
      }
    }
    return new HttpResponse(null, { status: 204 });
  }),

  http.post("/api/events/:id/reclassify", ({ params }) => {
    const { id } = params;
    return HttpResponse.json({ status: "ok" });
  }),

  http.delete("/api/messages/:id", ({ params }) => {
    const { id } = params;
    submittedStore.delete(id as string);
    submittedEvents.delete(id as string);
    return new HttpResponse(null, { status: 204 });
  }),

  http.post("/api/categories", async ({ request }) => {
    const body = (await request.json()) as { name: string; parent_id?: string };
    const newCat: CategoryNode = {
      id: `cat-new-${Date.now()}`,
      name: body.name,
      normalized_name: body.name.toLowerCase(),
      parent_id: body.parent_id,
      children: [],
      event_count: 0,
      total_event_count: 0,
    };
    return HttpResponse.json(newCat, { status: 201 });
  }),

  http.patch("/api/categories/:id", async ({ params, request }) => {
    const body = (await request.json()) as { name: string };
    return HttpResponse.json({
      id: params.id,
      name: body.name,
      normalized_name: body.name.toLowerCase(),
      children: [],
      event_count: 0,
      total_event_count: 0,
    } as CategoryNode);
  }),

  http.post("/api/categories/merge", () => {
    return new HttpResponse(null, { status: 204 });
  }),

  http.post("/api/categories/:id/delete-impact", ({ params }) => {
    return HttpResponse.json({
      category_id: params.id,
      category_name: "测试分类",
      descendant_count: 2,
      affected_event_count: 5,
    });
  }),

  http.delete("/api/categories/:id", () => {
    return new HttpResponse(null, { status: 204 });
  }),

  http.get("/api/settings", () => {
    return HttpResponse.json(sampleSettings);
  }),

  http.patch("/api/settings", async ({ request }) => {
    const body = (await request.json()) as Partial<SettingsConfig>;
    return HttpResponse.json({ ...sampleSettings, ...body });
  }),

  http.post("/api/settings/test-connection", () => {
    return HttpResponse.json({ ok: true });
  }),

  http.delete("/api/preferences", async ({ request }) => {
    const body = (await request.json()) as { confirm?: boolean };
    if (!body.confirm) {
      return HttpResponse.json(
        { error: { code: "confirmation_required", message: "需要确认操作" } },
        { status: 400 },
      );
    }
    return new HttpResponse(null, { status: 204 });
  }),

  http.get("/api/export", () => {
    return new HttpResponse('{"data":"exported"}', {
      headers: {
        "Content-Type": "application/json",
        "Content-Disposition": 'attachment; filename="shred-export.json"',
      },
    });
  }),
);
