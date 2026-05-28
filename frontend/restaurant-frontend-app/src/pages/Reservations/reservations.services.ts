import getApiBaseUrl from "../../config/GetApiBaseUrl";

export interface AllowedActions {
  can_edit: boolean;
  can_cancel: boolean;
}

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

  return response.json();
};
