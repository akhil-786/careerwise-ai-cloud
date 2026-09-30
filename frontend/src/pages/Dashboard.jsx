import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { clearSession, getDashboard, getSessionUser, hasSession, saveSession, updateSessionUser, updateSkills, getResumeUploadUrl } from "../services/api";
import "./Dashboard.css";

function dateLabel(value) {
  if (!value) return "Date not available";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Date not available" : new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(date);
}

function preview(value, max = 160) {
  if (typeof value !== "string") return "Your saved result is ready to view.";
  return value.length > max ? `${value.slice(0, max).trim()}…` : value;
}

function Dashboard() {
  const navigate = useNavigate();
  const sessionUser = useMemo(() => getSessionUser(), []);
  const userId = sessionUser?.userId;
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [skillText, setSkillText] = useState("");
  const [savingSkills, setSavingSkills] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [notice, setNotice] = useState("");

  const refresh = useCallback(async () => {
    if (!userId) {
      navigate("/login", { replace: true });
      return;
    }
    try {
      const result = await getDashboard(userId);
      setError("");
      setData(result);
      setSkillText((result.user?.skills || []).join(", "));
      if (result.user) {
        const updatedUser = { ...sessionUser, ...result.user };
        saveSession({ token: sessionStorage.getItem("careercloud_token"), user: updatedUser });
      }
    } catch (requestError) {
      if (!hasSession()) navigate("/login", { replace: true });
      else setError(requestError.message || "Could not load your dashboard.");
    } finally {
      setLoading(false);
    }
  }, [navigate, sessionUser, userId]);

  useEffect(() => {
    const timer = window.setTimeout(() => { void refresh(); }, 0);
    return () => window.clearTimeout(timer);
  }, [refresh]);

  async function saveSkills(event) {
    event.preventDefault();
    setSavingSkills(true);
    setNotice("");
    try {
      const skills = skillText.split(",").map((item) => item.trim()).filter(Boolean);
      const result = await updateSkills(userId, skills);
      const nextData = { ...data, user: result.user };
      setData(nextData);
      updateSessionUser({ ...sessionUser, ...result.user });
      setSkillText((result.user.skills || []).join(", "));
      setNotice("Your skills are up to date.");
    } catch (requestError) {
      setNotice(requestError.message || "Could not save your skills.");
    } finally {
      setSavingSkills(false);
    }
  }

  async function uploadResume(event) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    if (!/\.(pdf|docx)$/i.test(file.name)) {
      setNotice("Choose a PDF or DOCX resume.");
      return;
    }
    setUploading(true);
    setNotice("");
    try {
      const result = await getResumeUploadUrl(file.name);
      const uploaded = await fetch(result.uploadUrl, {
        method: "PUT",
        headers: { "Content-Type": "application/octet-stream" },
        body: file,
      });
      if (!uploaded.ok) throw new Error("The resume upload to LocalStack failed.");
      setNotice("Resume uploaded. Screening will appear here when processing finishes.");
      await refresh();
    } catch (requestError) {
      setNotice(requestError.message || "Could not upload your resume.");
    } finally {
      setUploading(false);
    }
  }

  function signOut() {
    clearSession();
    navigate("/login", { replace: true });
  }

  if (loading) return <main className="dashboard-shell"><div className="dashboard-loading">Loading your career workspace…</div></main>;

  const user = data?.user || sessionUser || {};
  const assessments = data?.assessments || [];
  const recommendations = data?.recommendations || [];
  const roadmaps = data?.roadmaps || [];
  const screenings = data?.screenings || [];

  return (
    <main className="dashboard-shell">
      <header className="dashboard-topbar">
        <a className="dashboard-brand" href="/dashboard">Career<span>Cloud</span></a>
        <div className="dashboard-account"><span>{user.name || user.email}</span><button onClick={signOut}>Sign out</button></div>
      </header>

      <section className="dashboard-welcome">
        <div><p className="dashboard-eyebrow">CAREER WORKSPACE</p><h1>Good to see you, {user.name?.split(" ")[0] || "there"}.</h1><p>Keep your career history, skills, and next steps moving forward.</p></div>
        <button className="dashboard-primary" onClick={() => navigate("/assessment")}>Start a new assessment <span>→</span></button>
      </section>

      {error && <div className="dashboard-alert" role="alert"><span>{error}</span><button onClick={refresh}>Try again</button></div>}
      {notice && <div className="dashboard-notice" role="status">{notice}</div>}

      <section className="dashboard-stats" aria-label="Career activity summary">
        <article><span className="stat-icon indigo">◎</span><div><strong>{assessments.length}</strong><span>Assessments</span></div></article>
        <article><span className="stat-icon violet">✦</span><div><strong>{recommendations.length}</strong><span>Recommendations</span></div></article>
        <article><span className="stat-icon teal">▤</span><div><strong>{screenings.length}</strong><span>Resume screenings</span></div></article>
        <article><span className="stat-icon amber">↗</span><div><strong>{roadmaps.length}</strong><span>Learning roadmaps</span></div></article>
      </section>

      <section className="dashboard-main-grid">
        <article className="dashboard-card profile-card">
          <div className="section-heading"><div><p className="dashboard-eyebrow">YOUR PROFILE</p><h2>Skills and strengths</h2></div><span className="profile-avatar">{(user.name || "C").slice(0, 1).toUpperCase()}</span></div>
          <p className="card-description">Keep your skills current. They help personalize assessments and career guidance.</p>
          <form onSubmit={saveSkills} className="skills-form"><label htmlFor="skills-list">Your skills</label><textarea id="skills-list" value={skillText} onChange={(event) => setSkillText(event.target.value)} placeholder="Python, AWS, communication" rows="3"/><small>Separate skills with commas. Your saved list is editable any time.</small><button className="dashboard-secondary" disabled={savingSkills}>{savingSkills ? "Saving…" : "Save skills"}</button></form>
          <div className="profile-details"><span>{user.education || "Education not added"}</span><span>{user.interests?.length ? user.interests.join(" · ") : "Add interests during onboarding"}</span></div>
        </article>

        <article className="dashboard-card resume-card">
          <div className="section-heading"><div><p className="dashboard-eyebrow">RESUME SCREENING</p><h2>Resume library</h2></div><span className="resume-symbol">↑</span></div>
          <p className="card-description">Upload a new version whenever your experience changes. Earlier screenings stay in your history.</p>
          <label className={`resume-upload ${uploading ? "is-uploading" : ""}`}>
            <input type="file" accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document" onChange={uploadResume} disabled={uploading}/>
            <strong>{uploading ? "Uploading resume…" : "Choose a resume to upload"}</strong><span>PDF or DOCX · upload goes to your local S3 bucket</span>
          </label>
          <div className="history-list compact-history">
            {screenings.slice(0, 3).map((item) => <div className="history-row resume-history-row" key={item.screeningId}><div><strong>{item.fileName || "Resume"}</strong><span>{dateLabel(item.createdAt)} · {item.status || "pending"}</span>{item.skills?.length > 0 && <span className="resume-skills">Skills: {item.skills.join(", ")}</span>}{item.careerMatches?.[0] && <span className="resume-match">Top match: {item.careerMatches[0].career} · {item.careerMatches[0].matchPercentage}%</span>}</div><span className={`status-pill ${item.status === "completed" ? "complete" : "pending"}`}>{item.status || "pending"}</span></div>)}
            {!screenings.length && <p className="empty-state">No resume screenings yet.</p>}
          </div>
        </article>
      </section>

      <section className="dashboard-card history-card">
        <div className="section-heading"><div><p className="dashboard-eyebrow">YOUR ACTIVITY</p><h2>Previous services</h2></div><button className="text-button" onClick={refresh}>Refresh history</button></div>
        <div className="service-history-grid">
          <History title="Assessments" items={assessments} idKey="assessmentId" detail={(item) => `${Object.keys(item.answers || {}).length} responses · ${item.status || "saved"}`} empty="Your completed assessments will show here." />
          <History title="Career recommendations" items={recommendations} idKey="recommendationId" detail={(item) => preview(item.recommendation)} empty="Recommendations generated from your assessments will show here." />
          <History title="Learning roadmaps" items={roadmaps} idKey="roadmapId" detail={(item) => preview(item.roadmap)} empty="Your saved learning plans will show here." />
        </div>
      </section>

      <footer className="dashboard-footer">CareerCloud keeps your career services and progress together.</footer>
    </main>
  );
}

function History({ title, items, idKey, detail, empty }) {
  return <section className="history-column"><h3>{title}<span>{items.length}</span></h3>{items.slice(0, 4).map((item) => <article key={item[idKey]} className="history-item"><span className="history-date">{dateLabel(item.createdAt)}</span><p>{detail(item)}</p></article>)}{!items.length && <p className="empty-state">{empty}</p>}</section>;
}

export default Dashboard;
