const API="http://127.0.0.1:8000";
export async function getDashboard(){const r=await fetch(`${API}/api/dashboard`);if(!r.ok)throw new Error("API request failed");return r.json();}
export async function getClaims(){const r=await fetch(`${API}/api/claims`);if(!r.ok)throw new Error("API request failed");return r.json();}
