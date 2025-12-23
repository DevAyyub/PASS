import React, { useEffect, useState } from "react";
import { Routes, Route, Navigate, Link, useNavigate } from "react-router-dom";
import Login from "./pages/Login.jsx";
import AdvisorDashboard from "./pages/AdvisorDashboard.jsx";
import StudentDashboard from "./pages/StudentDashboard.jsx";
import StudyPlan from "./pages/StudyPlan.jsx";
import { api, getToken, clearToken } from "./api.js";

function TopBar({ me, onLogout }) {
  return (
    <div style={{display:"flex", justifyContent:"space-between", padding:"12px 16px", borderBottom:"1px solid #333"}}>
      <div><Link to="/" style={{color:"#fff", textDecoration:"none"}}>PASS</Link></div>
      <div style={{display:"flex", gap:12, alignItems:"center"}}>
        {me?.name ? <span style={{opacity:0.9}}>{me.name} ({me.role})</span> : null}
        {me ? <button onClick={onLogout}>Logout</button> : null}
      </div>
    </div>
  );
}

export default function App() {
  const [me, setMe] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    (async () => {
      const token = getToken();
      if (!token) { setLoading(false); return; }
      try {
        const data = await api("/me");
        setMe(data);
      } catch {
        clearToken();
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const onLogout = () => {
    clearToken();
    setMe(null);
    navigate("/login");
  };

  if (loading) return <div style={{padding:16}}>Loading...</div>;

  return (
    <div style={{fontFamily:"system-ui, sans-serif", color:"#fff", background:"#111", minHeight:"100vh"}}>
      <TopBar me={me} onLogout={onLogout} />
      <div style={{padding:16}}>
        <Routes>
          <Route path="/login" element={<Login onLoggedIn={setMe} />} />
          <Route path="/" element={<HomeRedirect me={me} />} />
          <Route path="/advisor" element={<Protected me={me} role="advisor"><AdvisorDashboard /></Protected>} />
          <Route path="/student" element={<Protected me={me} role="student"><StudentDashboard /></Protected>} />
          <Route path="/student/study-plan" element={<Protected me={me} role="student"><StudyPlan /></Protected>} />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </div>
    </div>
  );
}

function Protected({ me, role, children }) {
  if (!me) return <Navigate to="/login" />;
  if (role && me.role !== role) return <Navigate to="/" />;
  return children;
}

function HomeRedirect({ me }) {
  if (!me) return <Navigate to="/login" />;
  return me.role === "advisor" ? <Navigate to="/advisor" /> : <Navigate to="/student" />;
}
