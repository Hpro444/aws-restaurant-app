import { Navigate, Route, Routes } from "react-router-dom";
import LoginPage from "./pages/Login";
import SignupPage from "./pages/Signup";
import HomePage from "./pages/Home";
import RestaurantPage from "./pages/Restaurant";
import AvailableTablesPage from "./pages/AvailableTables";
import { useAuth } from "./context/AuthContext";
import ReservationsPage from "./pages/Reservations";

const RequireAuth = ({ children }: { children: React.ReactNode }) => {
  const { isAuthenticated } = useAuth();
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return children;
};

const RequireGuest = ({ children }: { children: React.ReactNode }) => {
  const { isAuthenticated } = useAuth();
  if (isAuthenticated) return <Navigate to="/" replace />;
  return children;
};

function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route
        path="/login"
        element={
          <RequireGuest>
            <LoginPage />
          </RequireGuest>
        }
      />
      <Route
        path="/signup"
        element={
          <RequireGuest>
            <SignupPage />
          </RequireGuest>
        }
      />
      <Route path="/restaurant" element={<RestaurantPage />} />
      <Route
        path="/book-table"
        element={
          <RequireAuth>
            <AvailableTablesPage />
          </RequireAuth>
        }
      />
      <Route
        path="/reservations"
        element={
          // <RequireAuth>
            <ReservationsPage />
          // </RequireAuth>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;
