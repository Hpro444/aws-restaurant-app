import getApiBaseUrl from "../../config/GetApiBaseUrl";

export type ReservationStatus =
  | "RESERVED"
  | "IN_PROGRESS"
  | "CANCELLED"
  | "FINISHED";

export interface UpdateReservationPayload {
  guestsNumber?: number;
  status?: ReservationStatus;
}

type BackendValidationError = {
  field?: string;
  message?: string;
};

export interface AllowedActions {
  can_edit: boolean;
  can_cancel: boolean;
}

type BackendAllowedActions = {
  canEdit: boolean;
  canCancel: boolean;
};

export interface ReservationResponse {
  reservation_id: string;
  status: string;
  customer_id?: string;
  waiter_id?: string;
  location_id?: string;
  location_address?: string;
  table_number?: number;
  date: string;
  time_from: string;
  time_to: string;
  guests_number: number;
  allowed_actions: AllowedActions;
  cutoff_reason?: string;
}

type BackendReservation = {
  reservationId: string;
  status: string;
  customerId?: string;
  waiterId?: string;
  locationId?: string;
  location_address?: string;
  tableNumber?: number;
  date: string;
  timeFrom: string;
  timeTo: string;
  guestsNumber: number;
  allowedActions: BackendAllowedActions;
  cutoffReason?: string | null;
};

type BackendReservationsResponse = {
  reservations: BackendReservation[];
};

const mapReservation = (item: BackendReservation): ReservationResponse => ({
  reservation_id: item.reservationId,
  status: item.status,
  customer_id: item.customerId,
  waiter_id: item.waiterId,
  location_id: item.locationId,
  location_address: item.location_address,
  table_number: item.tableNumber,
  date: item.date,
  time_from: item.timeFrom,
  time_to: item.timeTo,
  guests_number: item.guestsNumber,
  allowed_actions: {
    can_edit: item.allowedActions?.canEdit ?? false,
    can_cancel: item.allowedActions?.canCancel ?? false,
  },
  cutoff_reason: item.cutoffReason ?? undefined,
});

export const getReservations = async (
  accessToken: string,
): Promise<ReservationResponse[]> => {
  const response = await fetch(`${getApiBaseUrl()}/bookings/client`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) {
    if (response.status === 401) {
      throw new Error("Unauthorized - Please log in again");
    }
    throw new Error(`Failed to fetch reservations: ${response.statusText}`);
  }

  const data = (await response.json()) as BackendReservationsResponse;
  return Array.isArray(data?.reservations)
    ? data.reservations.map(mapReservation)
    : [];
};

const getUpdateReservationErrorMessage = (
  status: number,
  payload: unknown,
): string => {
  const maybe = payload as Record<string, unknown> | null;

  if (status === 422 && Array.isArray(maybe?.errors)) {
    const messages = (maybe.errors as BackendValidationError[])
      .map((e) => e.message)
      .filter((m): m is string => Boolean(m));

    if (messages.length > 0) {
      return messages.join(", ");
    }
  }

  const directMessage =
    (typeof maybe?.message === "string" && maybe.message) ||
    (typeof maybe?.error === "string" && maybe.error);

  if (directMessage) return directMessage;

  switch (status) {
    case 401:
      return "Unauthorized. Please log in again.";
    case 403:
      return "Forbidden. You are not allowed to edit this reservation.";
    case 404:
      return "Reservation was not found.";
    case 422:
      return "Validation failed. Please check provided values.";
    default:
      return `Failed to update reservation (${status})`;
  }
};

export const updateReservation = async (
  id: string,
  payload: UpdateReservationPayload,
  accessToken: string,
): Promise<ReservationResponse> => {
  if (!id) {
    throw new Error("Reservation id is required.");
  }

  if (payload.guestsNumber == null && payload.status == null) {
    throw new Error("At least one editable field must be provided.");
  }

  const response = await fetch(`${getApiBaseUrl()}/bookings/client/${id}`, {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  const data: unknown = await response.json().catch(() => null);

  if (!response.ok) {
    throw new Error(getUpdateReservationErrorMessage(response.status, data));
  }

  return mapReservation(data as BackendReservation);
};


const getCancelReservationErrorMessage = (
  status: number,
  payload: unknown,
): string => {
  const maybe = payload as Record<string, unknown> | null;

  if (status === 422 && Array.isArray(maybe?.errors)) {
    const messages = (maybe.errors as BackendValidationError[])
      .map((e) => e.message)
      .filter((m): m is string => Boolean(m));

    if (messages.length > 0) {
      return messages.join(", ");
    }
  }

  const directMessage =
    (typeof maybe?.message === "string" && maybe.message) ||
    (typeof maybe?.error === "string" && maybe.error);

  if (directMessage) return directMessage;

  switch (status) {
    case 401:
      return "Unauthorized. Please log in again.";
    case 403:
      return "Forbidden. You are not allowed to cancel this reservation.";
    case 404:
      return "Reservation was not found.";
    case 422:
      return "Validation failed. Reservation cannot be cancelled.";
    default:
      return `Failed to cancel reservation (${status})`;
  }
};

export const cancelReservation = async (
  id: string,
  accessToken: string,
): Promise<ReservationResponse> => {
  if (!id) {
    throw new Error("Reservation id is required.");
  }

  const response = await fetch(
    `${getApiBaseUrl()}/bookings/client/${id}/cancel`,
    {
      method: "DELETE",
      headers: {
        Authorization: `Bearer ${accessToken}`,
        "Content-Type": "application/json",
      },
    },
  );

  const data: unknown = await response.json().catch(() => null);

  if (!response.ok) {
    throw new Error(getCancelReservationErrorMessage(response.status, data));
  }

  return mapReservation(data as BackendReservation);
};