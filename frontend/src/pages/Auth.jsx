import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { registerAccount, saveSession, signIn } from "../services/api";
import "./Auth.css";

function Auth() {
  const navigate = useNavigate();
  const [mode, setMode] = useState("signin");
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  function update(event) {
    setForm((current) => ({ ...current, [event.target.name]: event.target.value }));
  }

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      if (mode === "register") {
        await registerAccount(form);
      }
      const result = await signIn({ email: form.email, password: form.password });
      saveSession({ token: result.token, user: result.user });
      navigate(result.user.profileComplete ? "/dashboard" : "/onboarding", { replace: true });
    } catch (requestError) {
      setError(requestError.message || "Unable to sign in. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-panel">
        <Link className="auth-brand" to="/">Career<span>Cloud</span></Link>
        <p className="auth-kicker">YOUR CAREER JOURNEY, IN ONE PLACE</p>
        <h1>{mode === "signin" ? "Welcome back." : "Build your career profile."}</h1>
        <p className="auth-copy">
          Sign in to review your progress, update your skills, and continue with your career services.
        </p>

        <div className="auth-tabs" role="tablist" aria-label="Account access">
          <button type="button" className={mode === "signin" ? "active" : ""} onClick={() => { setMode("signin"); setError(""); }}>Sign in</button>
          <button type="button" className={mode === "register" ? "active" : ""} onClick={() => { setMode("register"); setError(""); }}>Create account</button>
        </div>

        <form className="auth-form" onSubmit={submit}>
          {mode === "register" && (
            <label>Full name<input name="name" autoComplete="name" value={form.name} onChange={update} required /></label>
          )}
          <label>Email address<input name="email" type="email" autoComplete="email" value={form.email} onChange={update} required /></label>
          <label>Password<input name="password" type="password" autoComplete={mode === "signin" ? "current-password" : "new-password"} minLength={10} value={form.password} onChange={update} required /></label>
          {mode === "register" && <p className="auth-hint">Use at least 10 characters.</p>}
          {error && <p className="auth-error" role="alert">{error}</p>}
          <button className="auth-submit" type="submit" disabled={busy}>
            {busy ? "Please wait…" : mode === "signin" ? "Sign in to dashboard" : "Create account"}
          </button>
        </form>
        <p className="auth-footnote">LocalStack development account. Your password is stored as a salted hash in the local database.</p>
      </section>
      <aside className="auth-aside">
        <span className="auth-orbit orbit-one" />
        <span className="auth-orbit orbit-two" />
        <div className="auth-aside-content">
          <span className="auth-aside-label">CAREERWISE AI</span>
          <h2>A clearer path from where you are to where you want to be.</h2>
          <ul><li>Track your career assessments</li><li>Keep your resume screenings together</li><li>Make steady progress on your learning plan</li></ul>
        </div>
      </aside>
    </main>
  );
}

export default Auth;
