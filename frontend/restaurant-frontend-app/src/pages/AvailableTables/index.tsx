import { useEffect, useMemo, useState } from "react";
import Header from "../../components/header";
import FoundResults from "./components/FoundResults";
import NoResults from "./components/NoResults";
import HeaderSection from "./components/HeaderSection";
import { useAuth } from "../../context/AuthContext";
import {
  getAvailableTables,
  getLocationSelectOptions,
} from "./availableTables.services";
import type {
  Filters,
  LocationSelectOption,
  TableResult,
} from "../../types/location";

const AvailableTablesPage = () => {
  const { accessToken } = useAuth();
  const [filters, setFilters] = useState<Filters>({
    locationId: "",
    date: "",
    fromTime: "",
    guests: 1,
  });
  const [tables, setTables] = useState<TableResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasSearched, setHasSearched] = useState(false);
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

  const updateFilter = (update: Partial<Filters>) => {
    setFilters((prev) => ({ ...prev, ...update }));
  };

  const selectedLocationAddress = useMemo(
    () =>
      locationOptions.find((l) => l.location_id === filters.locationId)
        ?.location_address ?? "",
    [locationOptions, filters.locationId],
  );

  const handleSearch = async () => {
    if (!filters.locationId || !filters.date || !accessToken) return;

    setIsLoading(true);
    setError(null);
    try {
      const response = await getAvailableTables(
        {
          location_id: filters.locationId,
          date: filters.date,
          guests_number: filters.guests,
          ...(filters.fromTime ? { from_time: filters.fromTime } : {}),
        },
        accessToken,
      );
      setTables(response.tables);
      setHasSearched(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch tables");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <>
      <Header />
      <HeaderSection
        filters={filters}
        onFiltersChange={updateFilter}
        onSearch={handleSearch}
        isLoading={isLoading}
        locations={locationOptions}
      />
      {error || locationsError ? (
        <div className="max-w-[1440px] px-10 mx-auto mt-4">
          <p className="text-[#B70B0B] font-medium">
            {error || locationsError}
          </p>
        </div>
      ) : null}
      <div className="max-w-[1440px] px-10 mx-auto flex flex-col gap-10 mb-8 font-poppins mt-16">
        {hasSearched &&
          (tables.length > 0 ? (
            <FoundResults
              tables={tables}
              locationAddress={selectedLocationAddress}
              date={filters.date}
            />
          ) : (
            <NoResults />
          ))}
      </div>
    </>
  );
};

export default AvailableTablesPage;
