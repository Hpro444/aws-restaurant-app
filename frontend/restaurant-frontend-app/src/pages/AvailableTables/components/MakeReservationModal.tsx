import { useState } from "react";
import { formatDate, formatTime } from "../../../utils/reservationHelpers";
import { createBooking, toUtcIsoDatetime } from "../availableTables.services";
import { useAuth } from "../../../context/AuthContext";
import ReservationConfirmModal from "./ReservationConfirmModal";
import { useNavigate } from "react-router-dom";
import type {
  AvailableSlot,
  CreateBookingResponse,
  ReservationResult,
} from "../../../types/location";

export type MakeReservationModalProps = {
  slot: AvailableSlot;
  allSlots: AvailableSlot[];
  locationAddress: string;
  locationId: string;
  tableNumber: number;
  tableCapacity: number;
  date: string;
  initialGuests: number;
  onClose: () => void;
  onSelectSlot: (slot: AvailableSlot) => void;
  onReservationResult?: (result: ReservationResult) => void;
};

const MakeReservationModal = ({
  slot,
  allSlots,
  locationAddress,
  locationId,
  tableNumber,
  tableCapacity,
  date,
  initialGuests,
  onClose,
  onSelectSlot,
  onReservationResult = () => {},
}: MakeReservationModalProps) => {
  const navigate = useNavigate();
  const { accessToken } = useAuth();
  const [guests, setGuests] = useState(
    Math.max(1, Math.min(initialGuests, tableCapacity)),
  );
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [successReservation, setSuccessReservation] =
    useState<CreateBookingResponse | null>(null);

  const increaseGuests = () => {
    setGuests((prev) => Math.min(tableCapacity, prev + 1));
  };

  const decreaseGuests = () => {
    setGuests((prev) => Math.max(1, prev - 1));
  };

  const handleMakeReservation = async () => {
    if (!accessToken) {
      const message = "You must be logged in to make a reservation.";
      setSubmitError(message);
      onReservationResult({ ok: false, message });
      return;
    }

    setIsSubmitting(true);
    setSubmitError(null);

    try {
      const response = await createBooking(
        {
          locationId,
          tableNumber,
          date,
          guestsNumber: guests,
          timeFrom: toUtcIsoDatetime(date, slot.start_time),
          timeTo: toUtcIsoDatetime(date, slot.end_time),
        },
        accessToken,
      );

      setSuccessReservation(response);
      onReservationResult({ ok: true, data: response });
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Failed to create reservation";
      setSubmitError(message);
      onReservationResult({ ok: false, message });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleConfirmModalClose = () => {
    setSuccessReservation(null);
    onClose();
  };

  const handleCancelReservation = () => {
    if (!successReservation) return;

    setSuccessReservation(null);
    onClose();
    navigate("/reservations", {
      state: {
        focusReservationId: successReservation.reservationId,
        reservationAction: "cancel",
      },
    });
  };

  const handleEditReservation = () => {
    if (!successReservation) return;

    setSuccessReservation(null);
    onClose();
    navigate("/reservations", {
      state: {
        openEditReservationId: successReservation.reservationId,
        reservationAction: "edit",
      },
    });
  };

  if (successReservation) {
    return (
      <ReservationConfirmModal
        reservation={successReservation}
        onClose={handleConfirmModalClose}
        onCancel={handleCancelReservation}
        onEdit={handleEditReservation}
      />
    );
  }

  return (
    <div
      className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-[496px] rounded-[24px] p-6 gap-10 shadow-[0_0_10px_4px_#DADADAB2] bg-[#F7F7F7] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div>
          <div className="flex justify-between items-center">
            <h2 className="font-medium text-2xl leading-[40px] align-middle tracking-normal">
              Make a Reservation
            </h2>
            <button onClick={onClose} className="cursor-pointer">
              <span className="pi pi-times" />
            </button>
          </div>
          <p className="font-light text-sm leading-[24px] tracking-normal max-w-[416px]">
            There are{" "}
            <span className="font-medium">{allSlots.length} slots</span>{" "}
            available at <span className="font-medium">{locationAddress}</span>,{" "}
            <span className="font-medium">Table {tableNumber}</span>, for{" "}
            <span className="font-medium">{formatDate(date)}</span>.
          </p>
        </div>

        <div className="flex flex-col gap-8">
          <div className="flex flex-col gap-6">
            <div>
              <h3 className="font-medium text-base leading-[32px] align-middle tracking-normal">
                Guests
              </h3>
              <p className="font-light text-sm leading-[24px] align-middle tracking-normal">
                Please specify the number of guests
              </p>
              <p className="font-light text-sm leading-[24px] align-middle tracking-normal">
                Table seating capacity: {tableCapacity} people
              </p>
            </div>

            <div className="flex justify-between py-4 px-6 border border-[#DADADA] rounded-lg">
              <div className="flex gap-2">
                <span className="pi pi-users text-lg" />
                <p className="font-medium text-sm leading-[24px] align-middle tracking-normal text-center">
                  Guests
                </p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={decreaseGuests}
                  disabled={guests <= 1 || isSubmitting}
                  className="w-10 h-8 flex items-center justify-center border-2 border-green-500 text-green-500 rounded-md cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  <span className="pi pi-minus" />
                </button>
                <span className="text-gray-800 w-4 text-center">{guests}</span>
                <button
                  onClick={increaseGuests}
                  disabled={guests >= tableCapacity || isSubmitting}
                  className="w-10 h-8 flex items-center justify-center border-2 border-green-500 text-green-500 rounded-md cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  <span className="pi pi-plus" />
                </button>
              </div>
            </div>
          </div>

          <div className="flex flex-col gap-4">
            <div className="flex flex-col gap-1">
              <h3 className="font-medium text-lg leading-[32px] align-middle tracking-normal">
                Time
              </h3>
              <p className="font-light text-sm leading-[24px] align-middle tracking-normal">
                Please choose your preferred time
              </p>
            </div>

            <select
              value={slot.slot_id}
              onChange={(e) => {
                const next = allSlots.find((s) => s.slot_id === e.target.value);
                if (next) onSelectSlot(next);
              }}
              disabled={isSubmitting}
              className="w-full border border-[#DADADA] rounded-lg p-3 bg-white disabled:opacity-70"
            >
              {allSlots.map((s) => (
                <option key={s.slot_id} value={s.slot_id}>
                  {formatTime(s.start_time)} - {formatTime(s.end_time)}
                </option>
              ))}
            </select>
          </div>
        </div>

        {submitError ? (
          <p className="text-[#B70B0B] text-sm font-medium">{submitError}</p>
        ) : null}

        <button
          onClick={handleMakeReservation}
          disabled={isSubmitting}
          className="cursor-pointer bg-[#00ad0c] text-white rounded-[8px] py-4 font-bold text-sm leading-[24px] tracking-normal text-center align-middle disabled:opacity-60 disabled:cursor-not-allowed"
        >
          {isSubmitting ? "Making reservation..." : "Make Reservation"}
        </button>
      </div>
    </div>
  );
};

export default MakeReservationModal;
