import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import { ArrowRight, GraduationCap, Mail, Phone, UserRound } from "lucide-react";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { PasswordField } from "../../components/PasswordField";
import { Notice } from "../../components/SiteLayout";
import { useAuth } from "../../lib/auth";

export function LoginPage() {
  const { user, isLoading, restoreError, signIn, signInWithGoogle } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [googleBusy, setGoogleBusy] = useState(false);

  useEffect(() => {
    if (!isLoading && user) {
      const fallback = user.role === "delivery_person" ? "/delivery/jobs" : "/account";
      navigate((location.state as { from?: string } | null)?.from ?? fallback, { replace: true });
    }
  }, [isLoading, location.state, navigate, user]);

  async function continueWithGoogle() {
    setError("");
    setGoogleBusy(true);
    try {
      await signInWithGoogle();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not start Google sign-in.");
      setGoogleBusy(false);
    }
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      await signIn(email, password);
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
        {!error && restoreError && <Notice tone="error">{restoreError}</Notice>}
        {(error.toLowerCase().includes("verify your email") || error.toLowerCase().includes("email not confirmed")) && <p className="auth-action-link"><Link to={`/verify-email?email=${encodeURIComponent(email)}`}>Resend verification email</Link></p>}
        <button type="button" className="button button-outline button-full" disabled={busy || googleBusy} onClick={() => void continueWithGoogle()}>
          {googleBusy ? "Connecting to Google..." : "Continue with Google"}
        </button>
        <p className="auth-switch">or sign in with email</p>
        <form onSubmit={submit} className="form-stack">
          <label>Email address<span className="input-wrap"><Mail size={17} /><input type="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@college.edu" /></span></label>
          <label htmlFor="login-password">Password<PasswordField id="login-password" autoComplete="current-password" value={password} onChange={setPassword} placeholder="Your password" /><small className="field-hint">Use the eye button to show or hide your password.</small></label>
          <div className="auth-action-link"><Link to="/forgot-password">Forgot your password?</Link></div>
          <button className="button button-dark button-full" disabled={busy}>{busy ? "Signing you in..." : "Sign in"} <ArrowRight size={16} /></button>
        </form>
        <p className="auth-switch">New to CampusKart? <Link to="/register">Create an account</Link></p>
      </section>
    </div>
  );
}

export function ForgotPasswordPage() {
  const { requestPasswordReset } = useAuth();
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [sent, setSent] = useState(false);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      await requestPasswordReset(email);
      setSent(true);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not request a password reset.");
    } finally {
      setBusy(false);
    }
  }

  return <AuthActionLayout eyebrow="ACCOUNT RECOVERY" title="Reset your password" description="Enter the email address linked to your account. If it exists, we'll send you a secure reset link.">
    {error && <Notice tone="error">{error}</Notice>}
    {sent ? <Notice tone="success">If an account exists for that email, password reset instructions will be sent.</Notice> : (
      <form onSubmit={(event) => void submit(event)} className="form-stack">
        <label>Email address<span className="input-wrap"><Mail size={17} /><input type="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@college.edu" /></span></label>
        <button className="button button-dark button-full" disabled={busy}>{busy ? "Sending..." : "Send reset link"} <ArrowRight size={16} /></button>
      </form>
    )}
    <p className="auth-switch"><Link to="/login">Back to sign in</Link></p>
  </AuthActionLayout>;
}

export function ResetPasswordPage() {
  const { token, isLoading, updatePassword } = useAuth();
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    if (password !== confirmation) {
      setError("Passwords do not match.");
      return;
    }
    setBusy(true);
    try {
      if (!token) {
        setError("This reset link is invalid or expired. Request a new password reset link.");
        return;
      }
      await updatePassword(password);
      setSuccess(true);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not reset your password.");
    } finally {
      setBusy(false);
    }
  }

  return <AuthActionLayout eyebrow="SECURE YOUR ACCOUNT" title="Choose a new password" description="Use at least 8 characters, including a letter, a number, and a special character.">
    {error && <Notice tone="error">{error}</Notice>}
    {!isLoading && !token && !error && <Notice tone="error">This reset link is invalid or expired. Request a new link to continue.</Notice>}
    {success ? <><Notice tone="success">Your password has been updated. Sign in with your new password.</Notice><Link className="button button-dark button-full" to="/login">Go to sign in</Link></> : (
      <>
      <form onSubmit={(event) => void submit(event)} className="form-stack">
        <label htmlFor="reset-password">New password<PasswordField id="reset-password" autoComplete="new-password" value={password} onChange={setPassword} placeholder="At least 8 characters" minLength={8} maxLength={128} pattern="(?=.*[A-Za-z])(?=.*[0-9])(?=.*[^A-Za-z0-9\s]).+" /></label>
        <label htmlFor="reset-password-confirmation">Confirm new password<PasswordField id="reset-password-confirmation" autoComplete="new-password" value={confirmation} onChange={setConfirmation} placeholder="Enter your new password again" minLength={8} maxLength={128} /></label>
        <button className="button button-dark button-full" disabled={busy || isLoading || !token}>{busy ? "Updating password..." : "Update password"} <ArrowRight size={16} /></button>
      </form>
      {error && <p className="auth-switch"><Link to="/forgot-password">Request a new reset link</Link></p>}
      </>
    )}
  </AuthActionLayout>;
}

export function VerifyEmailPage() {
  const [searchParams] = useSearchParams();
  const initialEmail = searchParams.get("email") ?? "";
  const { resendVerification } = useAuth();
  const [email, setEmail] = useState(initialEmail);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  async function resend(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setMessage("");
    setBusy(true);
    try {
      await resendVerification(email);
      setMessage("If an account needs verification, Supabase will send a new confirmation link.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not request a verification email.");
    } finally {
      setBusy(false);
    }
  }

  return <AuthActionLayout eyebrow="EMAIL VERIFICATION" title="Check your inbox" description="Open the confirmation link Supabase sent to your email. Use the form below if you need another link.">
    {error && <Notice tone="error">{error}</Notice>}
    {message && <Notice tone="success">{message}</Notice>}
    <form onSubmit={(event) => void resend(event)} className="form-stack">
      <label>Email address<span className="input-wrap"><Mail size={17} /><input type="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@college.edu" /></span></label>
      <button className="button button-dark button-full" disabled={busy}>{busy ? "Sending..." : "Resend verification link"} <ArrowRight size={16} /></button>
    </form>
    <p className="auth-switch"><Link to="/login">Back to sign in</Link></p>
  </AuthActionLayout>;
}

function AuthActionLayout({
  eyebrow,
  title,
  description,
  children,
}: {
  eyebrow: string;
  title: string;
  description: string;
  children: ReactNode;
}) {
  return <div className="auth-page auth-action-page"><section className="auth-panel auth-action-panel">
    <span className="eyebrow">{eyebrow}</span><h1>{title}</h1><p className="auth-subtitle">{description}</p>
    {children}
  </section></div>;
}

export function RegisterPage() {
  const { signUp } = useAuth();
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
      const needsConfirmation = await signUp(form);
      if (!needsConfirmation) {
        navigate("/account", { replace: true });
        return;
      }
      setCreated(true);
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
        {created && <Notice tone="success">Account created. Check your inbox for a verification link before signing in. <Link to={`/verify-email?email=${encodeURIComponent(form.email)}`}>Resend verification email</Link></Notice>}
        {error && <Notice tone="error">{error}</Notice>}
        {!created && <form onSubmit={submit} className="form-stack">
          <label>Full name<span className="input-wrap"><UserRound size={17} /><input autoComplete="name" required maxLength={120} value={form.full_name} onChange={(event) => change("full_name", event.target.value)} placeholder="Your name" /></span></label>
          <label>Email address<span className="input-wrap"><Mail size={17} /><input type="email" autoComplete="email" required value={form.email} onChange={(event) => change("email", event.target.value)} placeholder="you@college.edu" /></span></label>
          <label htmlFor="register-phone">Phone number<span className="input-wrap"><Phone size={17} /><input id="register-phone" type="tel" inputMode="numeric" autoComplete="tel-national" required minLength={10} maxLength={10} pattern="[0-9]{10}" value={form.phone_number} onChange={(event) => change("phone_number", event.target.value.replace(/\D/g, "").slice(0, 10))} placeholder="9876543210" /></span><small className="field-hint">Enter exactly 10 digits.</small></label>
          <label htmlFor="register-password">Password<PasswordField id="register-password" autoComplete="new-password" value={form.password} onChange={(value) => change("password", value)} placeholder="At least 8 characters" minLength={8} maxLength={128} pattern="(?=.*[A-Za-z])(?=.*[0-9])(?=.*[^A-Za-z0-9\s]).+" /><small className="field-hint">Use the eye button to show or hide your password. Choose 8–128 characters, including a letter, a number, and a special character.</small></label>
          <button className="button button-dark button-full" disabled={busy || created}>{busy ? "Creating account..." : "Create account"} <ArrowRight size={16} /></button>
        </form>}
        <p className="auth-switch">{created ? <>Verified already? <Link to="/login">Sign in</Link></> : <>Already have an account? <Link to="/login">Sign in</Link></>}</p>
      </section>
    </div>
  );
}
