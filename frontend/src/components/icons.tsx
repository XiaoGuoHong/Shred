import type { ReactNode } from "react";

export type IconName =
  | "shredMark"
  | "list"
  | "clock"
  | "folder"
  | "settings"
  | "chevronLeft"
  | "chevronRight"
  | "more"
  | "edit"
  | "trash"
  | "tag"
  | "send"
  | "briefcase"
  | "book"
  | "doc"
  | "dumbbell"
  | "home"
  | "heart"
  | "sparkle"
  | "calendar"
  | "x"
  | "menu";

const PATHS: Record<IconName, ReactNode> = {
  shredMark: (
    <>
      <rect x="4" y="4" width="16" height="16" rx="4.5" />
      <path d="M8 16l8-8M8.5 12.5l4-4M11.5 16.5l3.5-3.5" />
    </>
  ),
  list: (
    <>
      <path d="M8.5 6h12M8.5 12h12M8.5 18h12" />
      <circle cx="4.2" cy="6" r="0.9" fill="currentColor" stroke="none" />
      <circle cx="4.2" cy="12" r="0.9" fill="currentColor" stroke="none" />
      <circle cx="4.2" cy="18" r="0.9" fill="currentColor" stroke="none" />
    </>
  ),
  clock: (
    <>
      <circle cx="12" cy="12" r="8.6" />
      <path d="M12 7.2v4.8l3.2 2" />
    </>
  ),
  folder: (
    <path d="M3.5 7.5a2 2 0 0 1 2-2h4.2l2 2h6.8a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2h-13a2 2 0 0 1-2-2z" />
  ),
  settings: (
    <>
      <path d="M4 7h16M4 12h16M4 17h16" />
      <circle cx="9" cy="7" r="1.7" fill="currentColor" stroke="none" />
      <circle cx="15" cy="12" r="1.7" fill="currentColor" stroke="none" />
      <circle cx="7" cy="17" r="1.7" fill="currentColor" stroke="none" />
    </>
  ),
  chevronLeft: <path d="M14.5 5.5 8 12l6.5 6.5" />,
  chevronRight: <path d="M9.5 5.5 16 12l-6.5 6.5" />,
  more: (
    <>
      <circle cx="5" cy="12" r="1.5" fill="currentColor" stroke="none" />
      <circle cx="12" cy="12" r="1.5" fill="currentColor" stroke="none" />
      <circle cx="19" cy="12" r="1.5" fill="currentColor" stroke="none" />
    </>
  ),
  edit: (
    <>
      <path d="M4.5 19.5h4L19 9a2.1 2.1 0 0 0-3-3L5.5 16.5z" />
      <path d="M13.5 6.5l3 3" />
    </>
  ),
  trash: (
    <>
      <path d="M4 7h16M9.5 7V5a1 1 0 0 1 1-1h3a1 1 0 0 1 1 1v2M6.2 7l1 12.5a1.5 1.5 0 0 0 1.5 1.5h6.6a1.5 1.5 0 0 0 1.5-1.5L17.8 7" />
      <path d="M10 11v5.5M14 11v5.5" />
    </>
  ),
  tag: (
    <>
      <path d="M3.5 11V4.5A1.5 1.5 0 0 1 5 3h6.5l9 9-8.5 8.5z" />
      <circle cx="8" cy="8" r="1.3" />
    </>
  ),
  send: (
    <>
      <path d="M21 3.5 3.5 10.5l7 2.5 2.5 7z" />
      <path d="M10.5 13 21 3.5" />
    </>
  ),
  briefcase: (
    <>
      <rect x="3.2" y="7.2" width="17.6" height="12.6" rx="2.5" />
      <path d="M9 7.2V5.8a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v1.4M3.2 12.6h17.6" />
    </>
  ),
  book: (
    <>
      <path d="M4 19.5V5.2A2.2 2.2 0 0 1 6.2 3H20v17H6.2A2.2 2.2 0 0 1 4 17.8z" />
      <path d="M4 17.8A2.2 2.2 0 0 1 6.2 15.6H20" />
      <path d="M9 7.5h6.5" />
    </>
  ),
  doc: (
    <>
      <path d="M13.8 3.5H7.2A2.2 2.2 0 0 0 5 5.7v12.6a2.2 2.2 0 0 0 2.2 2.2h9.6a2.2 2.2 0 0 0 2.2-2.2V8.2z" />
      <path d="M13.8 3.5V8.2h4.7M9 12.8h6M9 16.2h4" />
    </>
  ),
  dumbbell: (
    <>
      <path d="M7 7.5v9M17 7.5v9" />
      <path d="M3.8 9.5v5M20.2 9.5v5" />
      <path d="M7 12h10" />
    </>
  ),
  home: (
    <>
      <path d="M4 11.2 12 4.5l8 6.7" />
      <path d="M6.2 9.8V20h11.6V9.8" />
      <path d="M10 20v-5h4v5" />
    </>
  ),
  heart: (
    <path d="M12 20.2S4.8 15.4 3 10.8A4.9 4.9 0 0 1 12 7.4a4.9 4.9 0 0 1 9 3.4c-1.8 4.6-9 9.4-9 9.4z" />
  ),
  sparkle: <path d="M12 3.5l1.9 5.1 5.1 1.9-5.1 1.9L12 17.5l-1.9-5.1L5 10.5l5.1-1.9z" />,
  calendar: (
    <>
      <rect x="3.5" y="5" width="17" height="15.5" rx="2.5" />
      <path d="M8 3v4M16 3v4M3.5 10.2h17" />
    </>
  ),
  x: <path d="M6 6l12 12M18 6 6 18" />,
  menu: <path d="M4 7h16M4 12h16M4 17h16" />,
};

export function Icon({
  name,
  size = 18,
  className,
  strokeWidth = 1.8,
}: {
  name: IconName;
  size?: number;
  className?: string;
  strokeWidth?: number;
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      {PATHS[name]}
    </svg>
  );
}
