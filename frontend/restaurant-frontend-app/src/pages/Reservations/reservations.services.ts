import getApiBaseUrl from "../../config/GetApiBaseUrl";
import type { ReservationResponse } from "../../types/location";

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
