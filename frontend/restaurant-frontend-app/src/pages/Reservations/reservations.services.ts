import getApiBaseUrl from "../../config/GetApiBaseUrl";

export interface AllowedActions {
  canEdit: boolean;
  canCancel: boolean;
}

export interface ReservationResponse {
  id: string;
  status: string;
  customerId?: string;
  waiterId?: string;
  locationId?: string;
  tableNumber?: number;
  date: string;
  timeFrom: string;
  timeTo: string;
  guestsNumber: number;
  allowedActions: AllowedActions;
  cutoffReason?: string;
}

export const getReservations = async (
  accessToken: string,
): Promise<ReservationResponse[]> => {
  const response = await fetch(`${getApiBaseUrl()}/booking/client`, {
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
