import React, { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { api } from "../api.js";

function useQuery() {
  const { search } = useLocation();
  return new URLSearchParams(search);
}

export default function StudyPlan() {
  const q = useQuery();
  const exam_id = q.get("exam_id") || "1";
  const [plan, setPlan] = useState(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const data = await api(`/student/study-plan?exam_id=${exam_id}`);
        setPlan(data);
      } catch (e) {
        setErr(e.message);
      }
    })();
  }, [exam_id]);

  if (err) return <div style={{color:"#ff8a8a"}}>{err}</div>;
  if (!plan) return <div>Loading...</div>;

  return (
    <div style={{maxWidth:800}}>
      <h2 style={{marginTop:0}}>AI Diagnostic Study Planner</h2>
      <div style={{opacity:0.85, marginBottom:12}}>
        Here’s your topic breakdown from Exam #{plan.exam_id}. Let’s focus on the areas that will give you the biggest improvement.
      </div>

      <Section title="🚀 Strengths">
        {plan.summary.strengths.length ? plan.summary.strengths.map((t, idx)=>(
          <Topic key={idx} t={t} />
        )) : <div style={{opacity:0.8}}>No strengths detected yet — we’ll build them.</div>}
      </Section>

      <Section title="💡 Areas for Focus">
        {plan.summary.areas_for_focus.length ? plan.summary.areas_for_focus.map((t, idx)=>(
          <div key={idx} style={{borderTop:"1px solid #2a2a2a", padding:"8px 0"}}>
            <Topic t={t} />
            <div style={{marginTop:6, opacity:0.85}}><b>Recommended resources</b></div>
            <ul>
              {t.resources?.length ? t.resources.map((r, i)=>(
                <li key={i}><a href={r.url} target="_blank" rel="noreferrer" style={{color:"#9ad"}}>{r.title}</a> <span style={{opacity:0.7}}>({r.type||"resource"})</span></li>
              )) : <li>No resources mapped yet for this topic.</li>}
            </ul>
          </div>
        )) : <div style={{opacity:0.8}}>Great news — no critical weak areas detected.</div>}
      </Section>

      <Section title="All Topics">
        <table style={{width:"100%", borderCollapse:"collapse"}}>
          <thead>
            <tr>
              <th style={{textAlign:"left", padding:"6px 0"}}>Topic</th>
              <th style={{textAlign:"right", padding:"6px 0"}}>Score</th>
            </tr>
          </thead>
          <tbody>
            {plan.all_topics.map((t, idx)=>(
              <tr key={idx} style={{borderTop:"1px solid #2a2a2a"}}>
                <td style={{padding:"6px 0"}}>{t.topic}</td>
                <td style={{padding:"6px 0", textAlign:"right"}}><b>{t.score_pct}%</b> <span style={{opacity:0.7}}>({t.correct}/{t.total})</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </Section>
    </div>
  );
}

function Section({ title, children }) {
  return (
    <div style={{border:"1px solid #333", borderRadius:12, padding:12, marginBottom:12}}>
      <h3 style={{margin:"4px 0"}}>{title}</h3>
      <div>{children}</div>
    </div>
  );
}

function Topic({ t }) {
  return (
    <div style={{display:"flex", justifyContent:"space-between", gap:12}}>
      <div><b>{t.topic}</b></div>
      <div><b>{t.score_pct}%</b> <span style={{opacity:0.7}}>({t.correct}/{t.total})</span></div>
    </div>
  );
}
