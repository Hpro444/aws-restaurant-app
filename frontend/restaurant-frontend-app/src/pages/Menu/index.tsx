import Layout from "../../components/layout";
import { useAuth } from "../../context/AuthContext";
import DynamicMenu from "./components/Dynamic";
import StaticMenu from "./components/Static";
import header_image from "../../assets/menu/menu_header.jpg";

const MenuPage = () => {
  const { isAuthenticated } = useAuth();
  return (
    <div>
      <div
        className="bg-cover bg-center relative"
        style={{ backgroundImage: `url(${header_image})` }}
      >
         <div className="absolute inset-0 bg-[#231E22CC]"></div>
        <Layout className="relative z-10 text-[var(--color-brand)] !gap-4">
          <h2 className="font-medium text-[24px] leading-[40px] align-middle tracking-normal">
            Green & Tasty Restaurants
          </h2>
          <h1 className="font-medium text-[48px] leading-[48px] tracking-normal align-middle">
            Menu
          </h1>
        </Layout>
      </div>

      <Layout>{isAuthenticated ? <DynamicMenu /> : <StaticMenu />}</Layout>
    </div>
  );
};

export default MenuPage;
