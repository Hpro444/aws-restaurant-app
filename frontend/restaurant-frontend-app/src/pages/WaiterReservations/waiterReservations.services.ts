import type { Nullable } from "primereact/ts-helpers";
import getApiBaseUrl from "../../config/GetApiBaseUrl";
import type { ReservationResponse } from "../../types/location";

export interface WaiterReservationApiItem {
  reservationId: string;
  customerId: string;
  location_address: string;
  tableNumber: number;
  date: string;
  timeFrom: string;
  timeTo: string;
  guestsNumber: number;
}

export type CustomerType = "visitor" | "existing";

export const apiDateToDate = (apiDate: string): Nullable<Date> => {
  if (!apiDate) return null;
  const [year, month, day] = apiDate.split("-").map(Number);
  if (!year || !month || !day) return null;
  return new Date(year, month - 1, day);
};

export interface CustomerApiItem {
  user_name: string;
  email: string;
  customer_id?: string;
  customerId?: string;
  user_id?: string;
  id?: string;
}

export interface CustomerOption {
  customerId: string;
  userName: string;
  email: string;
}

export interface NewReservationPayload {
  customerType: CustomerType;
  customerName: string;
  guests: number;
  date: string;
  fromTime: string;
  toTime: string;
  table: string;
}

export interface NewReservationFormState {
  customerType: CustomerType;
  customerName: string;
  selectedCustomer: CustomerOption | null;
  guests: number;
  date: string;
  fromTime: string;
  toTime: string;
  table: string;
}

export interface WaiterReservationsApiResponse {
  reservations: WaiterReservationApiItem[];
}

export interface WaiterLocation {
  location_id: string;
  location_address: string;
}

export interface WaiterSearchParams {
  date: string;
  time_from: string;
  table_name: string;
}

interface CreateReservationBaseRequest {
  locationId: string;
  tableNumber: number;
  date: string;
  guestsNumber: number;
  timeFrom: string;
  timeTo: string;
}

export interface CreateReservationForVisitorRequest extends CreateReservationBaseRequest {
  existingCustomer: false;
  clientName: string;
}

export interface CreateReservationForExistingCustomerRequest extends CreateReservationBaseRequest {
  existingCustomer: true;
  customerId: string;
}

export type CreateWaiterReservationRequest =
  | CreateReservationForVisitorRequest
  | CreateReservationForExistingCustomerRequest;

export interface CreateWaiterReservationResponse {
  reservationId: string;
  status: string;
  locationId: string;
  location_address: string;
  tableNumber: number;
  date: string;
  timeFrom: string;
  timeTo: string;
  guestsNumber: number;
}

export interface ValidSlotTimesResponse {
  start_times: string[];
  end_times: string[];
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

const isStringArray = (value: unknown): value is string[] => {
  return Array.isArray(value) && value.every(isString);
};

const isValidSlotTimesResponse = (
  value: unknown,
): value is ValidSlotTimesResponse => {
  if (!isRecord(value)) return false;
  return isStringArray(value.start_times) && isStringArray(value.end_times);
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

const isWaiterLocation = (value: unknown): value is WaiterLocation => {
  if (!isRecord(value)) return false;
  return isString(value.location_id) && isString(value.location_address);
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
  status: "RESERVED",
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
    can_leave_feedback: false,
    can_update_feedback: false,
  },
});

export const fetchWaiterLocation = async (
  accessToken: string,
): Promise<WaiterLocation> => {
  const response = await fetch(`${getApiBaseUrl()}/users/waiter/location`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });

  const payload: unknown = await response.json().catch(() => null);

  if (!response.ok) {
    const fallback = `Failed to fetch waiter location (${response.status})`;
    throw new Error(getErrorMessageFromPayload(payload, fallback));
  }

  if (!isWaiterLocation(payload)) {
    throw new Error("Invalid waiter location data");
  }

  return payload;
};

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

interface LocationTableApiItem {
  table_number: number;
}

type LocationTablesApiResponse =
  | LocationTableApiItem[]
  | { tables: LocationTableApiItem[] };

const isLocationTableApiItem = (
  value: unknown,
): value is LocationTableApiItem => {
  if (!isRecord(value)) return false;
  return isNumber(value.table_number);
};

export const parseLocationTables = (payload: unknown): number[] => {
  if (Array.isArray(payload)) {
    return payload
      .filter(isLocationTableApiItem)
      .map((item) => item.table_number);
  }

  if (isRecord(payload) && Array.isArray(payload.tables)) {
    return payload.tables
      .filter(isLocationTableApiItem)
      .map((item) => item.table_number);
  }

  return [];
};

export const getLocationTables = async (
  accessToken: string,
  locationId: string,
): Promise<number[]> => {
  if (!locationId.trim()) {
    throw new Error("Location id is required");
  }

  const response = await fetch(
    `
${getApiBaseUrl()}/locations/${encodeURIComponent(locationId)}/tables`,
    {
      method: "GET",
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    },
  );

  const payload: unknown = await response.json().catch(() => null);

  if (!response.ok) {
    const fallback = `Failed to fetch location tables (${response.status})`;
    throw new Error(getErrorMessageFromPayload(payload, fallback));
  }

  const tableNumbers = parseLocationTables(
    payload as LocationTablesApiResponse,
  );

  return Array.from(new Set(tableNumbers)).sort((a, b) => a - b);
};

export const getValidSlotTimes = async (
  accessToken: string,
  locationId: string,
): Promise<ValidSlotTimesResponse> => {
  if (!locationId.trim()) {
    throw new Error("Location id is required");
  }

  const response = await fetch(
    `${getApiBaseUrl()}/locations/${encodeURIComponent(locationId)}/valid-slot-times`,
    {
      method: "GET",
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    },
  );

  const payload: unknown = await response.json().catch(() => null);

  if (!response.ok) {
    const fallback = `Failed to fetch valid slot times (${response.status})`;
    throw new Error(getErrorMessageFromPayload(payload, fallback));
  }

  if (!isValidSlotTimesResponse(payload)) {
    throw new Error("Invalid valid slot times response format");
  }

  return payload;
};

export const createWaiterReservation = async (
  accessToken: string,
  payload: CreateWaiterReservationRequest,
): Promise<CreateWaiterReservationResponse> => {
  const response = await fetch(`${getApiBaseUrl()}/bookings/client`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  const body: unknown = await response.json().catch(() => null);

  if (!response.ok) {
    const fallback = `Failed to create reservation (${response.status})`;
    throw new Error(getErrorMessageFromPayload(body, fallback));
  }

  return body as CreateWaiterReservationResponse;
};

export const isDateOrNull = (value: unknown): value is Date | null => {
  return value === null || value instanceof Date;
};

export const formatApiDate = (apiDate: string): string => {
  const [year, month, day] = apiDate.split("-").map(Number);
  if (!year || !month || !day) return apiDate;
  const localDate = new Date(year, month - 1, day);

  return localDate.toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
};

export const toApiDate = (date: Date): string => {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
};

export const toApiTimeFrom = (selectedTime: Date): string => {
  const hours = String(selectedTime.getHours()).padStart(2, "0");
  const minutes = String(selectedTime.getMinutes()).padStart(2, "0");
  return `${hours}:${minutes}`;
};

export const getCustomerIdFromApiItem = (item: CustomerApiItem): string => {
  return item.customer_id || item.customerId || item.user_id || item.id || "";
};

export const isCustomerApiItem = (value: unknown): value is CustomerApiItem => {
  if (!isRecord(value)) return false;
  return isString(value.user_name) && isString(value.email);
};

export const dateToIsoString = (date: Nullable<Date>): string => {
  if (!date) return "";
  return date.toISOString().replace(/.\d{3}Z$/, "Z");
};

export const isoStringToDate = (iso: string): Nullable<Date> => {
  if (!iso) return null;
  return new Date(iso);
};
