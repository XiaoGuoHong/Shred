export type ViewSelection =
  | { kind: "all" }
  | { kind: "pending" }
  | { kind: "category"; categoryId: string }
  | { kind: "manage-categories" }
  | { kind: "settings" };
