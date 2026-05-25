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

// const API_BASE_URL =
//   "https://pga9t9qu63.execute-api.eu-west-3.amazonaws.com/api/auth";

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

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const result: SignupResponse = await response.json();
    return result;
  } catch (error) {
    console.error("Signup error:", error);
    throw error;
  }
};
