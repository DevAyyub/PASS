import React, { useEffect, useState } from "react";
import { api } from "../api.js";

export default function AdvisorDashboard() {
  const [students, setStudents] = useState([]);
  const [selected, setSelected] = useState(null);
  const [note, setNote] = useState("");
  const [msg, setMsg] = useState("");

  const load = async () => {
    const data = await api("/advisor/students");
    setStudents(data.students);
  };

  const openStudent = async (student_id) => {
    const data = await api(`/advisor/students/${student_id}`);
    setSelected(data);
    setMsg("");
  };

  const predict = async () => {
    setMsg("Running predictions...");
    await api("/advisor/predict-risk", { method:"POST" });
    setMsg("Done. Refreshing list...");
    await load();
    setMsg("Updated.");
  };

  const addIntervention = async () => {
    if (!selected) return;
    await api(`/advisor/students/${selected.student.student_id}/interventions`, { method:"POST", body:{ note } });
    setNote("");
    await openStudent(selected.student.student_id);
  };

  useEffect(() => { load(); }, []);

  return (
    <div style={{display:"grid", gridTemplateColumns:"1fr 1.2fr", gap:16}}>
      <div style={{border:"1px solid #333", borderRadius:12, padding:12}}>
        <div style={{display:"flex", justifyContent:"space-between", alignItems:"center"}}>
          <h3 style={{margin:"4px 0"}}>At-Risk Students</h3>
          <button onClick={predict}>Run Risk Scoring</button>
        </div>
        <div style={{opacity:0.8, fontSize:12, marginBottom:8}}>Sorted by latest risk probability (highest first).</div>
        {msg ? <div style={{fontSize:12, opacity:0.85, marginBottom:8}}>{msg}</div> : null}
        <div style={{display:"flex", flexDirection:"column", gap:8}}>
          {students.map(s => (
            <button key={s.student_id} onClick={()=>openStudent(s.student_id)} style={{textAlign:"left"}}>
              <div style={{display:"flex", justifyContent:"space-between"}}>
                <b>{s.name}</b>
                <span>{s.risk_probability === null ? "—" : s.risk_probability.toFixed(2)}</span>
              </div>
              <div style={{fontSize:12, opacity:0.75}}>{s.department || "—"} • {s.risk_generated_at ? new Date(s.risk_generated_at).toLocaleString() : "no score yet"}</div>
            </button>
          ))}
        </div>
      </div>

      <div style={{border:"1px solid #333", borderRadius:12, padding:12}}>
        {!selected ? (
          <div style={{opacity:0.8}}>Select a student to see details and explanations.</div>
        ) : (
          <div>
            <h3 style={{margin:"4px 0"}}>{selected.student.name}</h3>
            <div style={{fontSize:12, opacity:0.8}}>
              Dept: {selected.student.department || "—"} • Cohort: {selected.student.cohort_year || "—"}
            </div>

            <div style={{marginTop:12, padding:12, border:"1px solid #2a2a2a", borderRadius:12}}>
              <b>XAI (Top Factors)</b>
              <div style={{fontSize:12, opacity:0.8, marginBottom:8}}>Simple feature importance (MVP).</div>
              {selected.latest_risk?.top_factors?.length ? (
                <ul>
                  {selected.latest_risk.top_factors.map((f, idx)=>(
                    <li key={idx}>{f.feature}: {f.importance.toFixed(2)}</li>
                  ))}
                </ul>
              ) : (
                <div style={{opacity:0.8}}>No explanation available yet.</div>
              )}
            </div>

            <div style={{marginTop:12, padding:12, border:"1px solid #2a2a2a", borderRadius:12}}>
              <b>Intervention Log</b>
              <div style={{display:"flex", gap:8, marginTop:8}}>
                <input value={note} onChange={(e)=>setNote(e.target.value)} placeholder="Met with student, suggested tutoring..." style={{flex:1}} />
                <button onClick={addIntervention}>Add</button>
              </div>
              <div style={{marginTop:10}}>
                {selected.interventions.length ? selected.interventions.map(i => (
                  <div key={i.id} style={{padding:"8px 0", borderTop:"1px solid #2a2a2a"}}>
                    <div style={{fontSize:12, opacity:0.75}}>{new Date(i.created_at).toLocaleString()}</div>
                    <div>{i.note}</div>
                  </div>
                )) : <div style={{opacity:0.8, marginTop:8}}>No interventions yet.</div>}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
