import getApiBaseUrl from "../../config/GetApiBaseUrl";
import type { GetTablesParams, GetTablesResponse, LocationSelectOption } from "../../types/location";

export const getLocationSelectOptions = async (
  accessToken?: string,
): Promise<LocationSelectOption[]> => {
  const response = await fetch(`${getApiBaseUrl()}/locations/select-options`, {
    method: "GET",
    headers: {
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
    },
  });

  const payload: unknown = await response.json().catch(() => null);

  if (!response.ok) {
    const maybe = payload as Record<string, unknown> | null;
    const message =
      (typeof maybe?.message === "string" && maybe.message) ||
      (typeof maybe?.error === "string" && maybe.error) ||
      `Failed to fetch location options (${response.status})`;
    throw new Error(message);
  }

  return payload as LocationSelectOption[];
};

export const getAvailableTables = async (
  params: GetTablesParams,
  accessToken: string,
): Promise<GetTablesResponse> => {
  const query = new URLSearchParams({
    location_id: params.location_id,
    date: params.date,
    guests_number: String(params.guests_number),
    ...(params.from_time ? { from_time: params.from_time } : {}),
    ...(params.to_time ? { to_time: params.to_time } : {}),
  });

  const response = await fetch(
    `${getApiBaseUrl()}/bookings/tables?${query.toString()}`,
    {
      method: "GET",
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    },
  );

  const payload: unknown = await response.json().catch(() => null);

  if (!response.ok) {
    const maybe = payload as Record<string, unknown> | null;
    const message =
      (typeof maybe?.message === "string" && maybe.message) ||
      (typeof maybe?.error === "string" && maybe.error) ||
      `Failed to fetch tables (${response.status})`;
    throw new Error(message);
  }

  return payload as GetTablesResponse;
};

export interface CreateBookingPayload {
  locationId: string;
  tableNumber: number;
  date: string;
  guestsNumber: number;
  timeFrom: string;
  timeTo: string;
}

export interface CreateBookingResponse {
  reservationId: string;
  status: "RESERVED";
  locationId: string;
  tableNumber: number;
  date: string;
  timeFrom: string;
  timeTo: string;
  guestsNumber: number;
}

export const createBooking = async (
  payload: CreateBookingPayload,
  accessToken: string,
): Promise<CreateBookingResponse> => {
  const response = await fetch(`${getApiBaseUrl()}/bookings/client`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify(payload),
  });

  const data: unknown = await response.json().catch(() => null);

  if (!response.ok) {
    const maybe = data as Record<string, unknown> | null;
    const message =
      (typeof maybe?.message === "string" && maybe.message) ||
      (typeof maybe?.error === "string" && maybe.error) ||
      `Failed to create booking (${response.status})`;
    throw new Error(message);
  }

  return data as CreateBookingResponse;
};
