import type { HeaderAction } from "../header.config";
import CartIcon from "../../../assets/header/Cart.png";
import BellIcon from "../../../assets/header/Notification.png";
import AccountIcon from "../../../assets/header/user.png";
import { Link } from "react-router-dom";

type Props = {
  actions: HeaderAction[];
};

const iconBtnClass = "cursor-pointer";

const HeaderActions = ({ actions }: Props) => {
  return (
    <div className="flex items-center justify-end gap-4.5">
      {actions.map((action) => {
        if (action === "signIn") {
          return (
            <Link
              key={action}
              to="/login"
              className="border-[var(--color-brand)] border items-center rounded-lg bg-white text-sm font-semibold text-[var(--color-brand)] hover:opacity-90 transition-opacity rotate-0 text-[14px] leading-[24px] text-center align-middle opacity-100 px-3 py-2"
            >
              Sign In
            </Link>
          );
        }

        if (action === "bell") {
          return (
            <button
              key={action}
              type="button"
              className={iconBtnClass}
              aria-label="Notifications"
            >
              <img src={BellIcon} alt="Notifications" />
            </button>
          );
        }

        if (action === "cart") {
          return (
            <button
              key={action}
              type="button"
              className={iconBtnClass}
              aria-label="Shopping cart"
            >
              <img src={CartIcon} alt="Shopping cart" />
            </button>
          );
        }

        return (
          <button
            key={action}
            type="button"
            className={iconBtnClass}
            aria-label="Account"
          >
            <img src={AccountIcon} alt="Account" />
          </button>
        );
      })}
    </div>
  );
};

export default HeaderActions;
