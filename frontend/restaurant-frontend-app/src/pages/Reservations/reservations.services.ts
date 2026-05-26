import getApiBaseUrl from "../../config/GetApiBaseUrl";

export interface AllowedActions {
  canEdit: boolean;
  canCancel: boolean;
}

export interface ReservationResponse {
  id: string; // reservationId
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

// const API_BASE_URL =
// "https://pga9t9qu63.execute-api.eu-west-3.amazonaws.com/api";

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

// export const cancelReservation = async (
//   reservationId: string,
//   accessToken: string,
// ): Promise<void> => {
//   const response = await fetch(
//     `${getApiBaseUrl()}/reservations/${reservationId}/cancel`,
//     {
//       method: "PATCH",
//       headers: {
//         Authorization: `Bearer ${accessToken}`,
//         "Content-Type": "application/json",
//       },
//     },
//   );

//   if (!response.ok) {
//     throw new Error(`Failed to cancel reservation: ${response.statusText}`);
//   }
// };

// export const updateReservation = async (
//   reservationId: string,
//   updateData: Partial<ReservationResponse>,
//   accessToken: string,
// ): Promise<ReservationResponse> => {
//   const response = await fetch(
//     `${getApiBaseUrl()}/reservations/${reservationId}`,
//     {
//       method: "PATCH",
//       headers: {
//         Authorization: `Bearer ${accessToken}`,
//         "Content-Type": "application/json",
//       },
//       body: JSON.stringify(updateData),
//     },
//   );

//   if (!response.ok) {
//     throw new Error(`Failed to update reservation: ${response.statusText}`);
//   }

//   return response.json();
// };
