import { Routes, Route, Navigate, useLocation } from "react-router-dom";
import AdminLayout from "layouts/admin";
import AuthLayout from "layouts/auth";
import { useAuth0 } from "@auth0/auth0-react";
import { LoadingState } from "components/loading/LoadingState";
import { useEffect } from "react";
import DemoDashboard from "views/demo/DemoDashboard";
import { authConfigured } from "auth/Provider";

function PrivateWorkspace() {
  const { isAuthenticated, isLoading, error } = useAuth0();
  const location = useLocation();
  if (authConfigured && isLoading) return <LoadingState />;
  if (!authConfigured || error || !isAuthenticated) {
    return <Navigate to="/auth/sign-in" replace state={{ returnTo: location.pathname + location.search + location.hash }} />;
  }
  return <AdminLayout />;
}

const App = () => {
  const { isAuthenticated, isLoading } = useAuth0();
  useEffect(() => { document.body.classList.add("dark"); }, []);
  return (
    <Routes>
      <Route path="auth/*" element={<AuthLayout />} />
      <Route path="admin/*" element={<PrivateWorkspace />} />
      <Route path="demo" element={<DemoDashboard />} />
      <Route path="/" element={authConfigured && isLoading ? <LoadingState /> : <Navigate to={isAuthenticated ? "/admin/default" : "/auth/sign-in"} replace />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
};
export default App;
