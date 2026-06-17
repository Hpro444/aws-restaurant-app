import type { HeaderNavItem } from "../header.config";
import { NavLink } from "react-router-dom";

type Props = {
  items: HeaderNavItem[];
};

const HeaderNav = ({ items }: Props) => {
  const baseClass =
    "pb-1.5 text-[20px] font-medium font-poppins align-middle leading-[32px] transition-colors border-b-2 border-transparent text-[var(--color-text-primary)] hover:text-[var(--color-brand)]";

  return (
    <nav
      aria-label="Main navigation"
      className="flex items-center justify-center gap-4"
    >
      {items.map((item) => (
        <NavLink
          key={item.href}
          to={item.href}
          end={item.href === "/"}
          className={({ isActive }) =>
            `${baseClass} ${isActive && "border-[var(--color-brand)] text-[var(--color-brand)]"}`
          }
        >
          {item.label}
        </NavLink>
      ))}
    </nav>
  );
};

export default HeaderNav;
