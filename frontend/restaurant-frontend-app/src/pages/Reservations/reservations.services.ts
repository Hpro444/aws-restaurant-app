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

export type BackendValidationErrorE = {
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

export type FeedbackTab = "Service" | "Culinary Experience";
export type FeedbackType = "service" | "culinary";

export interface WaiterData {
  name: string;
  role: string;
  avatar: string;
  rating: number;
}

export interface FeedbackContextResponse {
  reservation_id: string;
  waiter_id: string;
  waiter_name: string;
  waiter_image_url: string;
  waiter_avg_rating: number;
}

export interface FeedbackFormState {
  selectedTab: FeedbackTab;
  rating: number;
  comments: string;
}

export interface BackendValidationError {
  message?: string;
}

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

export const mapTabToType = (tab: FeedbackTab): FeedbackType =>
    tab === "Service" ? "service" : "culinary";

export const handleSubmit = async (
  setSubmitError: React.Dispatch<React.SetStateAction<string | null>>,
  reservationId: string | null,
  accessToken: string | null,
  form: FeedbackFormState,
  setIsSubmitting: React.Dispatch<React.SetStateAction<boolean>>,
  onHide: () => void,
): Promise<void> => {
  if (!reservationId) {
    setSubmitError("Reservation id is required.");
    return;
  }

  if (!accessToken) {
    setSubmitError("Please log in to submit feedback.");
    return;
  }

  if (form.rating < 1 || form.rating > 5) {
    setSubmitError("Please select a rating from 1 to 5.");
    return;
  }

  try {
    setIsSubmitting(true);
    setSubmitError(null);

    const response = await fetch(`${getApiBaseUrl()}/feedbacks`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${accessToken}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        reservation_id: reservationId,
        type: mapTabToType(form.selectedTab),
        rating: form.rating,
        comment: form.comments,
      }),
    });

    const data: unknown = await response.json().catch(() => null);

    if (!response.ok) {
      throw new Error(getFeedbackErrorMessage(response.status, data));
    }

    onHide();
  } catch (err) {
    setSubmitError(
      err instanceof Error ? err.message : "Failed to submit feedback.",
    );
  } finally {
    setIsSubmitting(false);
  }
};

export const fetchWaiterContext = async (
  setIsWaiterLoading: React.Dispatch<React.SetStateAction<boolean>>,
  setWaiterError: React.Dispatch<React.SetStateAction<string | null>>,
  setWaiterData: React.Dispatch<React.SetStateAction<WaiterData | null>>,
  reservationId: string,
  accessToken: string,
  controller: AbortController,
) => {
  try {
    setIsWaiterLoading(true);
    setWaiterError(null);
    setWaiterData(null);

    const response = await fetch(
      `${getApiBaseUrl()}/feedbacks/context/${encodeURIComponent(reservationId)}`,
      {
        method: "GET",
        headers: {
          Authorization: `Bearer ${accessToken}`,
          "Content-Type": "application/json",
        },
        signal: controller.signal,
      },
    );

    const payload: unknown = await response.json().catch(() => null);

    if (!response.ok) {
      throw new Error(getWaiterContextErrorMessage(response.status, payload));
    }

    const data = payload as FeedbackContextResponse;

    setWaiterData({
      name: data.waiter_name,
      role: "Waiter",
      avatar: data.waiter_image_url,
      rating: data.waiter_avg_rating,
    });
  } catch (err) {
    if ((err as Error).name === "AbortError") return;

    setWaiterData(null);
    setWaiterError(
      err instanceof Error ? err.message : "Failed to load waiter info.",
    );
  } finally {
    setIsWaiterLoading(false);
  }
};

export const getWaiterContextErrorMessage = (
  status: number,
  payload: unknown,
): string => {
  const maybe = payload as Record<string, unknown> | null;

  const directMessage =
    (typeof maybe?.message === "string" && maybe.message) ||
    (typeof maybe?.error === "string" && maybe.error);

  if (directMessage) return directMessage;

  switch (status) {
    case 401:
      return "Unauthorized. Please log in again.";
    case 403:
      return "Forbidden. You are not allowed to access feedback context.";
    case 404:
      return "Feedback context was not found for this reservation.";
    default:
      return "Failed to load waiter info.";
  }
};

export const getFeedbackErrorMessage = (
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
      return "Forbidden. You are not allowed to leave feedback.";
    case 404:
      return "Reservation was not found.";
    case 409:
      return "Feedback already exists for this reservation.";
    case 422:
      return "Validation failed. Please check provided values.";
    default:
      return "Failed to submit feedback.";
  }
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
