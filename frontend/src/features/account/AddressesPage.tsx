import { useEffect, useState, type FormEvent } from "react";
import { MapPin, Pencil, Plus, Star, Trash2 } from "lucide-react";
import { LoadingState, Notice, PageTitle } from "../../components/SiteLayout";
import { api } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import type { SavedAddress, SavedAddressInput } from "../../lib/types";

const emptyAddress: SavedAddressInput = {
  full_name: "", phone_number: "", address_line: "", city: "", state: "", pin_code: "", is_default: false,
};

export function AddressesPage() {
  const { token } = useAuth();
  const [addresses, setAddresses] = useState<SavedAddress[]>([]);
  const [form, setForm] = useState<SavedAddressInput>(emptyAddress);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  async function reload() {
    if (!token) return;
    const items = await api.listAddresses(token);
    setAddresses(items);
  }

  useEffect(() => {
    let active = true;
    if (!token) return;
    api.listAddresses(token).then((items) => { if (active) setAddresses(items); })
      .catch((reason: unknown) => { if (active) setError(reason instanceof Error ? reason.message : "Could not load saved addresses."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [token]);

  function beginEdit(address: SavedAddress) {
    setEditingId(address.id);
    setForm({
      full_name: address.full_name,
      phone_number: address.phone_number,
      address_line: address.address_line,
      city: address.city,
      state: address.state,
      pin_code: address.pin_code,
      is_default: address.is_default,
    });
    setError("");
  }

  function resetForm() {
    setEditingId(null);
    setForm(emptyAddress);
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) return;
    setBusy(true); setError(""); setSuccess("");
    try {
      if (editingId) await api.updateAddress(editingId, form, token);
      else await api.createAddress(form, token);
      await reload();
      setSuccess(editingId ? "Address updated." : "Address saved.");
      resetForm();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not save this address.");
    } finally { setBusy(false); }
  }

  async function makeDefault(id: number) {
    if (!token) return;
    setError("");
    try { await api.updateAddress(id, { is_default: true }, token); await reload(); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Could not update the default address."); }
  }

  async function remove(id: number) {
    if (!token || !window.confirm("Delete this saved address?")) return;
    setError("");
    try { await api.deleteAddress(id, token); await reload(); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Could not delete this address."); }
  }

  return <section className="content-narrow addresses-page">
    <PageTitle eyebrow="YOUR DELIVERY DETAILS" title="Saved addresses" description="Keep delivery addresses ready for your next order." />
    {error && <Notice tone="error">{error}</Notice>}
    {success && <Notice tone="success">{success}</Notice>}
    {loading ? <LoadingState label="Loading saved addresses..." /> : <div className="saved-address-list">
      {addresses.length ? addresses.map((address) => <article className="saved-address-card" key={address.id}>
        <div className="saved-address-title"><span><MapPin size={17} /> {address.full_name}</span>{address.is_default && <b><Star size={13} fill="currentColor" /> Default</b>}</div>
        <p>{address.phone_number}</p><p>{address.address_line}</p>
        <p>{address.city}, {address.state} {address.pin_code}</p>
        <div className="saved-address-actions">
          {!address.is_default && <button type="button" className="button button-outline" onClick={() => void makeDefault(address.id)}><Star size={14} /> Set as default</button>}
          <button type="button" className="button button-outline" onClick={() => beginEdit(address)}><Pencil size={14} /> Edit</button>
          <button type="button" className="button button-outline address-delete-button" onClick={() => void remove(address.id)}><Trash2 size={14} /> Delete</button>
        </div>
      </article>) : <div className="empty-state"><MapPin size={28} /><h3>No saved addresses</h3><p>Add an address here, or save one while checking out.</p></div>}
    </div>}
    <form className="form-card saved-address-form" onSubmit={(event) => void save(event)}>
      <div className="form-card-heading"><span className="card-icon"><Plus size={19} /></span><div><h2>{editingId ? "Edit address" : "Add an address"}</h2><p>Enter the details used for delivery.</p></div></div>
      <div className="checkout-fields">
        <label>Full name<input required maxLength={120} autoComplete="name" value={form.full_name} onChange={(event) => setForm((current) => ({ ...current, full_name: event.target.value }))} /></label>
        <label>Phone number<input required type="tel" minLength={10} maxLength={16} autoComplete="tel" value={form.phone_number} onChange={(event) => setForm((current) => ({ ...current, phone_number: event.target.value }))} /></label>
        <label className="checkout-field-full">Address<input required minLength={5} maxLength={1000} autoComplete="street-address" value={form.address_line} onChange={(event) => setForm((current) => ({ ...current, address_line: event.target.value }))} placeholder="Building, street, hostel, room" /></label>
        <label>City<input required maxLength={100} value={form.city} onChange={(event) => setForm((current) => ({ ...current, city: event.target.value }))} /></label>
        <label>State<input required maxLength={100} value={form.state} onChange={(event) => setForm((current) => ({ ...current, state: event.target.value }))} /></label>
        <label>PIN code<input required inputMode="numeric" pattern="[0-9]{6}" minLength={6} maxLength={6} value={form.pin_code} onChange={(event) => setForm((current) => ({ ...current, pin_code: event.target.value }))} /></label>
      </div>
      <label className="default-address-option"><input type="checkbox" checked={form.is_default} onChange={(event) => setForm((current) => ({ ...current, is_default: event.target.checked }))} /> Set as default delivery address</label>
      <div className="saved-address-form-actions"><button className="button button-dark" disabled={busy}>{busy ? "Saving..." : editingId ? "Save changes" : "Save address"}</button>{editingId && <button type="button" className="button button-outline" onClick={resetForm}>Cancel</button>}</div>
    </form>
  </section>;
}
