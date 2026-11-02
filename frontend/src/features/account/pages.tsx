import { ArrowRight, BadgeCheck, CalendarDays, Mail, Phone, UserRound } from "lucide-react";
import { Link } from "react-router-dom";
import { PageTitle } from "../../components/SiteLayout";
import { useAuth } from "../../lib/auth";

export function AccountPage() {
  const { user } = useAuth();
  if (!user) return null;

  return (
    <div className="content-narrow account-page">
      <PageTitle eyebrow="YOUR CAMPUSKART" title={`Hey, ${user.full_name.split(" ")[0]}.`} description="Your account, all in one place." />
      <div className="account-card">
        <div className="account-avatar">{user.full_name.trim().charAt(0).toUpperCase()}</div>
        <div className="account-identity"><h2>{user.full_name}</h2><span className="role-pill"><BadgeCheck size={14} />{user.role}</span></div>
        <div className="account-details">
          <div><Mail size={17} /><span><small>Email</small>{user.email}</span></div>
          <div><Phone size={17} /><span><small>Phone</small>{user.phone_number}</span></div>
          <div><CalendarDays size={17} /><span><small>Member since</small>{new Date(user.created_at).toLocaleDateString()}</span></div>
          <div><UserRound size={17} /><span><small>Account ID</small>#{user.id}</span></div>
        </div>
      </div>
      {user.role === "buyer" && (
        <div className="account-callout"><div><span className="eyebrow">READY TO SELL?</span><h3>Turn your campus finds into someone else's.</h3><p>Apply to join the seller community. An admin will review your application.</p></div><Link className="button button-dark" to="/sell">Apply to sell <ArrowRight size={16} /></Link></div>
      )}
      {user.role === "buyer" && <div className="account-callout"><div><span className="eyebrow">DELIVERY DETAILS</span><h3>Keep your addresses ready.</h3><p>Save multiple delivery addresses and choose one during checkout.</p></div><Link className="button button-dark" to="/addresses">Manage addresses <ArrowRight size={16} /></Link></div>}
      {user.role === "seller" && <div className="account-callout"><div><span className="eyebrow">SELLER SPACE</span><h3>Your seller journey starts here.</h3><p>Add and manage your product listings in Seller Studio.</p></div><Link className="button button-dark" to="/seller/products">Open Seller Studio <ArrowRight size={16} /></Link></div>}
      {user.role === "admin" && <div className="account-callout"><div><span className="eyebrow">ADMIN SPACE</span><h3>Keep the marketplace moving.</h3><p>Review applications and keep categories up to date.</p></div><Link className="button button-dark" to="/admin">Open admin <ArrowRight size={16} /></Link></div>}
      <div className="account-callout"><div><span className="eyebrow">YOUR PURCHASES</span><h3>Keep track of your campus finds.</h3><p>See your order history, delivery details, and COD totals.</p></div><Link className="button button-dark" to="/orders">View my orders <ArrowRight size={16} /></Link></div>
    </div>
  );
}
