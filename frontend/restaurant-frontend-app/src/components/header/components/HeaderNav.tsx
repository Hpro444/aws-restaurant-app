import type { HeaderNavItem } from "../header.config";
import { Link } from "react-router-dom";

type Props = {
  items: HeaderNavItem[];
};

const HeaderNav = ({ items }: Props) => {
  return (
    <nav
      aria-label="Main navigation"
      className="flex items-center justify-center gap-4"
    >
      {items.map((item) => (
        <Link
          key={item.href}
          to={item.href}
          className="text-[15px] font-medium text-[var(--color-text-primary)] hover:text-[var(--color-brand)] transition-colors font-poppins align-middle"
        >
          {item.label}
        </Link>
      ))}
    </nav>
  );
};

export default HeaderNav;
