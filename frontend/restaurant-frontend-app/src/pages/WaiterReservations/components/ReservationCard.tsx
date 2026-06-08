import { type ReservationResponse } from "../../Reservations/reservations.services";
import {
  formatDate,
  formatTime,
} from "../../../utils/reservationHelpers";

const LocationIcon = () => (
  <svg
    className="w-5 h-5 text-green-600"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    viewBox="0 0 24 24"
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M12 21c-4.418 0-8-4.03-8-9a8 8 0 1116 0c0 4.97-3.582 9-8 9z"
    />
    <circle cx="12" cy="12" r="3" />
  </svg>
);

const CalendarIcon = () => (
  <svg
    className="w-5 h-5 text-green-600"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    viewBox="0 0 24 24"
  >
    <rect x="3" y="4" width="18" height="18" rx="2" />
    <path d="M16 2v4M8 2v4M3 10h18" />
  </svg>
);

const ClockIcon = () => (
  <svg
    className="w-5 h-5 text-green-600"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    viewBox="0 0 24 24"
  >
    <circle cx="12" cy="12" r="10" />
    <path d="M12 6v6l4 2" />
  </svg>
);

const UserIcon = () => (
  <svg
    className="w-5 h-5 text-green-600"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    viewBox="0 0 24 24"
  >
    <circle cx="12" cy="8" r="4" />
    <path d="M6 20v-2a6 6 0 0112 0v2" />
  </svg>
);

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
          <LocationIcon />
          <span className="text-gray-800 font-medium">
            {reservation.location_address ?? "Unknown location"}
          </span>
        </div>
        <div className="text-gray-700 font-medium">
          Table {reservation.table_number ?? "-"}
        </div>
      </div>

      <div className="space-y-3 mb-6">
        <div className="flex items-center gap-2">
          <CalendarIcon />
          <span className="text-gray-700">{formatDate(reservation.date)}</span>
        </div>

        <div className="flex items-center gap-2">
          <ClockIcon />
          <span className="text-gray-700">
            {formatTime(reservation.time_from)} -{" "}
            {formatTime(reservation.time_to)}
          </span>
        </div>

        <div className="flex items-center gap-2">
          <UserIcon />
          <span className="text-gray-700">
            Customer {reservation.customer_id ?? "-"}
          </span>
        </div>

        <div className="flex items-center gap-2">
          <UserIcon />
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
