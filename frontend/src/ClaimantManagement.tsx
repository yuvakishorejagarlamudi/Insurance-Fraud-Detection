import { useEffect, useState } from 'react';
const API = 'http://127.0.0.1:8000';
type Claimant = { claimant_id: string; claimant_name: string; age: number | null; status: 'ACTIVE' | 'INACTIVE' };
type Claim = { claim_id: string; status: string; claimed_amount: number };
type Details = Claimant & { claims: Claim[] };
type Form = { claimant_name: string; age: string; status: 'ACTIVE' | 'INACTIVE'; address: string; phone: string };
const empty: Form = { claimant_name: '', age: '', status: 'ACTIVE', address: '', phone: '' };
async function request(path: string, options?: RequestInit) {
  const res = await fetch(API + path, options);
  const json = await res.json();
  if (!res.ok) throw new Error(typeof json.detail === 'string' ? json.detail : JSON.stringify(json.detail || json));
  return json;
}
export default function ClaimantManagement({ onChanged }: { onChanged?: () => void }) {
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(0);
  const [items, setItems] = useState<Claimant[]>([]);
  const [total, setTotal] = useState(0);
  const [form, setForm] = useState<Form>(empty);
  const [editing, setEditing] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [details, setDetails] = useState<Details | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [refresh, setRefresh] = useState(0);
  useEffect(() => {
    let cancelled = false;
    request(`/api/claimants?search=${encodeURIComponent(search)}&offset=${page * 25}&limit=25`)
      .then(data => { if (!cancelled) { setItems(data.items); setTotal(data.total); } })
      .catch(e => { if (!cancelled) setError(String(e.message)); });
    return () => { cancelled = true; };
  }, [search, page, refresh]);
  const reload = () => { setRefresh(n => n + 1); onChanged?.(); };
  const openAdd = () => { setForm(empty); setEditing(null); setShowForm(true); setError(''); };
  const openEdit = (c: Claimant) => { setForm({ claimant_name: c.claimant_name, age: c.age == null ? '' : String(c.age), status: c.status, address: '', phone: '' }); setEditing(c.claimant_id); setShowForm(true); setError(''); };
  async function save(e: React.FormEvent) {
    e.preventDefault(); setBusy(true); setError('');
    const age = form.age.trim() === '' ? null : Number(form.age);
    if (age !== null && (!Number.isInteger(age) || age < 0 || age > 120)) { setError('Age must be between 0 and 120'); setBusy(false); return; }
    const payload = editing ? { claimant_name: form.claimant_name, age, status: form.status, ...(form.address.trim() ? { address: form.address } : {}), ...(form.phone.trim() ? { phone: form.phone } : {}) } : { ...form, age };
    try {
      await request(editing ? `/api/claimants/${encodeURIComponent(editing)}` : '/api/claimants', { method: editing ? 'PUT' : 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
      setShowForm(false); reload();
    } catch (err) { setError(err instanceof Error ? err.message : String(err)); }
    finally { setBusy(false); }
  }
  async function remove(c: Claimant) {
    if (!window.confirm(`Delete ${c.claimant_name} (${c.claimant_id})? This cannot be undone.`)) return;
    setError(''); setBusy(true);
    try { await request(`/api/claimants/${encodeURIComponent(c.claimant_id)}`, { method: 'DELETE' }); setDetails(null); reload(); }
    catch (err) { setError(err instanceof Error ? err.message : String(err)); }
    finally { setBusy(false); }
  }
  async function view(c: Claimant) {
    setError('');
    try { setDetails(await request(`/api/claimants/${encodeURIComponent(c.claimant_id)}`)); }
    catch (err) { setError(err instanceof Error ? err.message : String(err)); }
  }
  const field = (label: string, key: keyof Form, type = 'text', required = false) => <label style={{ display: 'grid', gap: 5 }} key={key}>{label}<input type={type} required={required} value={form[key]} onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))} style={{ padding: 9, borderRadius: 6, border: '1px solid #a8b5c5' }} /></label>;
  return <section className="panel" id="claimant-management">
    <h2>Claimant Management</h2><p>Search, register, edit, and manage insurance claimants.</p>
    <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 15 }}><input aria-label="Search claimants" placeholder="Search by claimant ID or name" value={search} onChange={e => { setSearch(e.target.value); setPage(0); }} style={{ padding: 10, flex: 1, minWidth: 200 }} /><button onClick={openAdd}>+ Add Claimant</button></div>
    {error && <p role="alert" className="error">{error}</p>}
    {showForm && <form onSubmit={save} style={{ border: '1px solid #cbd5e1', padding: 16, borderRadius: 10, marginBottom: 18 }}><h3>{editing ? `Edit ${editing}` : 'Add Claimant'}</h3><div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(190px,1fr))', gap: 12 }}>
      {field('Full name', 'claimant_name', 'text', true)}{field('Age (optional)', 'age', 'number')}
      <label style={{ display: 'grid', gap: 5 }}>Status<select value={form.status} onChange={e => setForm(f => ({ ...f, status: e.target.value as Form['status'] }))}><option value="ACTIVE">ACTIVE</option><option value="INACTIVE">INACTIVE</option></select></label>
      {field(editing ? 'New address (leave blank to keep existing)' : 'Address', 'address', 'text', !editing)}{field(editing ? 'New phone (leave blank to keep existing)' : 'Phone', 'phone', 'tel', !editing)}
    </div><p style={{ fontSize: 12 }}>Addresses and phone numbers are hashed before database storage. Existing hashes cannot be converted back to the original values.</p><div style={{ display: 'flex', gap: 8 }}><button type="submit" disabled={busy}>{busy ? 'Saving...' : 'Save Claimant'}</button><button type="button" onClick={() => setShowForm(false)}>Cancel</button></div></form>}
    <p>{total} matching claimants</p><div style={{ overflowX: 'auto' }}><table style={{ width: '100%', borderCollapse: 'collapse' }}><thead><tr>{['Claimant ID', 'Name', 'Age', 'Status', 'Actions'].map(x => <th key={x} style={{ textAlign: 'left', padding: 9 }}>{x}</th>)}</tr></thead><tbody>{items.map(c => <tr key={c.claimant_id}><td style={{ padding: 9 }}>{c.claimant_id}</td><td style={{ padding: 9 }}>{c.claimant_name}</td><td style={{ padding: 9 }}>{c.age ?? 'Not provided'}</td><td style={{ padding: 9 }}>{c.status}</td><td style={{ padding: 9 }}><div style={{ display: 'flex', gap: 6 }}><button onClick={() => view(c)}>View</button><button onClick={() => openEdit(c)}>Edit</button><button disabled={busy} onClick={() => remove(c)}>Delete</button></div></td></tr>)}</tbody></table></div>
    <div style={{ display: 'flex', gap: 12, marginTop: 12 }}><button disabled={page === 0} onClick={() => setPage(p => p - 1)}>Previous</button><span>Page {page + 1} / {Math.max(1, Math.ceil(total / 25))}</span><button disabled={(page + 1) * 25 >= total} onClick={() => setPage(p => p + 1)}>Next</button></div>
    {details && <div style={{ marginTop: 16, border: '1px solid #cbd5e1', padding: 16, borderRadius: 10 }}><button onClick={() => setDetails(null)} style={{ float: 'right' }}>Close</button><h3>{details.claimant_name} — linked claims</h3><p>{details.claimant_id} | {details.status} | Age: {details.age ?? 'Not provided'}</p>{details.claims.length ? <ul>{details.claims.map(c => <li key={c.claim_id}>{c.claim_id} — {c.status} — ₹{c.claimed_amount.toLocaleString('en-IN')}</li>)}</ul> : <p>No linked claims</p>}</div>}
  </section>;
}
