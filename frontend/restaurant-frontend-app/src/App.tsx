import { Navigate, Route, Routes } from "react-router-dom";
import LoginPage from "./pages/Login";
import SignupPage from "./pages/Signup";
import RestaurantPage from "./pages/Restaurant";
import AvailableTablesPage from "./pages/AvailableTables";
import { useAuth } from "./context/AuthContext";
import ReservationsPage from "./pages/Reservations";
import HomePage from "./pages/Home";
import MenuPage from "./pages/Menu";
import DashboardPage from "./pages/Dashboard";
import WaiterReservations from "./pages/WaiterReservations";

const RequireAuth = ({ children }: { children: React.ReactNode }) => {
  const { isAuthenticated } = useAuth();
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return children;
};

const RequireAdmin = ({ children }: { children: React.ReactNode }) => {
  const { isAuthenticated, user } = useAuth();
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  else if (user?.role !== "Admin") return <Navigate to="/" replace />;
  return children;
};

const RequireGuest = ({ children }: { children: React.ReactNode }) => {
  const { isAuthenticated } = useAuth();
  if (isAuthenticated) return <Navigate to="/" replace />;
  return children;
};

function App() {
  return (
    <>
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
        <Route path="/restaurant/:id" element={<RestaurantPage />} />
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
            <RequireAuth>
              <ReservationsPage />
            </RequireAuth>
          }
        />
        <Route
          path="/dashboard"
          element={
            <RequireAdmin>
              <DashboardPage />
            </RequireAdmin>
          }
        />
        <Route path="/menu" element={<MenuPage />} />
        <Route
          path="/waiter-reservations"
          element={
            <RequireAuth>
              <WaiterReservations />
            </RequireAuth>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </>
  );
}

export default App;
