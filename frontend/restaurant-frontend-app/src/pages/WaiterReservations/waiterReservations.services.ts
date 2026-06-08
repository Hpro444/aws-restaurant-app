import getApiBaseUrl from "../../config/GetApiBaseUrl";
import { type ReservationResponse } from "../Reservations/reservations.services";

interface WaiterReservationApiItem {
  reservationId: string;
  customerId: string;
  location_address: string;
  tableNumber: number;
  date: string;
  timeFrom: string;
  timeTo: string;
  guestsNumber: number;
}

interface WaiterReservationsApiResponse {
  reservations: WaiterReservationApiItem[];
}

export interface WaiterSearchParams {
  date: string;
  time_from: string;
  table_name: string;
}

const isRecord = (value: unknown): value is Record<string, unknown> => {
  return typeof value === "object" && value !== null;
};

const isString = (value: unknown): value is string => {
  return typeof value === "string";
};

const isNumber = (value: unknown): value is number => {
  return typeof value === "number" && Number.isFinite(value);
};

const isWaiterReservationApiItem = (
  value: unknown,
): value is WaiterReservationApiItem => {
  if (!isRecord(value)) return false;

  return (
    isString(value.reservationId) &&
    isString(value.customerId) &&
    isString(value.location_address) &&
    isNumber(value.tableNumber) &&
    isString(value.date) &&
    isString(value.timeFrom) &&
    isString(value.timeTo) &&
    isNumber(value.guestsNumber)
  );
};

const isWaiterReservationsApiResponse = (
  value: unknown,
): value is WaiterReservationsApiResponse => {
  if (!isRecord(value) || !Array.isArray(value.reservations)) return false;
  return value.reservations.every(isWaiterReservationApiItem);
};

const getErrorMessageFromPayload = (
  payload: unknown,
  fallback: string,
): string => {
  if (!isRecord(payload)) return fallback;

  if (isString(payload.message) && payload.message.trim()) {
    return payload.message;
  }

  if (isString(payload.error) && payload.error.trim()) {
    return payload.error;
  }

  return fallback;
};

const mapApiReservation = (
  item: WaiterReservationApiItem,
): ReservationResponse => ({
  reservation_id: item.reservationId,
  status: "Reserved",
  customer_id: item.customerId,
  location_address: item.location_address,
  table_number: item.tableNumber,
  date: item.date,
  time_from: item.timeFrom,
  time_to: item.timeTo,
  guests_number: item.guestsNumber,
  allowed_actions: {
    can_edit: true,
    can_cancel: true,
  },
});

export const searchWaiterReservations = async (
  accessToken: string,
  params: WaiterSearchParams,
): Promise<ReservationResponse[]> => {
  const query = new URLSearchParams({
    date: params.date,
    time_from: params.time_from,
    table_name: params.table_name,
  });

  const response = await fetch(
    `${getApiBaseUrl()}/reservations/waiter?${query.toString()}`,
    {
      method: "GET",
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    },
  );

  const payload: unknown = await response.json().catch(() => null);

  if (!response.ok) {
    const fallback = `Failed to fetch reservations (${response.status})`;
    throw new Error(getErrorMessageFromPayload(payload, fallback));
  }

  if (!isWaiterReservationsApiResponse(payload)) return [];

  return payload.reservations.map(mapApiReservation);
};
