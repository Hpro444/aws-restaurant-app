import getApiBaseUrl from "../../config/GetApiBaseUrl";
import type {
  ApiErrorResponse,
  LoginPayload,
  LoginResponse,
} from "../../types/auth";

const isApiErrorResponse = (value: unknown): value is ApiErrorResponse => {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  const maybe = value as Record<string, unknown>;
  return typeof maybe.message === "string" || typeof maybe.error === "string";
};

export const loginUser = async (data: LoginPayload): Promise<LoginResponse> => {
  const response = await fetch(getApiBaseUrl() + "/auth/sign-in", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });

  const payload: unknown = await response.json().catch(() => null);

  if (!response.ok) {
    const backendMessage = isApiErrorResponse(payload)
      ? payload.message || payload.error
      : undefined;

    throw new Error(backendMessage || "Login failed");
  }

  return payload as LoginResponse;
};
