import Layout from "../../components/layout";
import { useAuth } from "../../context/AuthContext";
import DynamicMenu from "./components/Dynamic";
import StaticMenu from "./components/Static";
import header_image from "../../assets/menu/menu_header.jpg";
import Header from "../../components/header";
import { Link } from "react-router-dom";

const MenuPage = () => {
  const { isAuthenticated } = useAuth();
  return (
    <div>
      <Header />
      {isAuthenticated && (
        <div className="max-w-[1440px] px-10 mx-auto flex flex-col gap-16 mb-7 font-poppins">
          <section className="flex gap-2 mt-2 font-light text-[14px] leading-[24px] tracking-normal">
            <Link
              to="/"
              className="cursor-pointer hover:text-[var(--color-brand)] transition-colors"
            >
              Main page
            </Link>
            <span>{">"}</span>

            <span className="font-medium text-[14px] leading-[24px]">Menu</span>
          </section>
        </div>
      )}

      <div
        className={`bg-cover bg-center relative ${isAuthenticated && "py-20"}`}
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
