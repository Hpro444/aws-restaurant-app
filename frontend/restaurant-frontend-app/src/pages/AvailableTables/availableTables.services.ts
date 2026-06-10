import getApiBaseUrl from "../../config/GetApiBaseUrl";
import type {
  CreateBookingPayload,
  CreateBookingResponse,
  GetTablesParams,
  GetTablesResponse,
  LocationSelectOption,
} from "../../types/location";

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

export const isDateOrNull = (date: unknown): date is Date | null => {
  return date === null || date instanceof Date;
};

export const toLocalApiDate = (date: Date): string => {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
};

export const toCalendarDate = (value: string): Date | null => {
  if (!value) return null;
  const [y, m, d] = value.split("-").map(Number);
  if (!y || !m || !d) return null;

  const localDate = new Date(y, m - 1, d);
  return Number.isNaN(localDate.getTime()) ? null : localDate;
};

export const toCalendarTime = (value: string): Date | null => {
  if (!value) return null;

  const [hRaw, mRaw] = value.split(":");
  const h = Number(hRaw);
  const m = mRaw !== undefined ? Number(mRaw) : 0;

  if (Number.isNaN(h) || Number.isNaN(m)) return null;

  const date = new Date();
  date.setHours(h, m, 0, 0);
  return date;
};

export const toTimeString = (date: Date): string => {
  const hh = String(date.getHours()).padStart(2, "0");
  const mm = String(date.getMinutes()).padStart(2, "0");
  return `${hh}:${mm}`;
};

export const toApiFromTime = (
  date: string,
  time: string,
): string | undefined => {
  if (!date || !time) return undefined;

  const parts = time.split(":");
  const hour = (parts[0] || "").padStart(2, "0");
  const minute = (parts[1] || "00").padStart(2, "0");

  if (!hour) return undefined;

  return date + "T" + hour + ":" + minute + ":00Z";
};

export const stripMilliseconds = (iso: string): string =>
  iso.replace(/\.\d{3}Z$/, "Z");

export const toUtcIsoDatetime = (date: string, value: string): string => {
  const trimmed = value.trim();

  const timeOnly = /^([01]\d|2[0-3]):([0-5]\d)(?::([0-5]\d))?$/.exec(trimmed);
  if (timeOnly) {
    const [, hh, mm, ss] = timeOnly;
    return `${date}T${hh}:${mm}:${ss ?? "00"}Z`;
  }

  const dateTimeNoZone =
    /^(\d{4}-\d{2}-\d{2})[T\s]([01]\d|2[0-3]):([0-5]\d)(?::([0-5]\d))?$/.exec(
      trimmed,
    );
  if (dateTimeNoZone) {
    const [, yyyyMmDd, hh, mm, ss] = dateTimeNoZone;
    return `${yyyyMmDd}T${hh}:${mm}:${ss ?? "00"}Z`;
  }

  const parsed = new Date(trimmed);
  if (!Number.isNaN(parsed.getTime())) {
    return stripMilliseconds(parsed.toISOString());
  }

  return `${date}T00:00:00Z`;
};
