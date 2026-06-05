import {
  createContext,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { loginUser } from "../pages/Login/login.services";
import type {
  AuthContextValue,
  AuthUser,
  LoginPayload,
  LoginResponse,
  ViewerRole,
} from "../types/auth";

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

const mapBackendRoleToViewerRole = (
  role: LoginResponse["role"] | undefined,
): ViewerRole => {
  if (role === "Customer") return "customer";
  if (role === "Waiter") return "waiter";
  if (role === "Admin") return "admin";
  return "guest";
};

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [refreshToken, setRefreshToken] = useState<string | null>(null);

  const signIn = async (payload: LoginPayload) => {
    const result = await loginUser(payload);

    setUser({
      username: result.username,
      role: result.role,
    });
    setAccessToken(result.access_token);
    setRefreshToken(result.refresh_token);
  };

  const signOut = () => {
    setUser(null);
    setAccessToken(null);
    setRefreshToken(null);
  };

  const value = useMemo(
    () => ({
      user,
      accessToken,
      refreshToken,
      isAuthenticated: Boolean(accessToken),
      viewerRole: mapBackendRoleToViewerRole(user?.role),
      signIn,
      signOut,
    }),
    [user, accessToken, refreshToken],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

// eslint-disable-next-line react-refresh/only-export-components
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
};
