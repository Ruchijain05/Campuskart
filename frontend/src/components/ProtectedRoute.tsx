import { Navigate, Outlet, useLocation } from "react-router-dom";
import { LoadingState, Notice } from "./SiteLayout";
import { useAuth } from "../lib/auth";
import type { UserRole } from "../lib/types";

export function ProtectedRoute({ roles }: { roles?: UserRole[] }) {
  const { user, isLoading, restoreError, retryRestore } = useAuth();
  const location = useLocation();
  if (isLoading) return <LoadingState label="Restoring your session..." />;
  if (restoreError) {
    return (
      <section className="content-narrow">
        <Notice tone="error">Could not restore your saved session: {restoreError}</Notice>
        <button type="button" className="button button-outline" onClick={() => void retryRestore()}>Try again</button>
      </section>
    );
  }
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  if (roles && !roles.includes(user.role)) return <Navigate to="/" replace />;
  return <Outlet />;
}
