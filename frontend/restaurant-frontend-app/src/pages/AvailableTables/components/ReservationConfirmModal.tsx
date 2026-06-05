import type { CreateBookingResponse } from "../availableTables.services";
import close_icon from "../../../assets/close_icon.png";
import { formatDate, formatSlotTime } from "../../../utils/reservationHelpers";

type ReservationConfirmModalProps = {
  reservation: CreateBookingResponse;
  onClose: () => void;
  onCancel?: () => void;
  onEdit?: () => void;
};

const ReservationConfirmModal = ({
  reservation,
  onClose,
  onCancel,
  onEdit,
}: ReservationConfirmModalProps) => {
  return (
    <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4">
      <div className="w-full max-w-[496px] rounded-[24px] gap-10 p-6 shadow-[0_0_10px_4px_#DADADAB2] bg-[#F7F7F7] flex flex-col">
        <div className="flex justify-between items-center">
          <h2 className="font-medium text-2xl leading-[40px] align-middle tracking-normal">
            Reservation Confirmed!
          </h2>
          <button onClick={onClose} className="cursor-pointer">
            <img src={close_icon} alt="Close" />
          </button>
        </div>
        <div className="flex flex-col gap-3 font-light text-sm leading-[24px] tracking-normal align-middle">
          <p>
            Your table reservation at{" "}
            <span className="font-medium">{reservation.location_address}</span>{" "}
            for{" "}
            <span className="font-medium">
              {reservation.guestsNumber} people
            </span>{" "}
            on{" "}
            <span className="font-medium">{formatDate(reservation.date)}</span>,
            from{" "}
            <span className="font-medium">
              {formatSlotTime(reservation.timeFrom)}
            </span>{" "}
            to{" "}
            <span className="font-medium">
              {formatSlotTime(reservation.timeTo)}
            </span>{" "}
            at{" "}
            <span className="font-medium">Table {reservation.tableNumber}</span>{" "}
            has been successfully made.
          </p>
          <p>
            We look forward to welcoming you at{" "}
            <span className="font-medium">{reservation.location_address}</span>.
          </p>
          <p>
            If you need to modify or cancel your reservation, you can do so up
            to 30 min. before the reservation time.
          </p>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <button
            onClick={onCancel}
            className="rounded-[8px] py-2 border border-[#00ad0c] text-[#00ad0c] font-bold text-sm leading-[24px] tracking-normal text-center align-middle cursor-pointer hover:bg-green-50"
          >
            Cancel Reservation
          </button>
          <button
            onClick={onEdit}
            className="rounded-[8px] py-2 bg-[#00ad0c] text-white font-bold text-sm leading-[24px] tracking-normal text-center align-middle cursor-pointer hover:bg-green-600"
          >
            Edit Reservation
          </button>
        </div>
      </div>
    </div>
  );
};

export default ReservationConfirmModal;
