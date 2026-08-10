import { describe, it, expect, vi, beforeAll, afterAll, afterEach } from "vitest";
import { api, buildSubmissionInput } from "@/api/client";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";

const server = setupServer(
  http.get("/api/health", () => HttpResponse.json({ status: "ok" })),
);

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe("api.submitMessage", () => {
  it("sends correct shape with UUID, ISO time, and IANA timezone", async () => {
    const capturedBody: unknown[] = [];

    server.use(
      http.post("/api/messages", async ({ request }) => {
        const body = await request.json();
        capturedBody.push(body);
        return HttpResponse.json({
          message: {
            id: "msg-1",
            submission_uuid: (body as { submission_uuid: string }).submission_uuid,
            original_text: (body as { text: string }).text,
            submitted_at: (body as { submitted_at: string }).submitted_at,
            timezone: (body as { timezone: string }).timezone,
            status: "classified",
          },
          events: [],
        });
      }),
    );

    const input = buildSubmissionInput("test message");
    await api.submitMessage(input);

    expect(capturedBody).toHaveLength(1);
    const body = capturedBody[0] as Record<string, unknown>;
    expect(body).toHaveProperty("submission_uuid");
    expect(typeof body.submission_uuid).toBe("string");
    expect((body.submission_uuid as string).length).toBeGreaterThan(0);
    expect(body).toHaveProperty("text", "test message");
    expect(body).toHaveProperty("submitted_at");
    expect(new Date(body.submitted_at as string).toISOString()).toBe(
      body.submitted_at,
    );
    expect(body).toHaveProperty("timezone");
    expect(typeof body.timezone).toBe("string");
    expect((body.timezone as string).length).toBeGreaterThan(0);
  });

  it("throws ApiError on non-2xx error response", async () => {
    server.use(
      http.post("/api/messages", () => {
        return HttpResponse.json(
          { error: { code: "validation_error", message: "Invalid input" } },
          { status: 422 },
        );
      }),
    );

    const input = buildSubmissionInput("bad input");
    let error: Error | undefined;
    try {
      await api.submitMessage(input);
    } catch (e) {
      error = e as Error;
    }

    expect(error).toBeDefined();
    expect(error!.name).toBe("ApiClientError");
    expect((error as { code: string }).code).toBe("validation_error");
    expect(error!.message).toBe("Invalid input");
  });

  it("throws unexpected_response on malformed response", async () => {
    server.use(
      http.post("/api/messages", () => {
        return new HttpResponse("not json", { status: 200 });
      }),
    );

    const input = buildSubmissionInput("test");
    let error: Error | undefined;
    try {
      await api.submitMessage(input);
    } catch (e) {
      error = e as Error;
    }

    expect(error).toBeDefined();
    expect(error!.name).toBe("ApiClientError");
    expect((error as { code: string }).code).toBe("unexpected_response");
  });
});
