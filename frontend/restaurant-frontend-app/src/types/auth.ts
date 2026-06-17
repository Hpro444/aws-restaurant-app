import type { InputHTMLAttributes } from "react";

export type AuthUser = {
  username: string;
  role: LoginResponse["role"];
  waiterLocation?: {
    location_id: string;
    location_address: string;
  };
};

export type ViewerRole = "guest" | "customer" | "waiter" | "admin";

export type AuthContextValue = {
  user: AuthUser | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  viewerRole: ViewerRole;
  signIn: (payload: LoginPayload) => Promise<void>;
  signOut: () => void;
};

export type InputType = "text" | "email" | "password";

export type FieldConfig = {
  id: string;
  name: string;
  label: string;
  type: InputType;
  placeholder: string;
  example?: string;
};

export type FormInputProps = InputHTMLAttributes<HTMLInputElement> & {
  id: string;
  label: string;
  example?: string;
  helperText?: string;
  helperColor?: string;
  inputBorderColor?: string;
};

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
