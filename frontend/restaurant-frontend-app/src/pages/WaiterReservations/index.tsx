import { useState } from "react";
import { Calendar } from "primereact/calendar";
import type { Nullable } from "primereact/ts-helpers";
import subheading from "../../assets/reservations/subheading.png";
import logoWhite from "../../assets/logoWhite.png";
import Header from "../../components/header";
import Layout from "../../components/layout";
import { useAuth } from "../../context/AuthContext";
import ReservationCard from "./components/ReservationCard";
import NoResults from "../Reservations/components/NoResults";
import { type ReservationResponse } from "../Reservations/reservations.services";
import { searchWaiterReservations } from "./waiterReservations.services";
import NewReservationModal from "./components/NewReservationModal";

const isDateOrNull = (value: unknown): value is Date | null => {
  return value === null || value instanceof Date;
};

const formatSelectedDate = (selectedDate: Date | null) => {
  if (!selectedDate) return "selected date";
  return selectedDate.toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
};

const toApiDate = (date: Date): string => {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
};

const toApiTimeFromIso = (selectedDate: Date, selectedTime: Date): string => {
  const combined = new Date(selectedDate);
  combined.setHours(selectedTime.getHours(), selectedTime.getMinutes(), 0, 0);

  return combined.toISOString().replace(/\.\d{3}Z$/, "Z");
};

const WaiterReservations = () => {
  const { accessToken, user } = useAuth();
  const [selectedDate, setSelectedDate] = useState<Date | null>(null);
  const [selectedTime, setSelectedTime] = useState<Nullable<Date>>(null);
  const [tableName, setTableName] = useState<string>("");
  const [reservations, setReservations] = useState<ReservationResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasSearched, setHasSearched] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);

  const handleSearch = async () => {
    if (!accessToken) {
      setError("Please log in to view reservations");
      return;
    }

    if (!selectedDate || !selectedTime || !tableName.trim()) {
      setError("Date, time and table are required");
      return;
    }

    try {
      setLoading(true);
      setError(null);
      setHasSearched(true);

      const data = await searchWaiterReservations(accessToken, {
        date: toApiDate(selectedDate),
        time_from: toApiTimeFromIso(selectedDate, selectedTime),
        table_name: tableName.trim(),
      });

      setReservations(data);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load reservations",
      );
      setReservations([]);
    } finally {
      setLoading(false);
    }
  };

  const handleEditReservation = (reservation: ReservationResponse) => {
    console.log("Edit reservation:", reservation);
  };

  const handleCancelReservation = (reservationId: string) => {
    console.log("Cancel reservation:", reservationId);
  };

  return (
    <>
      <Header />

      <div
        className="bg-cover bg-center"
        style={{ backgroundImage: `url(${subheading})` }}
      >
        <div className="max-w-[1440px] mx-auto px-10 py-[18px] flex justify-between items-center">
          <h2 className="font-medium text-2xl leading-10 tracking-normal align-middle text-white">
            {user?.username
              ? `Hello, ${user.username} (${user.role})`
              : "Hello, Waiter"}
          </h2>
          <img src={logoWhite} alt="Logo" />
        </div>
      </div>

      <Layout>
        <div className="flex flex-col gap-8">
          <div className="flex items-center gap-4 justify-center">
            <div className="max-w-[200px] relative flex items-center gap-2 border border-gray-200 rounded-lg px-6 py-4">
              <Calendar
                value={selectedDate}
                onChange={(e) => {
                  if (isDateOrNull(e.value)) {
                    setSelectedDate(e.value);
                  }
                }}
                selectionMode="single"
                showIcon={true}
                iconPos="left"
                icon="pi pi-calendar"
                panelClassName="bg-white"
                className="gap-2"
                dateFormat="M d, yy"
                placeholder="Pick date"
              />
            </div>

            <div className="relative flex items-center gap-2 border border-gray-200 rounded-xl px-6 py-4 bg-white max-w-[200px] hover:border-green-500 transition">
              <Calendar
                value={selectedTime}
                iconPos="left"
                showIcon={true}
                icon="pi pi-clock"
                onChange={(e) => {
                  if (isDateOrNull(e.value)) {
                    setSelectedTime(e.value);
                  }
                }}
                timeOnly
                panelClassName="text-[20px]"
                className="gap-2"
                hourFormat="24"
                placeholder="Pick time"
              />
            </div>

            <select
              value={tableName}
              onChange={(e) => setTableName(e.target.value)}
              className="border border-gray-200 rounded-xl px-6 py-4 bg-white w-[200px] hover:border-green-500 transition"
            >
              <option value="">Select table</option>
              <option value="Table 1">Table 1</option>
              <option value="Table 2">Table 2</option>
              <option value="Table 3">Table 3</option>
              <option value="Table 4">Table 4</option>
              <option value="Table 5">Table 5</option>
              <option value="Table 6">Table 6</option>
              <option value="Table 7">Table 7</option>
              <option value="Table 8">Table 8</option>
              <option value="Table 9">Table 9</option>
              <option value="Table 10">Table 10</option>
            </select>

            <button
              onClick={handleSearch}
              className="flex items-center justify-center border-2 border-green-500 rounded-lg p-4 bg-white hover:bg-green-50 transition"
              type="button"
              aria-label="Search reservations"
            >
              <span className="pi pi-search"></span>
            </button>
          </div>

          <div className="flex items-center justify-between gap-4">
            <p className="text-lg font-medium text-[#232323]">
              {reservations.length} reservations for{" "}
              {formatSelectedDate(selectedDate)}
            </p>
            <button
              onClick={() => setIsModalOpen(true)}
              className="cursor-pointer rounded-lg bg-[#00AD0C] px-5 py-3 text-white"
            >
              Create New Reservation
            </button>
          </div>

          {loading ? (
            <p className="text-center text-gray-500">Loading reservations...</p>
          ) : error ? (
            <p className="text-center text-red-500">{error}</p>
          ) : !hasSearched ? (
            <p className="text-center text-gray-500">
              Select date, time and table, then click search.
            </p>
          ) : reservations.length === 0 ? (
            <NoResults />
          ) : (
            <div className="grid grid-cols-1 gap-8 lg:grid-cols-2 xl:grid-cols-3">
              {reservations.map((reservation) => (
                <ReservationCard
                  key={reservation.reservation_id}
                  reservation={reservation}
                  onEdit={handleEditReservation}
                  onCancel={handleCancelReservation}
                />
              ))}
            </div>
          )}
        </div>
      </Layout>
      {isModalOpen && (
        // Implement logic for commucating with backend
        <NewReservationModal
          onClose={() => setIsModalOpen(false)}
          onSubmit={(payload) => {
            console.log("New reservation:", payload);
            setIsModalOpen(false);
          }}
        />
      )}
    </>
  );
};

export default WaiterReservations;
