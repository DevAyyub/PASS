import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, setToken } from "../api.js";

export default function Login({ onLoggedIn }) {
  const [email, setEmail] = useState("advisor@pass.local");
  const [password, setPassword] = useState("advisor123");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const { access_token } = await api("/login", { method:"POST", body:{ email, password }, token:null });
      setToken(access_token);
      const me = await api("/me");
      onLoggedIn(me);
      navigate(me.role === "advisor" ? "/advisor" : "/student");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div style={{maxWidth:420, margin:"40px auto", padding:16, border:"1px solid #333", borderRadius:12}}>
      <h2 style={{marginTop:0}}>Login</h2>
      <p style={{opacity:0.85, marginTop:0}}>Demo accounts are seeded in the backend.</p>

      <form onSubmit={submit} style={{display:"flex", flexDirection:"column", gap:10}}>
        <label>
          <div style={{fontSize:12, opacity:0.8}}>Email</div>
          <input value={email} onChange={(e)=>setEmail(e.target.value)} style={{width:"100%"}} />
        </label>
        <label>
          <div style={{fontSize:12, opacity:0.8}}>Password</div>
          <input type="password" value={password} onChange={(e)=>setPassword(e.target.value)} style={{width:"100%"}} />
        </label>
        <button disabled={busy} type="submit">{busy ? "Signing in..." : "Sign in"}</button>
      </form>

      {error ? <div style={{marginTop:12, color:"#ff8a8a"}}>{error}</div> : null}

      <div style={{marginTop:16, fontSize:12, opacity:0.85}}>
        <div><b>Advisor</b>: advisor@pass.local / advisor123</div>
        <div><b>Student</b>: student1@pass.local / student123</div>
      </div>
    </div>
  );
}
