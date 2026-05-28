import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../../context/AuthContext";
import {
  getReservations,
  type ReservationResponse,
} from "./reservations.services";
import ReservationCard from "./components/ReservationCard";
import Header from "../../components/header";
import logoWhite from "../../assets/logoWhite.png";
import subheading from "../../assets/reservations/subheading.png";
import Layout from "../../components/layout";
import NoResults from "./components/NoResults";

const mockReservations: ReservationResponse[] = [
  {
    id: "1",
    status: "Reserved",
    customerId: "cust-123",
    waiterId: undefined,
    locationId: "loc-456",
    tableNumber: 5,
    date: "2026-05-25",
    timeFrom: "7:00 PM",
    timeTo: "8:00 PM",
    guestsNumber: 4,
    allowedActions: {
      canEdit: true,
      canCancel: true,
    },
    cutoffReason: undefined,
  },
  {
    id: "2",
    status: "In Progress",
    customerId: "cust-123",
    waiterId: "waiter-789",
    locationId: "loc-456",
    tableNumber: 8,
    date: "2026-05-20",
    timeFrom: "6:30 PM",
    timeTo: "7:30 PM",
    guestsNumber: 2,
    allowedActions: {
      canEdit: false,
      canCancel: true,
    },
    cutoffReason: undefined,
  },
  {
    id: "3",
    status: "Finished",
    customerId: "cust-123",
    waiterId: "waiter-789",
    locationId: "loc-456",
    tableNumber: 3,
    date: "2026-05-15",
    timeFrom: "8:00 PM",
    timeTo: "9:00 PM",
    guestsNumber: 6,
    allowedActions: {
      canEdit: false,
      canCancel: false,
    },
    cutoffReason: undefined,
  },
  {
    id: "4",
    status: "Canceled",
    customerId: "cust-123",
    waiterId: undefined,
    locationId: "loc-456",
    tableNumber: 2,
    date: "2026-05-10",
    timeFrom: "7:30 PM",
    timeTo: "8:30 PM",
    guestsNumber: 3,
    allowedActions: {
      canEdit: false,
      canCancel: false,
    },
    cutoffReason: "Customer requested cancellation",
  },
];

const ReservationsPage = () => {
  const { accessToken, user, isAuthenticated } = useAuth();
  const [reservations, setReservations] = useState<ReservationResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchReservations = useCallback(async () => {
    if (!accessToken) {
      setError("Please log in to view your reservations");
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const data = await getReservations(accessToken);
      setReservations(data);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load reservations",
      );
    } finally {
      setLoading(false);
    }
  }, [accessToken]);

  useEffect(() => {
    if (isAuthenticated) {
      const timeoutId = window.setTimeout(() => {
        void fetchReservations();
      }, 0);

      return () => {
        window.clearTimeout(timeoutId);
      };
    }
  }, [isAuthenticated, fetchReservations]);

  //   const handleCancelReservation = async (reservationId: string) => {
  //     if (
  //       !accessToken ||
  //       !window.confirm("Are you sure you want to cancel this reservation?")
  //     ) {
  //       return;
  //     }

  //     try {
  //       setCancellingId(reservationId);
  //       await cancelReservation(reservationId, accessToken);

  //       // Update local state
  //       setReservations((prev) =>
  //         prev.map((reservation) =>
  //           reservation.id === reservationId
  //             ? { ...reservation, status: "Canceled" }
  //             : reservation,
  //         ),
  //       );
  //     } catch (err) {
  //       setError(
  //         err instanceof Error ? err.message : "Failed to cancel reservation",
  //       );
  //     } finally {
  //       setCancellingId(null);
  //     }
  //   };

  const handleEditReservation = (reservation: ReservationResponse) => {
    // Navigate to edit page or open modal
    console.log("Edit reservation:", reservation);
    // You can implement navigation here:
    // navigate(`/reservations/${reservation.id}/edit`);
  };

  const handleLeaveFeedback = (reservationId: string) => {
    // Navigate to feedback page or open modal
    console.log("Leave feedback for reservation:", reservationId);
    // You can implement navigation here:
    // navigate(`/reservations/${reservationId}/feedback`);
  };

  return (
    <>
      <Header />

      {/* Subheading */}
      <div
        className="bg-cover bg-center"
        style={{
          //   backgroundImage: `linear-gradient(rgba(0, 0, 0, 0.3), rgba(0, 0, 0, 0.3)), url(${subheading})`,
          backgroundImage: `url(${subheading})`,
          // backgroundBlendMode: "overlay",
        }}
      >
        <div className="max-w-[1440px] mx-auto px-10 py-[18px] flex justify-between items-center">
          {/* <Layout> */}
          <h2 className="font-medium text-2xl leading-10 tracking-normal align-middle text-white">
            {user?.username
              ? `Hello, ${user.username} (${user.role})`
              : "Hello, Customer"}
          </h2>
          <div>
            <img src={logoWhite} alt="Logo" />
          </div>
        </div>
        {/* </Layout> */}
      </div>
      <Layout>
        {loading && (
          <p className="col-span-3 text-center text-gray-500">
            Loading reservations...
          </p>
        )}
        {error && (
          <p className="col-span-3 text-center text-red-500">{error}</p>
        )}
        {!loading && !error && reservations.length === 0 && <NoResults />}
        {/* {reservations.length > 0 && ( */}
        <div className="grid gap-8 grid-cols-3">
          {/* {reservations.map((reservation) => (
              <ReservationCard
                key={reservation.id}
                reservation={reservation}
                onEdit={handleEditReservation}
                onFeedback={handleLeaveFeedback}
              />
            ))} */}
          {mockReservations.map((reservation) => (
            <ReservationCard
              key={reservation.id}
              reservation={reservation}
              onEdit={(res) => handleEditReservation(res)}
              onCancel={(id) => console.log("Cancel:", id)}
              onFeedback={(id) => handleLeaveFeedback(id)}
            />
          ))}
        </div>
      </Layout>
    </>
  );
};

export default ReservationsPage;
