import Header from "../../components/header";
import FoundResults from "./components/FoundResults";
import NoResults from "./components/NoResults";
import HeaderSection from "./components/HeaderSection";

const AvailableTablesPage = () => {
  return (
    <>
      <Header />
      <HeaderSection />
      <div className="max-w-[1440px] px-10 mx-auto flex flex-col gap-10 mb-8 font-poppins mt-16">
        <FoundResults />
        <NoResults />
      </div>
    </>
  );
};

export default AvailableTablesPage;
