import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { ArrowRight, Bell, GraduationCap, LogOut, MessageCircle, Search, ShoppingBag, ShoppingCart, UserRound } from "lucide-react";
import { useAuth } from "../lib/auth";
import { useCart } from "../lib/cart";
import { CompareTray } from "../features/compare/CompareTray";
import { useNotifications } from "../lib/notifications";
import { api } from "../lib/api";

export function SiteLayout() {
  const { user, token, signOut } = useAuth();
  const { itemCount } = useCart();
  const { unreadCount } = useNotifications();
  const [search, setSearch] = useState("");
  const [unreadMessages, setUnreadMessages] = useState(0);
  const navigate = useNavigate();

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
    if (!window.confirm("Are you sure to logout?")) return;
    try {
      await signOut();
      navigate("/");
    } catch (error) {
      navigate("/");
      window.alert(error instanceof Error ? error.message : "Could not sign out.");
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
          <NavLink to={user ? "/account" : "/login"} className="header-link">
            <UserRound size={19} />
            <span><small>{user ? "Hello," : "Welcome"}</small>{user?.full_name.split(" ")[0] ?? "Sign in"}</span>
          </NavLink>
          <NavLink to="/cart" className="header-link cart-header-link" aria-label="Cart">
            <ShoppingCart size={19} /><span><small>Your items</small>Cart <b className="cart-count">{itemCount}</b></span>
          </NavLink>
          {user ? (
            <button type="button" className="header-link header-signout" onClick={handleSignOut}>
              <LogOut size={18} /><span><small>Account</small>Sign out</span>
            </button>
          ) : (
            <Link to="/register" className="header-link header-register">
              <span><small>New here?</small>Create account</span>
            </Link>
          )}
        </nav>
      </header>
      <nav className="category-nav" aria-label="Main navigation">
        <NavLink to="/" end>Discover</NavLink>
        <NavLink to="/bundles">Bundles</NavLink>
        <NavLink to="/sell">Sell on CampusKart</NavLink>
        {user && <NavLink to="/orders">My orders</NavLink>}
        {(user?.role === "buyer" || user?.role === "seller") && <NavLink to="/messages" className="notification-nav-link"><MessageCircle size={14} /> Messages{unreadMessages > 0 && <b className="notification-count">{unreadMessages > 99 ? "99+" : unreadMessages}</b>}</NavLink>}
        {user?.role === "buyer" && <NavLink to="/buy-again">Buy again</NavLink>}
        {user?.role === "buyer" && <NavLink to="/wishlist">Wishlist</NavLink>}
        {user?.role === "buyer" && <NavLink to="/my-questions">My questions</NavLink>}
        {user?.role === "buyer" && <NavLink to="/returns">Returns &amp; refunds</NavLink>}
        {user?.role === "buyer" && <NavLink to="/support">Support</NavLink>}
        {user?.role === "buyer" && <NavLink to="/requests">Request anything</NavLink>}
        {user?.role === "buyer" && <NavLink to="/notifications" className="notification-nav-link"><Bell size={14} /> Notifications{unreadCount > 0 && <b className="notification-count">{unreadCount > 99 ? "99+" : unreadCount}</b>}</NavLink>}
        {user?.role === "seller" && <NavLink to="/seller/products">Seller studio</NavLink>}
        {user?.role === "seller" && <NavLink to="/seller/orders">Seller orders</NavLink>}
        {user?.role === "admin" && <NavLink to="/admin">Admin</NavLink>}
        <span className="nav-note">Good finds. Great campus energy.</span>
      </nav>
      <main className="main-content"><Outlet /></main>
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
