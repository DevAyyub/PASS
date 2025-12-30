import React from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../auth/AuthContext.jsx";

export function RequireAuth({ children }) {
  const { me, loading } = useAuth();
  const location = useLocation();

  if (loading) return <div style={{ padding: 16 }}>Loading...</div>;
  if (!me) return <Navigate to="/login" state={{ from: location }} replace />;
  return children;
}

export function RequireRole({ role, children }) {
  const { me, loading } = useAuth();
  if (loading) return <div style={{ padding: 16 }}>Loading...</div>;
  if (!me) return <Navigate to="/login" replace />;
  if (role && me.role !== role) return <Navigate to="/" replace />;
  return children;
}
