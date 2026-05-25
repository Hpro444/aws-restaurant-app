import { ACTIONS_BY_ROLE, NAV_ITEMS_BY_ROLE } from "./header.config";
import HeaderActions from "./components/HeaderActions";
// import HeaderLogo from "./HeaderLogo";
import HeaderNav from "./components/HeaderNav";
// import { useAuth } from "../../contexts/AuthContext";
import HeaderLogo from "../../assets/Logo.png";
import { Link } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";

const Header = () => {
  const { viewerRole } = useAuth();

  const navItems = NAV_ITEMS_BY_ROLE[viewerRole];
  const actions = ACTIONS_BY_ROLE[viewerRole];

  return (
    <header className="border-b border-[var(--color-border-default)] bg-[var(--color-surface)] mx-auto max-w-[1440px] font-poppins">
      <div className="w-full flex justify-between items-center py-3 px-10">
        <Link to="/">
          <img src={HeaderLogo} alt="Logo" />
        </Link>
        <HeaderNav items={navItems} />
        <HeaderActions actions={actions} />
      </div>
    </header>
  );
};

export default Header;
