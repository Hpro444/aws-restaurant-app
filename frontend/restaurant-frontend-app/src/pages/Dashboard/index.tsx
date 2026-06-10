import Header from "../../components/header";
import logoWhite from "../../assets/logoWhite.png";
import subheading from "../../assets/reservations/subheading.png";
import { useAuth } from "../../context/AuthContext";
import Layout from "../../components/layout";
import { Calendar } from "primereact/calendar";
import { useEffect, useState } from "react";
import DownloadButton from "./components/DownloadButton";
import ReportTable from "./components/Table";
import { getLocationSelectOptions } from "../AvailableTables/availableTables.services";
import type { LocationSelectOption } from "../../types/location";

const DashboardPage = () => {
  const { user, accessToken } = useAuth();
  const [dates, setDates] = useState<(Date | null)[] | null>(null);
  const [reportType, setReportType] = useState("");
  const [location, setLocation] = useState("");
  const [locationOptions, setLocationOptions] = useState<
    LocationSelectOption[]
  >([]);
  const [locationsError, setLocationsError] = useState<string | null>(null);

  useEffect(() => {
    const loadLocations = async () => {
      try {
        setLocationsError(null);
        const data = await getLocationSelectOptions(accessToken || undefined);
        setLocationOptions(data);
      } catch (err) {
        setLocationsError(
          err instanceof Error ? err.message : "Failed to fetch locations",
        );
      }
    };

    loadLocations();
  }, [accessToken]);

  return (
    <>
      <Header />

      <div
        className="bg-cover bg-center"
        style={{
          backgroundImage: `url(${subheading})`,
        }}
      >
        <div className="max-w-[1440px] mx-auto px-10 py-[18px] flex justify-between items-center font-poppins">
          <h2 className="font-medium text-2xl leading-10 tracking-normal align-middle text-white">
            {user && `Hello, ${user.username} (${user.role})`}
          </h2>
          <div>
            <img src={logoWhite} alt="Logo" />
          </div>
        </div>
      </div>

      <Layout>
        <div className="flex gap-4 font-poppins">
          <select
            value={reportType}
            onChange={(e) => setReportType(e.target.value)}
            name="reportType"
            className={
              "cursor-pointer border border-[#dadada] px-6 py-4 rounded-lg flex-1 max-w-[328px]" +
              (reportType === "" ? " text-[#898989]" : " text-[#232323]")
            }
          >
            <option value="" disabled>
              Select report type
            </option>
            <option value="staff-performance" className="text-[#232323]">
              Staff performance
            </option>
            <option value="sales" className="text-[#232323]">
              Sales
            </option>
          </select>

          <Calendar
            value={dates}
            onChange={(e) => setDates(e.value ?? null)}
            selectionMode="range"
            readOnlyInput
            hideOnRangeSelection
            inputClassName="border border-[#dadada] px-6 rounded-lg"
            panelClassName="border border-[#dadada] rounded-lg bg-white shadow-lg"
            className="w-full max-w-[328px] flex-1"
            dateFormat="M d, yy"
            placeholder="Select period"
          />

          <select
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            name="location"
            className={
              "cursor-pointer border border-[#dadada] px-6 py-4 rounded-lg flex-1 max-w-[328px]" +
              (location === "" ? " text-[#898989]" : " text-[#232323]")
            }
          >
            <option value="" disabled className="text-[#898989]">
              Select location
            </option>
            {locationOptions.map((option) => (
              <option
                key={option.location_id}
                value={option.location_id}
                className="text-[#232323]"
              >
                {option.location_address}
              </option>
            ))}
          </select>

          <button className="cursor-pointer rounded-lg bg-[var(--color-brand)] text-white py-2 flex-1 max-w-[328px]">
            Generate Report
          </button>
        </div>

        <div className="font-poppins flex flex-col gap-4">
          <h2 className="font-medium text-2xl leading-10 tracking-normal mb-2">
            Report
          </h2>

          {locationsError ? (
            <p className="text-[#B70B0B] font-medium">{locationsError}</p>
          ) : null}

          <ReportTable />

          <DownloadButton className="self-end" />
        </div>
      </Layout>
    </>
  );
};

export default DashboardPage;
