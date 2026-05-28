import getApiBaseUrl from "../../config/GetApiBaseUrl";

export interface SignupPayload {
  first_name: string;
  last_name: string;
  password: string;
  email: string;
  confirmPassword: string;
}

export interface SignupResponse {
  message: string;
  user_id: string;
}

type ApiErrorResponse = {
  message?: string;
  error?: string;
};

const isApiErrorResponse = (value: unknown): value is ApiErrorResponse => {
  if (typeof value !== "object" || value === null) return false;
  const maybe = value as Record<string, unknown>;
  return typeof maybe.message === "string" || typeof maybe.error === "string";
};

const getSignupErrorMessage = (status: number, backendMessage?: string) => {
  if (backendMessage) return backendMessage;

  switch (status) {
    case 400:
      return "Invalid signup data. Please check all fields.";
    case 401:
      return "You are not authorized to perform this action.";
    case 403:
      return "Access denied.";
    case 404:
      return "Signup service not found.";
    case 409:
      return "An account with this email already exists.";
    case 422:
      return "Validation failed. Please review your input.";
    case 429:
      return "Too many requests. Please try again later.";
    case 500:
      return "Server error. Please try again in a few minutes.";
    default:
      return "Signup failed. Please try again.";
  }
};

export const signupUser = async (
  data: SignupPayload,
): Promise<SignupResponse> => {
  try {
    const response = await fetch(`${getApiBaseUrl()}/auth/sign-up`, {
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

      throw new Error(getSignupErrorMessage(response.status, backendMessage));
    }

    return payload as SignupResponse;
  } catch (error) {
    console.error("Signup error:", error);
    throw error;
  }
};
