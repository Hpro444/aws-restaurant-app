import { useMemo, useState } from "react";
import type {
  ReservationResponse,
  UpdateReservationPayload,
} from "../reservations.services";
import { formatDate, formatTime } from "../../../utils/reservationHelpers";

type EditReservationModalProps = {
  reservation: ReservationResponse;
  isSubmitting: boolean;
  submitError: string | null;
  onClose: () => void;
  onSubmit: (payload: UpdateReservationPayload) => Promise<void>;
};

const EditReservationModal = ({
  reservation,
  isSubmitting,
  submitError,
  onClose,
  onSubmit,
}: EditReservationModalProps) => {
  const [guests, setGuests] = useState<number>(reservation.guests_number);

  const canEdit = reservation.allowed_actions.can_edit;

  const maxGuests = 10;
  const minGuests = 1;

  const payload = useMemo<UpdateReservationPayload>(() => {
    const next: UpdateReservationPayload = {};

    if (canEdit && guests !== reservation.guests_number) {
      next.guestsNumber = guests;
    }

    return next;
  }, [canEdit, guests, reservation.guests_number]);

  const hasChanges = payload.guestsNumber !== undefined;

  const handleSave = async () => {
    if (!hasChanges) return;
    await onSubmit(payload);
  };

  return (
    <div
      className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-[496px] rounded-[24px] p-6 gap-8 shadow-[0_0_10px_4px_#DADADAB2] bg-[#F7F7F7] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div>
          <div className="flex justify-between items-center">
            <h2 className="font-medium text-2xl leading-[40px]">
              Edit Reservation
            </h2>
            <button onClick={onClose} className="cursor-pointer">
              <span className="pi pi-times text-xl" />
            </button>
          </div>
          <p className="font-light text-sm leading-[24px]">
            <span className="font-medium">{reservation.location_address}</span>,{" "}
            <span className="font-medium">
              Table {reservation.table_number}
            </span>
            ,{" "}
            <span className="font-medium">{formatDate(reservation.date)}</span>,{" "}
            <span className="font-medium">
              {formatTime(reservation.time_from)} -{" "}
              {formatTime(reservation.time_to)}
            </span>
          </p>
        </div>

        <div className="flex flex-col gap-6">
          <div className="flex flex-col gap-2">
            <h3 className="font-medium text-base leading-[28px]">Guests</h3>
          </div>

          <div className="flex justify-between py-4 px-6 border border-[#DADADA] rounded-lg">
            <div className="flex gap-2 items-center">
              <span className="pi pi-users text-lg" />
              <p className="font-medium text-sm">Guests</p>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() =>
                  setGuests((prev) => Math.max(minGuests, prev - 1))
                }
                disabled={!canEdit || isSubmitting || guests <= minGuests}
                className="w-10 h-8 flex items-center justify-center border-2 border-green-500 rounded-md disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <span className="pi pi-minus" />
              </button>
              <span className="w-6 text-center">{guests}</span>
              <button
                onClick={() =>
                  setGuests((prev) => Math.min(maxGuests, prev + 1))
                }
                disabled={!canEdit || isSubmitting || guests >= maxGuests}
                className="w-10 h-8 flex items-center justify-center border-2 border-green-500 rounded-md disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <span className="pi pi-plus" />
              </button>
            </div>
          </div>
        </div>

        {submitError ? (
          <p className="text-[#B70B0B] text-sm font-medium">{submitError}</p>
        ) : null}

        <div className="grid grid-cols-2 gap-4">
          <button
            onClick={onClose}
            disabled={isSubmitting}
            className="cursor-pointer rounded-[8px] py-3 border border-[#00ad0c] text-[#00ad0c] font-bold text-sm disabled:opacity-60"
          >
            Close
          </button>
          <button
            onClick={handleSave}
            disabled={isSubmitting || !hasChanges}
            className="cursor-pointer rounded-[8px] py-3 bg-[#00ad0c] text-white font-bold text-sm disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {isSubmitting ? "Saving..." : "Save Changes"}
          </button>
        </div>
      </div>
    </div>
  );
};

export default EditReservationModal;
