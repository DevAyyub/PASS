import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";

export default function StudentDashboard() {
  const [data, setData] = useState(null);

  useEffect(() => {
    (async () => {
      const d = await api("/student/progress");
      setData(d);
    })();
  }, []);

  if (!data) return <div>Loading...</div>;

  const p = data.progress;
  return (
    <div style={{maxWidth:720}}>
      <h2 style={{marginTop:0}}>My Progress</h2>
      <div style={{opacity:0.85, marginBottom:12}}>
        Keep going — small steps add up. Your next focus plan is ready after your midterm.
      </div>

      <Card title="This week snapshot">
        <Row label="Assignments completed" value={`${p.assignments_completed_pct}%`} />
        <Row label="Attendance" value={`${p.attendance_pct}%`} />
        <Row label="LMS logins (7d)" value={`${p.lms_logins_last_7d}`} />
      </Card>

      <div style={{marginTop:12}}>
        <Link to="/student/study-plan?exam_id=1">
          <button>Open my Study Plan (Midterm)</button>
        </Link>
      </div>

      <div style={{marginTop:16, opacity:0.7, fontSize:12}}>
        Note: PASS never shows “risk score” on the student side — it focuses on actions and support.
      </div>
    </div>
  );
}

function Card({ title, children }) {
  return (
    <div style={{border:"1px solid #333", borderRadius:12, padding:12}}>
      <b>{title}</b>
      <div style={{marginTop:8}}>{children}</div>
    </div>
  );
}

function Row({ label, value }) {
  return (
    <div style={{display:"flex", justifyContent:"space-between", padding:"6px 0", borderTop:"1px solid #2a2a2a"}}>
      <div style={{opacity:0.85}}>{label}</div>
      <div><b>{value}</b></div>
    </div>
  );
}
