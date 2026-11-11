import { useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { ArrowRight, Bell, ClipboardList, GraduationCap, Headphones, Heart, Home, LogOut, MessageCircle, Package, RotateCcw, Search, ShoppingBag, ShoppingCart, UserRound } from "lucide-react";
import { useAuth } from "../lib/auth";
import type { UserRole } from "../lib/types";
import { useCart } from "../lib/cart";
import { CompareTray } from "../features/compare/CompareTray";
import { useNotifications } from "../lib/notifications";
import { api } from "../lib/api";

export function SiteLayout() {
  const { user, token, signOut, switchRole } = useAuth();
  const { itemCount } = useCart();
  const { unreadCount } = useNotifications();
  const [search, setSearch] = useState("");
  const [unreadMessages, setUnreadMessages] = useState(0);
  const [signOutOpen, setSignOutOpen] = useState(false);
  const [signingOut, setSigningOut] = useState(false);
  const [switchingRole, setSwitchingRole] = useState(false);
  const signOutDialogRef = useRef<HTMLDialogElement>(null);
  const navigate = useNavigate();

  useEffect(() => {
    const dialog = signOutDialogRef.current;
    if (!dialog) return;
    if (signOutOpen && !dialog.open) dialog.showModal();
    else if (!signOutOpen && dialog.open) dialog.close();
  }, [signOutOpen]);

  useEffect(() => {
    if (!token || (user?.role !== "buyer" && user?.role !== "seller")) { setUnreadMessages(0); return; }
    let active = true;
    const refresh = () => api.getUnreadChatCount(token).then((result) => { if (active) setUnreadMessages(result.unread_count); }).catch(() => undefined);
    void refresh();
    const timer = window.setInterval(() => void refresh(), 30000);
    window.addEventListener("campuskart-messages-updated", refresh);
    return () => { active = false; window.clearInterval(timer); window.removeEventListener("campuskart-messages-updated", refresh); };
  }, [token, user?.id, user?.role]);

  function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    navigate(`/?q=${encodeURIComponent(search.trim())}`);
  }

  async function handleSignOut() {
    setSigningOut(true);
    try {
      await signOut();
      setSignOutOpen(false);
      navigate("/");
    } catch (error) {
      setSignOutOpen(false);
      navigate("/");
      window.alert(error instanceof Error ? error.message : "Could not sign out.");
    } finally {
      setSigningOut(false);
    }
  }

  async function handleRoleSwitch(role: UserRole) {
    if (!user || role === user.role) return;
    setSwitchingRole(true);
    try {
      await switchRole(role);
      navigate(role === "admin" ? "/admin" : role === "seller" ? "/seller/products" : role === "delivery_person" ? "/delivery/jobs" : "/account");
    } catch (error) {
      window.alert(error instanceof Error ? error.message : "Could not switch roles.");
    } finally {
      setSwitchingRole(false);
    }
  }

  return (
    <div className="site-frame">
      <div className="announcement">
        <span><GraduationCap size={15} /> Made for campus life</span>
        <span className="announcement-note">Find your next campus essential <ArrowRight size={14} /></span>
      </div>
      <header className="site-header">
        <Link className="brand" to="/" aria-label="CampusKart home">
          <span className="brand-mark"><ShoppingBag size={21} strokeWidth={2.5} /></span>
          <span>campus<span className="brand-accent">kart</span><small>STUDENT MARKETPLACE</small></span>
        </Link>
        <form className="search-bar" onSubmit={submitSearch}>
          <Search size={19} />
          <input
            aria-label="Search products"
            placeholder="Search for textbooks, tech, dorm finds..."
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
          <button type="submit">Search</button>
        </form>
        <nav className="header-actions">
          <NavLink to={user ? user.role === "delivery_person" ? "/delivery/jobs" : "/account" : "/login"} className="header-link">
            <UserRound size={19} />
            <span><small>{user ? user.role === "delivery_person" ? "Staff" : "Hello," : "Welcome"}</small>{user?.full_name.split(" ")[0] ?? "Sign in"}</span>
          </NavLink>
          {user?.role !== "delivery_person" && <NavLink to="/cart" className="header-link cart-header-link" aria-label="Cart">
            <ShoppingCart size={19} /><span><small>Your items</small>Cart <b className="cart-count">{itemCount}</b></span>
          </NavLink>}
          {user ? (
            <>
              {user.roles.length > 1 && <label className="header-link role-switcher"><span><small>Active role</small></span><select aria-label="Switch active role" value={user.role} disabled={switchingRole} onChange={(event) => void handleRoleSwitch(event.target.value as UserRole)}>{user.roles.map((role) => <option key={role} value={role}>{role.replace("_", " ")}</option>)}</select></label>}
              <button type="button" className="header-link header-signout" onClick={() => setSignOutOpen(true)}>
                <LogOut size={18} /><span><small>Account</small>Sign out</span>
              </button>
            </>
          ) : (
            <Link to="/register" className="header-link header-register">
              <span><small>New here?</small>Create account</span>
            </Link>
          )}
        </nav>
      </header>
      <dialog
        ref={signOutDialogRef}
        className="logout-confirmation"
        aria-labelledby="logout-confirmation-title"
        aria-describedby="logout-confirmation-description"
        onCancel={(event) => {
          event.preventDefault();
          if (!signingOut) setSignOutOpen(false);
        }}
        onClose={() => setSignOutOpen(false)}
      >
        <div className="logout-confirmation-icon"><LogOut size={21} /></div>
        <h2 id="logout-confirmation-title">Sign out of CampusKart?</h2>
        <p id="logout-confirmation-description">You can sign back in anytime to continue shopping and manage your account.</p>
        <div className="logout-confirmation-actions">
          <button type="button" className="button button-outline" disabled={signingOut} onClick={() => setSignOutOpen(false)}>Cancel</button>
          <button type="button" className="button logout-confirm-button" disabled={signingOut} onClick={() => void handleSignOut()}>
            {signingOut ? "Signing out..." : "Logout"}
          </button>
        </div>
      </dialog>
      <nav className="category-nav" aria-label="Main navigation">
        <NavLink to="/" end>Home</NavLink>
        <NavLink to="/bundles">Bundles</NavLink>
        {user?.role !== "delivery_person" && <NavLink to="/sell">Sell on CampusKart</NavLink>}
        {(user?.role === "seller" || user?.role === "admin") && <NavLink to="/orders">My orders</NavLink>}
        {user?.role === "seller" && <NavLink to="/messages" className="notification-nav-link"><MessageCircle size={14} /> Messages{unreadMessages > 0 && <b className="notification-count">{unreadMessages > 99 ? "99+" : unreadMessages}</b>}</NavLink>}
        {user?.role === "seller" && <NavLink to="/seller/products">Seller studio</NavLink>}
        {user?.role === "seller" && <NavLink to="/seller/orders">Seller orders</NavLink>}
        {user?.role === "delivery_person" && <NavLink to="/delivery/jobs">Delivery jobs</NavLink>}
        {user?.role === "admin" && <NavLink to="/admin">Admin</NavLink>}
        <span className="nav-note">Good finds. Great campus energy.</span>
      </nav>
      {user?.role === "buyer" ? (
        <div className="buyer-layout">
          <aside className="buyer-sidebar" aria-label="Customer navigation">
            <span className="buyer-sidebar-heading">MY CAMPUSKART</span>
            <NavLink to="/" end><Home size={19} strokeWidth={1.9} /><span>Home</span></NavLink>
            <NavLink to="/account"><UserRound size={19} strokeWidth={1.9} /><span>My account</span></NavLink>
            <NavLink to="/orders"><Package size={19} strokeWidth={1.9} /><span>My orders</span></NavLink>
            <NavLink to="/buy-again"><RotateCcw size={19} strokeWidth={1.9} /><span>Buy again</span></NavLink>
            <NavLink to="/wishlist"><Heart size={19} strokeWidth={1.9} /><span>Wishlist</span></NavLink>
            <NavLink to="/my-questions"><MessageCircle size={19} strokeWidth={1.9} /><span>My questions</span></NavLink>
            <NavLink to="/returns"><RotateCcw size={19} strokeWidth={1.9} /><span>Returns &amp; refunds</span></NavLink>
            <NavLink to="/support"><Headphones size={19} strokeWidth={1.9} /><span>Support</span></NavLink>
            <NavLink to="/requests"><ClipboardList size={19} strokeWidth={1.9} /><span>Request anything</span></NavLink>
            <NavLink to="/notifications" className="notification-nav-link"><Bell size={19} strokeWidth={1.9} /><span>Notifications</span>{unreadCount > 0 && <b className="notification-count">{unreadCount > 99 ? "99+" : unreadCount}</b>}</NavLink>
            <NavLink to="/messages" className="notification-nav-link"><MessageCircle size={19} strokeWidth={1.9} /><span>Messages</span>{unreadMessages > 0 && <b className="notification-count">{unreadMessages > 99 ? "99+" : unreadMessages}</b>}</NavLink>
          </aside>
          <main className="main-content"><Outlet /></main>
        </div>
      ) : <main className="main-content"><Outlet /></main>}
      <CompareTray />
      <footer className="site-footer">
        <Link className="footer-brand" to="/">campus<span>kart</span></Link>
        <span>Campus finds, made simple.</span>
        <span>Built for student life</span>
      </footer>
    </div>
  );
}

export function PageTitle({
  eyebrow,
  title,
  description,
}: {
  eyebrow: string;
  title: string;
  description?: string;
}) {
  return (
    <div className="page-title">
      <span className="eyebrow">{eyebrow}</span>
      <h1>{title}</h1>
      {description && <p>{description}</p>}
    </div>
  );
}

export function Notice({ children, tone = "info" }: { children: ReactNode; tone?: "info" | "success" | "error" }) {
  return <div className={`notice notice-${tone}`} role={tone === "error" ? "alert" : "status"}>{children}</div>;
}

export function LoadingState({ label = "Loading..." }: { label?: string }) {
  return <div className="loading-state"><span className="spinner" />{label}</div>;
}
