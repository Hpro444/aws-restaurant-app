import getApiBaseUrl from "../../config/GetApiBaseUrl";

export interface LoginPayload {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  username: string;
  role: "Customer" | "Waiter" | "Admin" | "Visitor";
}

export interface ApiErrorResponse {
  error?: string;
  message?: string;
}

// const API_BASE_URL =
//   "https://pga9t9qu63.execute-api.eu-west-3.amazonaws.com/api/auth";

const isApiErrorResponse = (value: unknown): value is ApiErrorResponse => {
  return typeof value === "object" && value !== null && "message" in value;
};

export const loginUser = async (data: LoginPayload): Promise<LoginResponse> => {
  const response = await fetch(`${getApiBaseUrl()}/auth/sign-in`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });

  const payload: unknown = await response.json().catch(() => null);

  if (!response.ok) {
    const message =
      isApiErrorResponse(payload) && typeof payload.message === "string"
        ? payload.message
        : `Login failed with status ${response.status}`;

    throw new Error(message);
  }

  return payload as LoginResponse;
};
