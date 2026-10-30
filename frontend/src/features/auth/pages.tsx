import { useState, type FormEvent } from "react";
import { ArrowRight, GraduationCap, Mail, Phone, UserRound } from "lucide-react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { PasswordField } from "../../components/PasswordField";
import { Notice } from "../../components/SiteLayout";
import { useAuth } from "../../lib/auth";
import { api } from "../../lib/api";

export function LoginPage() {
  const { signIn } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      await signIn(email, password);
      navigate((location.state as { from?: string } | null)?.from ?? "/account", { replace: true });
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not sign in.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-art"><span className="auth-asterisk">✳</span><div className="auth-art-copy"><span>YOUR CAMPUS<br />IS FULL OF</span><b>possibility.</b><p>Come find what fits your next chapter.</p></div><div className="auth-art-orbit" /></div>
      <section className="auth-panel">
        <span className="eyebrow">WELCOME BACK</span><h1>Good to see you.</h1><p className="auth-subtitle">Sign in and get back to finding your campus favorites.</p>
        {error && <Notice tone="error">{error}</Notice>}
        <form onSubmit={submit} className="form-stack">
          <label>Email address<span className="input-wrap"><Mail size={17} /><input type="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@college.edu" /></span></label>
          <label htmlFor="login-password">Password<PasswordField id="login-password" autoComplete="current-password" value={password} onChange={setPassword} placeholder="Your password" /><small className="field-hint">Use the eye button to show or hide your password.</small></label>
          <button className="button button-dark button-full" disabled={busy}>{busy ? "Signing you in..." : "Sign in"} <ArrowRight size={16} /></button>
        </form>
        <p className="auth-switch">New to CampusKart? <Link to="/register">Create an account</Link></p>
      </section>
    </div>
  );
}

export function RegisterPage() {
  const navigate = useNavigate();
  const [form, setForm] = useState({ full_name: "", email: "", phone_number: "", password: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [created, setCreated] = useState(false);

  function change(field: keyof typeof form, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      await api.register(form);
      setCreated(true);
      window.setTimeout(() => navigate("/login", { replace: true }), 1400);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not create your account.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-page register-layout">
      <div className="auth-art register-art"><span className="auth-art-cap"><GraduationCap size={46} /></span><div className="auth-art-copy"><span>GOOD THINGS<br />HAPPEN ON</span><b>campus.</b><p>Join your student marketplace.</p></div><div className="auth-art-orbit" /></div>
      <section className="auth-panel">
        <span className="eyebrow">JOIN THE CAMPUS CROWD</span><h1>Your next find<br />starts here.</h1><p className="auth-subtitle">Create an account to make CampusKart yours.</p>
        {created && <Notice tone="success">Account created! Taking you to sign in...</Notice>}
        {error && <Notice tone="error">{error}</Notice>}
        <form onSubmit={submit} className="form-stack">
          <label>Full name<span className="input-wrap"><UserRound size={17} /><input autoComplete="name" required maxLength={120} value={form.full_name} onChange={(event) => change("full_name", event.target.value)} placeholder="Your name" /></span></label>
          <label>Email address<span className="input-wrap"><Mail size={17} /><input type="email" autoComplete="email" required value={form.email} onChange={(event) => change("email", event.target.value)} placeholder="you@college.edu" /></span></label>
          <label htmlFor="register-phone">Phone number<span className="input-wrap"><Phone size={17} /><input id="register-phone" type="tel" inputMode="numeric" autoComplete="tel-national" required minLength={10} maxLength={10} pattern="[0-9]{10}" value={form.phone_number} onChange={(event) => change("phone_number", event.target.value.replace(/\D/g, "").slice(0, 10))} placeholder="9876543210" /></span><small className="field-hint">Enter exactly 10 digits.</small></label>
          <label htmlFor="register-password">Password<PasswordField id="register-password" autoComplete="new-password" value={form.password} onChange={(value) => change("password", value)} placeholder="At least 8 characters" minLength={8} maxLength={128} pattern="(?=.*[A-Za-z])(?=.*[0-9])(?=.*[^A-Za-z0-9\s]).+" /><small className="field-hint">Use the eye button to show or hide your password. Choose 8–128 characters, including a letter, a number, and a special character.</small></label>
          <button className="button button-dark button-full" disabled={busy || created}>{busy ? "Creating account..." : "Create account"} <ArrowRight size={16} /></button>
        </form>
        <p className="auth-switch">Already have an account? <Link to="/login">Sign in</Link></p>
      </section>
    </div>
  );
}
