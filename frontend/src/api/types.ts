export type ViewSelection =
  | { kind: "all" }
  | { kind: "pending" }
  | { kind: "category"; categoryId: string }
  | { kind: "manage-categories" }
  | { kind: "settings" };

export interface SourceMessage {
  id: string;
  submission_uuid: string;
  original_text: string;
  submitted_at: string;
  timezone: string;
  status: string;
  error_code?: string;
  error_summary?: string;
}

export interface ActivityEvent {
  id: string;
  source_message_id: string;
  position: number;
  title: string;
  source_fragment: string;
  occurred_at: string;
  occurrence_precision: string;
  part_of_day: string;
  category_id?: string;
  category_path?: string;
  tags: string[];
  status: string;
}

export interface CategoryNode {
  id: string;
  name: string;
  normalized_name: string;
  parent_id?: string;
  children: CategoryNode[];
  event_count: number;
  total_event_count: number;
}

export interface MessageDetail {
  message: SourceMessage;
  events: ActivityEvent[];
}

export interface TimelineGroup {
  message: SourceMessage;
  events: ActivityEvent[];
}

export interface TimelinePage {
  groups: TimelineGroup[];
  total: number;
  page: number;
  page_size: number;
}

export interface SubmitMessageInput {
  submission_uuid: string;
  text: string;
  submitted_at: string;
  timezone: string;
}

export interface ApiError {
  code: string;
  message: string;
}

export interface TimelineParams {
  page?: number;
  page_size?: number;
  category_id?: string;
  status?: string;
}

export interface DeleteImpact {
  category_id: string;
  category_name: string;
  descendant_count: number;
  affected_event_count: number;
}

export interface SettingsConfig {
  api_base_url: string;
  model_name: string;
  api_key_configured: boolean;
  preference_count: number;
}

export interface TestConnectionResult {
  ok: boolean;
  error_code?: string | null;
  error_message?: string | null;
}
