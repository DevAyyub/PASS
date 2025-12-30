import React from "react";
import { Link, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext.jsx";

function TopBar() {
  const { me, logout } = useAuth();
  const navigate = useNavigate();

  const onLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div style={{ display: "flex", justifyContent: "space-between", padding: "12px 16px", borderBottom: "1px solid #333" }}>
      <div>
        <Link to="/" style={{ color: "#fff", textDecoration: "none" }}>PASS</Link>
      </div>
      <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
        {me?.name ? <span style={{ opacity: 0.9 }}>{me.name} ({me.role})</span> : null}
        {me ? <button onClick={onLogout}>Logout</button> : null}
      </div>
    </div>
  );
}

export default function AppLayout() {
  const location = useLocation();
  const hideTopBar = location.pathname === "/login";

  return (
    <div style={{ fontFamily: "system-ui, sans-serif", color: "#fff", background: "#111", minHeight: "100vh" }}>
      {!hideTopBar && <TopBar />}
      <div style={{ padding: 16 }}>
        <Outlet />
      </div>
    </div>
  );
}
