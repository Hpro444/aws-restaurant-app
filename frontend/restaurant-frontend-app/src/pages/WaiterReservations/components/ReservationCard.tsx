import { type ReservationResponse } from "../../Reservations/reservations.services";
import { formatDate, formatTime } from "../../../utils/reservationHelpers";

interface ReservationCardProps {
  reservation: ReservationResponse;
  onCancel: (reservationId: string) => void;
  onEdit: (reservation: ReservationResponse) => void;
}

const ReservationCard = ({
  reservation,
  onCancel,
  onEdit,
}: ReservationCardProps) => {
  return (
    <div className="bg-white rounded-2xl shadow-md p-6 w-full max-w-md">
      <div className="flex justify-between items-start mb-4">
        <div className="flex items-center gap-2">
          <span className="pi pi-map-marker text-xl" />
          <span className="text-gray-800 font-medium">
            {reservation.location_address}
          </span>
        </div>
        <div className="text-gray-700 font-medium">
          Table {reservation.table_number ?? "-"}
        </div>
      </div>

      <div className="space-y-3 mb-6">
        <div className="flex items-center gap-2">
          <span className="pi pi-calendar text-xl" />
          <span className="text-gray-700">{formatDate(reservation.date)}</span>
        </div>

        <div className="flex items-center gap-2">
          <span className="pi pi-clock text-xl" />
          <span className="text-gray-700">
            {formatTime(reservation.time_from)} -{" "}
            {formatTime(reservation.time_to)}
          </span>
        </div>

        <div className="flex items-center gap-2">
          <span className="pi pi-user text-xl" />
          <span className="text-gray-700">
            Customer {reservation.customer_id ?? "-"}
          </span>
        </div>

        <div className="flex items-center gap-2">
          <span className="pi pi-users text-xl" />
          <span className="text-gray-700">
            {reservation.guests_number} Guests
          </span>
        </div>
      </div>

      <div className="flex justify-end gap-4">
        <button
          onClick={() => onCancel(reservation.reservation_id)}
          className="text-gray-500 font-medium hover:underline"
        >
          Cancel
        </button>
        <button
          onClick={() => onEdit(reservation)}
          className="bg-white border border-green-500 text-green-600 font-semibold px-6 py-2 rounded-xl hover:bg-green-50 transition"
        >
          Edit
        </button>
      </div>
    </div>
  );
};

export default ReservationCard;
