import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../../context/AuthContext";
import { getReservations } from "./reservations.services";
import ReservationCard from "./components/ReservationCard";
import Header from "../../components/header";
import logoWhite from "../../assets/logoWhite.png";
import subheading from "../../assets/reservations/subheading.png";
import Layout from "../../components/layout";
import NoResults from "./components/NoResults";
import type { ReservationResponse } from "../../types/location";

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
      console.log(data);
      setReservations(Array.isArray(data) ? data : []);
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

  const handleEditReservation = (reservation: ReservationResponse) => {
    console.log("Edit reservation:", reservation);
  };

  const handleLeaveFeedback = (reservationId: string) => {
    console.log("Leave feedback for reservation:", reservationId);
  };

  return (
    <>
      <Header />

      <div
        className="bg-cover bg-center"
        style={{
          backgroundImage: `url(${subheading})`,
        }}
      >
        <div className="max-w-[1440px] mx-auto px-10 py-[18px] flex justify-between items-center">
          <h2 className="font-medium text-2xl leading-10 tracking-normal align-middle text-white">
            {user?.username
              ? `Hello, ${user.username} (${user.role})`
              : "Hello, Customer"}
          </h2>
          <div>
            <img src={logoWhite} alt="Logo" />
          </div>
        </div>
      </div>
      <Layout>
        {loading ? (
          <p className="col-span-3 text-center text-gray-500">
            Loading reservations...
          </p>
        ) : error ? (
          <p className="col-span-3 text-center text-red-500">{error}</p>
        ) : reservations.length === 0 ? (
          <NoResults />
        ) : (
          <div className="grid gap-8 grid-cols-3">
            {reservations.map((reservation) => (
              <ReservationCard
                key={reservation.reservation_id}
                reservation={reservation}
                onEdit={handleEditReservation}
                onFeedback={handleLeaveFeedback}
              />
            ))}
          </div>
        )}
      </Layout>
    </>
  );
};

export default ReservationsPage;
