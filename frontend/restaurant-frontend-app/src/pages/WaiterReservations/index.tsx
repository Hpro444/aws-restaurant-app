import { useEffect, useState } from "react";
import { Calendar } from "primereact/calendar";
import type { Nullable } from "primereact/ts-helpers";
import subheading from "../../assets/reservations/subheading.png";
import logoWhite from "../../assets/logoWhite.png";
import Header from "../../components/header";
import Layout from "../../components/layout";
import { useAuth } from "../../context/AuthContext";
import NoResults from "../Reservations/components/NoResults";
import ReservationCard from "../Reservations/components/ReservationCard";
import EditReservationModal from "../Reservations/components/EditReservationModal";
import {
  cancelReservation,
  type ReservationResponse,
  updateReservation,
  type UpdateReservationPayload,
} from "../Reservations/reservations.services";
import {
  formatApiDate,
  getLocationTables,
  isDateOrNull,
  searchWaiterReservations,
  toApiDate,
  toApiTimeFrom,
} from "./waiterReservations.services";
import NewReservationModal from "./components/NewReservationModal";

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

  const [selectedReservation, setSelectedReservation] =
    useState<ReservationResponse | null>(null);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isEditSubmitting, setIsEditSubmitting] = useState(false);
  const [tableOptions, setTableOptions] = useState<number[]>([]);
  const [tablesLoading, setTablesLoading] = useState(false);
  const [tablesError, setTablesError] = useState<string | null>(null);

  const [toastError, setToastError] = useState<string | null>(null);
  const [toastSuccess, setToastSuccess] = useState<string | null>(null);

  const hasWaiterContext = Boolean(
    accessToken && user?.waiterLocation?.location_id,
  );

  const visibleTableOptions = hasWaiterContext ? tableOptions : [];
  const visibleTablesError = hasWaiterContext ? tablesError : null;

  useEffect(() => {
    if (!hasWaiterContext) return;

    let isMounted = true;

    const loadTables = async () => {
      try {
        setTablesLoading(true);
        setTablesError(null);
        const tableNumbers = await getLocationTables(
          accessToken as string,
          user?.waiterLocation?.location_id as string,
        );

        if (!isMounted) return;
        setTableOptions(tableNumbers);
      } catch (err) {
        if (!isMounted) return;
        setTableOptions([]);
        setTablesError(
          err instanceof Error ? err.message : "Failed to load tables",
        );
      } finally {
        if (isMounted) {
          setTablesLoading(false);
        }
      }
    };

    void loadTables();

    return () => {
      isMounted = false;
    };
  }, [hasWaiterContext, accessToken, user?.waiterLocation?.location_id]);

  useEffect(() => {
    if (!accessToken || !hasWaiterContext || tableOptions.length === 0) return;
    if (hasSearched) return;

    let isMounted = true;

    const loadTodayReservations = async () => {
      const today = new Date();
      const defaultTable = String(tableOptions[0]);

      try {
        setLoading(true);
        setError(null);

        const data = await searchWaiterReservations(accessToken, {
          date: toApiDate(today),
          time_from: "00:00",
          table_name: defaultTable,
        });

        if (!isMounted) return;

        setReservations(data);
        console.log(data);
        setSelectedDate(today);
        setSelectedTime(
          new Date(
            today.getFullYear(),
            today.getMonth(),
            today.getDate(),
            0,
            0,
            0,
            0,
          ),
        );
        setTableName(defaultTable);
        setHasSearched(true);
      } catch (err) {
        if (!isMounted) return;
        setError(
          err instanceof Error
            ? err.message
            : "Failed to load today's reservations",
        );
        setReservations([]);
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    void loadTodayReservations();

    return () => {
      isMounted = false;
    };
  }, [accessToken, hasWaiterContext, tableOptions, hasSearched]);

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
        time_from: toApiTimeFrom(selectedTime),
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
    setError(null);
    setSelectedReservation(reservation);
    setIsEditModalOpen(true);
  };

  const handleSubmitEdit = async (payload: UpdateReservationPayload) => {
    if (!accessToken || !selectedReservation) {
      setError("Please log in to edit reservation");
      return;
    }

    try {
      setIsEditSubmitting(true);
      setError(null);

      const updated = await updateReservation(
        selectedReservation.reservation_id,
        payload,
        accessToken,
      );

      setReservations((prev) =>
        prev.map((item) =>
          item.reservation_id === updated.reservation_id ? updated : item,
        ),
      );

      setSelectedReservation(updated);
      setIsEditModalOpen(false);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to update reservation",
      );
    } finally {
      setIsEditSubmitting(false);
    }
  };

  const handleReservationCreated = async () => {
    if (!accessToken) return;

    if (!selectedDate || !selectedTime || !tableName.trim()) {
      setToastSuccess("Reservation created successfully.");
      setToastError(null);
      return;
    }

    try {
      setLoading(true);
      setError(null);
      setHasSearched(true);

      const data = await searchWaiterReservations(accessToken, {
        date: toApiDate(selectedDate),
        time_from: toApiTimeFrom(selectedTime),
        table_name: tableName.trim(),
      });

      setReservations(data);
      setToastSuccess("Reservation created successfully.");
      setToastError(null);
    } catch (err) {
      setToastError(
        err instanceof Error
          ? `Reservation created, but refresh failed: ${err.message}`
          : "Reservation created, but refresh failed.",
      );
      setToastSuccess(null);
    } finally {
      setLoading(false);
    }
  };

  const handleCancelReservation = async (reservationId: string) => {
    if (!accessToken) {
      setError("Please log in to cancel reservation");
      return;
    }

    const confirmed = window.confirm(
      "Are you sure you want to cancel this reservation?",
    );
    if (!confirmed) return;

    try {
      setError(null);

      const updated = await cancelReservation(reservationId, accessToken);

      setReservations((prev) =>
        prev.map((item) =>
          item.reservation_id === updated.reservation_id ? updated : item,
        ),
      );

      if (
        selectedReservation &&
        selectedReservation.reservation_id === updated.reservation_id
      ) {
        setSelectedReservation(updated);
      }
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to cancel reservation",
      );
    }
  };

  const handleCloseEditModal = () => {
    setIsEditModalOpen(false);
    setSelectedReservation(null);
  };

  const responseDateLabel =
    reservations.length > 0
      ? formatApiDate(reservations[0].date)
      : selectedDate
        ? formatApiDate(toApiDate(selectedDate))
        : "selected date";

  return (
    <>
      {(toastError || toastSuccess) && (
        <div
          className={`fixed top-4 right-4 z-50 max-w-md w-full flex items-start gap-4 p-4 rounded-lg shadow-lg ${
            toastSuccess
              ? "bg-[#eaffea] border border-[#00ad0c]"
              : "bg-[#fde8e8] border border-[#b70b0b]"
          }`}
        >
          <div className="flex-shrink-0">
            {toastSuccess ? (
              <span className="inline-flex items-center justify-center w-8 h-8 rounded-full bg-[#00ad0c]">
                <svg
                  className="w-5 h-5 text-white"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth={2}
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M5 13l4 4L19 7"
                  />
                </svg>
              </span>
            ) : (
              <span className="inline-flex items-center justify-center w-8 h-8 rounded-full bg-[#b70b0b]">
                <svg
                  className="w-5 h-5 text-white"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth={2}
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </span>
            )}
          </div>
          <div>
            <div className="font-semibold text-lg text-black">
              {toastSuccess ? "Success" : "Error"}
            </div>
            <div className="text-black mt-1">{toastSuccess ?? toastError}</div>
          </div>
          <button
            type="button"
            onClick={() => {
              setToastError(null);
              setToastSuccess(null);
            }}
            aria-label="Close notification"
            className="ml-auto text-2xl cursor-pointer font-bold text-black hover:text-gray-700 focus:outline-none"
          >
            <span className="pi pi-times text-lg" />
          </button>
        </div>
      )}
      <Header />

      <div
        className="bg-cover bg-center"
        style={{ backgroundImage: `url(${subheading})` }}
      >
        <div className="max-w-[1440px] mx-auto px-10 py-[18px] flex justify-between items-center">
          <h2 className="font-medium text-2xl leading-10 tracking-normal align-middle text-white">
            {user && `Hello, ${user.username} (${user.role})`}
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
              disabled={
                tablesLoading ||
                !hasWaiterContext ||
                visibleTableOptions.length === 0
              }
            >
              <option value="">
                {tablesLoading ? "Loading tables..." : "Select table"}
              </option>
              {visibleTableOptions.map((tableNumber) => (
                <option key={tableNumber} value={String(tableNumber)}>
                  Table {tableNumber}
                </option>
              ))}
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
          {visibleTablesError ? (
            <p className="text-center text-red-500">{visibleTablesError}</p>
          ) : null}

          <div className="flex items-center justify-between gap-4">
            <p className="text-lg font-medium text-[#232323]">
              {reservations.length} reservations for {responseDateLabel}
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
                <div
                  key={reservation.reservation_id}
                  id={`reservation-${reservation.reservation_id}`}
                >
                  <ReservationCard
                    reservation={reservation}
                    onEdit={handleEditReservation}
                    onCancel={handleCancelReservation}
                    showCustomerId={true}
                  />
                </div>
              ))}
            </div>
          )}
        </div>
      </Layout>

      {selectedReservation && isEditModalOpen ? (
        <EditReservationModal
          reservation={selectedReservation}
          isSubmitting={isEditSubmitting}
          submitError={error}
          onClose={handleCloseEditModal}
          onSubmit={handleSubmitEdit}
        />
      ) : null}

      {isModalOpen && (
        <NewReservationModal
          onClose={() => setIsModalOpen(false)}
          onSubmit={() => {
            setIsModalOpen(false);
            void handleReservationCreated();
          }}
        />
      )}
    </>
  );
};

export default WaiterReservations;
