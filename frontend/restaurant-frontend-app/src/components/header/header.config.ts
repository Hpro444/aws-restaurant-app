// import type { HeaderViewerRole } from "../../contexts/AuthContext";

export type HeaderNavItem = {
  label: string;
  href: string;
};

type HeaderViewerRole = "guest" | "customer" | "waiter" | "admin";

export type HeaderAction = "bell" | "account" | "cart" | "signIn";

export const NAV_ITEMS_BY_ROLE: Record<HeaderViewerRole, HeaderNavItem[]> = {
  guest: [
    { label: "Main Page", href: "/" },
    { label: "Book a Table", href: "/book-table" },
  ],
  customer: [
    { label: "Main Page", href: "/" },
    { label: "Book a Table", href: "/book-table" },
    { label: "Reservations", href: "/reservations" },
  ],
  waiter: [
    { label: "Reservations", href: "/reservations" },
    { label: "Menu", href: "/menu" },
  ],
  admin: [
    { label: "Reports", href: "/reports" },
    { label: "Staff", href: "/staff" },
  ],
};

export const ACTIONS_BY_ROLE: Record<HeaderViewerRole, HeaderAction[]> = {
  guest: ["signIn"],
  customer: ["cart", "account"],
  waiter: ["bell", "account"],
  admin: ["bell", "account"],
};
