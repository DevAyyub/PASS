import React from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import Login from "./pages/Login.jsx";
import AdvisorDashboard from "./pages/AdvisorDashboard.jsx";
import StudentDashboard from "./pages/StudentDashboard.jsx";
import StudyPlan from "./pages/StudyPlan.jsx";

import AppLayout from "./layout/AppLayout.jsx";
import { RequireAuth, RequireRole } from "./routes/guards.jsx";
import { useAuth } from "./auth/AuthContext.jsx";

function HomeRedirect() {
  const { me } = useAuth();
  if (!me) return <Navigate to="/login" replace />;
  return me.role === "advisor" ? <Navigate to="/advisor" replace /> : <Navigate to="/student" replace />;
}

export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route path="/login" element={<Login />} />

        <Route
          path="/"
          element={
            <RequireAuth>
              <HomeRedirect />
            </RequireAuth>
          }
        />

        <Route
          path="/advisor"
          element={
            <RequireRole role="advisor">
              <AdvisorDashboard />
            </RequireRole>
          }
        />

        <Route
          path="/student"
          element={
            <RequireRole role="student">
              <StudentDashboard />
            </RequireRole>
          }
        />

        <Route
          path="/student/study-plan"
          element={
            <RequireRole role="student">
              <StudyPlan />
            </RequireRole>
          }
        />

        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
