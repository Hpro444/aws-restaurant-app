import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../../context/AuthContext";
import {
  cancelReservation,
  getReservations,
  updateReservation,
  type UpdateReservationPayload,
} from "./reservations.services";
import ReservationCard from "./components/ReservationCard";
import Header from "../../components/header";
import logoWhite from "../../assets/logoWhite.png";
import subheading from "../../assets/reservations/subheading.png";
import Layout from "../../components/layout";
import NoResults from "./components/NoResults";
import type { ReservationResponse } from "../../types/location";
import EditReservationModal from "./components/EditReservationModal";
import { useLocation, useNavigate } from "react-router-dom";
import FeedbackModal from "./components/Feedback";

type ReservationsLocationState = {
  openEditReservationId?: string;
  focusReservationId?: string;
  reservationAction?: "edit" | "cancel";
};

const ReservationsPage = () => {
  const { accessToken, user, isAuthenticated } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const routeState = location.state as ReservationsLocationState | null;

  const openEditReservationId = routeState?.openEditReservationId;
  const focusReservationId = routeState?.focusReservationId;
  const reservationAction = routeState?.reservationAction;

  const [reservations, setReservations] = useState<ReservationResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedReservation, setSelectedReservation] =
    useState<ReservationResponse | null>(null);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isEditSubmitting, setIsEditSubmitting] = useState(false);
  const [isFeedbackModalOpen, setIsFeedbackModalOpen] = useState(false);
  const [feedbackReservationId, setFeedbackReservationId] = useState<
    string | null
  >(null);

  const routedEditReservation =
    reservationAction === "edit" && openEditReservationId
      ? (reservations.find(
          (item) => item.reservation_id === openEditReservationId,
        ) ?? null)
      : null;

  const routedCancelReservation =
    reservationAction === "cancel" && focusReservationId
      ? (reservations.find(
          (item) => item.reservation_id === focusReservationId,
        ) ?? null)
      : null;

  const modalReservation = isEditModalOpen
    ? selectedReservation
    : routedEditReservation;

  const isRouteDrivenEditOpen =
    !isEditModalOpen && Boolean(routedEditReservation);

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

  useEffect(() => {
    if (loading) return;

    if (routedCancelReservation) {
      const element = document.getElementById(
        `reservation-${routedCancelReservation.reservation_id}`,
      );
      element?.scrollIntoView({ behavior: "smooth", block: "center" });

      navigate("/reservations", { replace: true, state: null });
      return;
    }

    if (
      (reservationAction === "cancel" &&
        focusReservationId &&
        !routedCancelReservation) ||
      (reservationAction === "edit" &&
        openEditReservationId &&
        reservations.length > 0 &&
        !routedEditReservation)
    ) {
      navigate("/reservations", { replace: true, state: null });
    }
  }, [
    loading,
    reservationAction,
    focusReservationId,
    openEditReservationId,
    routedCancelReservation,
    routedEditReservation,
    reservations.length,
    navigate,
  ]);

  const handleEditReservation = (reservation: ReservationResponse) => {
    setError(null);
    setSelectedReservation(reservation);
    setIsEditModalOpen(true);
  };

  const handleSubmitEdit = async (payload: UpdateReservationPayload) => {
    const reservationToUpdate = modalReservation;

    if (!accessToken || !reservationToUpdate) {
      setError("Please log in to edit reservation");
      return;
    }

    try {
      setIsEditSubmitting(true);
      setError(null);

      const updated = await updateReservation(
        reservationToUpdate.reservation_id,
        payload,
        accessToken,
      );

      setReservations((prev) =>
        prev.map((item) =>
          item.reservation_id === updated.reservation_id ? updated : item,
        ),
      );

      setSelectedReservation(updated);

      if (isEditModalOpen) {
        setIsEditModalOpen(false);
      }

      if (isRouteDrivenEditOpen) {
        navigate("/reservations", { replace: true, state: null });
      }
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to update reservation",
      );
    } finally {
      setIsEditSubmitting(false);
    }
  };

  const handleLeaveFeedback = (reservationId: string) => {
    setFeedbackReservationId(reservationId);
    setIsFeedbackModalOpen(true);
  };

  const handleCloseFeedbackModal = () => {
    setIsFeedbackModalOpen(false);
    setFeedbackReservationId(null);
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

    if (isRouteDrivenEditOpen) {
      navigate("/reservations", { replace: true, state: null });
    }
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
              <div
                key={reservation.reservation_id}
                id={`reservation-${reservation.reservation_id}`}
              >
                <ReservationCard
                  reservation={reservation}
                  onEdit={handleEditReservation}
                  onCancel={handleCancelReservation}
                  onFeedback={handleLeaveFeedback}
                />
              </div>
            ))}
          </div>
        )}
      </Layout>

      {modalReservation ? (
        <EditReservationModal
          reservation={modalReservation}
          isSubmitting={isEditSubmitting}
          submitError={error}
          onClose={handleCloseEditModal}
          onSubmit={handleSubmitEdit}
        />
      ) : null}

      {isFeedbackModalOpen && (
        <FeedbackModal
          visible={isFeedbackModalOpen}
          onHide={handleCloseFeedbackModal}
          reservationId={feedbackReservationId}
          accessToken={accessToken}
        />
      )}
    </>
  );
};

export default ReservationsPage;
