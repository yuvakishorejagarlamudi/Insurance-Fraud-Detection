
import React, { useState } from "react";
import { createRoot } from "react-dom/client";

type Indicator = {
  code: string;
  score: number;
  evidence: Record<string, unknown>;
};

type Result = {
  claim_id: string;
  status: string;
  risk_score: number;
  risk_level: string;
  decision: string;
  indicators: Indicator[];
};

const API = "http://127.0.0.1:8000";

function App() {
  const [form, setForm] = useState({
    claimant_id: "",
    policy_id: "",
    incident_description: "",
    provider_id: "",
    invoice_number: "",
    claimed_amount: "",
    approved_amount: "",
    payment_amount: "",
    incident_date: ""
  });

  const [result, setResult] = useState<Result | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  function update(key: string, value: string) {
    setForm(previous => ({ ...previous, [key]: value }));
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setResult(null);
    setLoading(true);

    try {
      const response = await fetch(
        `${API}/api/claim-intake/submit`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            ...form,
            claimed_amount: Number(form.claimed_amount),
            approved_amount: Number(form.approved_amount),
            payment_amount: Number(form.payment_amount)
          })
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          typeof data.detail === "string"
            ? data.detail
            : JSON.stringify(data.detail)
        );
      }

      setResult(data);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Submission failed"
      );
    } finally {
      setLoading(false);
    }
  }

  const fields = [
    ["claimant_id", "Claimant ID"],
    ["policy_id", "Policy ID"],
    ["provider_id", "Provider ID"],
    ["invoice_number", "Invoice Number"],
    ["incident_description", "Incident Description"],
    ["incident_date", "Incident Date"],
    ["claimed_amount", "Claimed Amount"],
    ["approved_amount", "Approved Amount"],
    ["payment_amount", "Payment Amount"]
  ];

  return (
    <main style={{
      maxWidth: 900,
      margin: "40px auto",
      padding: 24,
      fontFamily: "Arial, sans-serif",
      color: "#17233a"
    }}>
      <a href="/">← Back to Dashboard</a>

      <h1>New Insurance Claim</h1>
      <p>
        Submit a claim and automatically generate a fraud risk assessment.
      </p>

      <form onSubmit={submit} style={{
        display: "grid",
        gap: 16,
        padding: 24,
        border: "1px solid #ddd",
        borderRadius: 12
      }}>
        {fields.map(([key, label]) => (
          <label key={key} style={{
            display: "grid",
            gap: 6,
            fontWeight: 600
          }}>
            {label}

            {key === "incident_description" ? (
              <textarea
                required
                minLength={5}
                value={form.incident_description}
                onChange={e => update(key, e.target.value)}
                rows={3}
              />
            ) : (
              <input
                required
                type={
                  key === "incident_date" ? "date"
                  : key.includes("amount") ? "number"
                  : "text"
                }
                step={key.includes("amount") ? "0.01" : undefined}
                min={key.includes("amount") ? "0" : undefined}
                value={form[key as keyof typeof form]}
                onChange={e => update(key, e.target.value)}
                style={{ padding: 10 }}
              />
            )}
          </label>
        ))}

        <button
          type="submit"
          disabled={loading}
          style={{
            padding: 14,
            background: "#175cd3",
            color: "white",
            border: 0,
            borderRadius: 8,
            cursor: "pointer"
          }}
        >
          {loading
            ? "Analyzing..."
            : "Submit Claim & Analyze Fraud"}
        </button>
      </form>

      {error && (
        <p role="alert" style={{ color: "#b42318" }}>
          {error}
        </p>
      )}

      {result && (
        <section style={{
          marginTop: 28,
          padding: 24,
          border: "1px solid #ddd",
          borderRadius: 12
        }}>
          <h2>Fraud Analysis Result</h2>

          <p><strong>Claim:</strong> {result.claim_id}</p>
          <p><strong>Status:</strong> {result.status}</p>

          <h2>
            Risk Score: {result.risk_score}/100
          </h2>

          <h3>
            Risk Level: {result.risk_level}
          </h3>

          <p>
            <strong>Decision:</strong> {result.decision}
          </p>

          <h3>Detected Fraud Indicators</h3>

          {result.indicators.length === 0 ? (
            <p>
              No fraud indicators triggered by the current intake rules.
              This does not guarantee that the claim is fraud-free.
            </p>
          ) : (
            result.indicators.map((item, index) => (
              <article key={index} style={{
                padding: 16,
                marginBottom: 12,
                background: "#fff5f3",
                borderRadius: 8
              }}>
                <strong>{item.code}</strong>
                <p>Rule score: {item.score}</p>
                <pre style={{
                  whiteSpace: "pre-wrap",
                  overflowWrap: "anywhere"
                }}>
                  {JSON.stringify(item.evidence, null, 2)}
                </pre>
              </article>
            ))
          )}

          <p>
            <a
              href={`${API}/api/claim-intake/${result.claim_id}`}
              target="_blank"
              rel="noreferrer"
            >
              View saved claim and audit events
            </a>
          </p>
        </section>
      )}
    </main>
  );
}

createRoot(
  document.getElementById("root")!
).render(<App />);
