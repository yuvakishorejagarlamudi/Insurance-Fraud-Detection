
import { useEffect, useState } from "react";

const API = "http://127.0.0.1:8000";

type Indicator = {
  claim_id: string;
  indicator_type: string;
  risk_score: number;
  evidence: Record<string, unknown>;
};

type FraudClaim = {
  claim_id: string;
  risk_score: number;
  risk_level: string;
  indicators: Indicator[];
};

type FraudResponse = {
  total_suspicious_claims: number;
  high_risk: number;
  medium_risk: number;
  low_risk: number;
  claims: FraudClaim[];
};

type ProviderPattern = {
  provider_id: string;
  claimant_count: number;
  claim_count: number;
};

type NetworkResponse = {
  nodes: number;
  explicit_edges: number;
  connected_components: number;
  largest_component_size: number;
  shared_address_groups: unknown[];
  shared_bank_groups: unknown[];
  high_volume_providers: ProviderPattern[];
};

const cardStyle: React.CSSProperties = {
  padding: 18,
  background: "#ffffff",
  border: "1px solid #e2e8f0",
  borderRadius: 12,
  boxShadow: "0 2px 6px rgba(0,0,0,0.04)"
};

const cellStyle: React.CSSProperties = {
  padding: 12,
  borderBottom: "1px solid #e2e8f0",
  textAlign: "left"
};

function riskColor(level: string) {
  if (level === "HIGH") return "#dc2626";
  if (level === "MEDIUM") return "#d97706";
  return "#16a34a";
}

export default function FraudIntelligence() {
  const [fraud, setFraud] = useState<FraudResponse | null>(null);
  const [network, setNetwork] = useState<NetworkResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedClaim, setSelectedClaim] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function loadData() {
      try {
        const [fraudResponse, networkResponse] = await Promise.all([
          fetch(`${API}/api/fraud-analysis`),
          fetch(`${API}/api/network-analysis`)
        ]);

        if (!fraudResponse.ok || !networkResponse.ok) {
          throw new Error("Failed to load fraud intelligence data");
        }

        const fraudData: FraudResponse = await fraudResponse.json();
        const networkData: NetworkResponse = await networkResponse.json();

        if (active) {
          setFraud(fraudData);
          setNetwork(networkData);
        }
      } catch (err) {
        if (active) {
          setError(
            err instanceof Error ? err.message : "Unknown error"
          );
        }
      } finally {
        if (active) setLoading(false);
      }
    }

    loadData();

    return () => {
      active = false;
    };
  }, []);

  if (loading) {
    return <p>Loading fraud intelligence...</p>;
  }

  if (error) {
    return (
      <div style={{ ...cardStyle, color: "#dc2626" }}>
        Error: {error}
      </div>
    );
  }

  if (!fraud || !network) {
    return <p>No fraud intelligence data available.</p>;
  }

  const selected = fraud.claims.find(
    item => item.claim_id === selectedClaim
  );

  return (
    <section style={{ marginTop: 30, color: "#0f172a" }}>
      <h2>Fraud Intelligence Dashboard</h2>
      <p>
        Automated detection results and suspicious network analysis
      </p>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))",
          gap: 14,
          marginTop: 20
        }}
      >
        {[
          ["Suspicious Claims", fraud.total_suspicious_claims],
          ["High Risk", fraud.high_risk],
          ["Medium Risk", fraud.medium_risk],
          ["Low Risk", fraud.low_risk],
          ["Network Nodes", network.nodes],
          ["Relationship Edges", network.explicit_edges]
        ].map(([label, value]) => (
          <div key={String(label)} style={cardStyle}>
            <div style={{ color: "#64748b", fontSize: 13 }}>
              {label}
            </div>
            <div style={{ fontSize: 28, fontWeight: 700 }}>
              {value}
            </div>
          </div>
        ))}
      </div>

      <div style={{ ...cardStyle, marginTop: 24 }}>
        <h3>Automatically Flagged Claims</h3>

        <div style={{ overflowX: "auto" }}>
          <table
            style={{
              width: "100%",
              borderCollapse: "collapse"
            }}
          >
            <thead>
              <tr>
                <th style={cellStyle}>Claim ID</th>
                <th style={cellStyle}>Risk Score</th>
                <th style={cellStyle}>Risk Level</th>
                <th style={cellStyle}>Indicators</th>
                <th style={cellStyle}>Action</th>
              </tr>
            </thead>

            <tbody>
              {fraud.claims.map(claim => (
                <tr key={claim.claim_id}>
                  <td style={cellStyle}>{claim.claim_id}</td>
                  <td style={cellStyle}>
                    {claim.risk_score}/100
                  </td>
                  <td
                    style={{
                      ...cellStyle,
                      color: riskColor(claim.risk_level),
                      fontWeight: 700
                    }}
                  >
                    {claim.risk_level}
                  </td>
                  <td style={cellStyle}>
                    {claim.indicators
                      .map(item => item.indicator_type)
                      .join(", ")}
                  </td>
                  <td style={cellStyle}>
                    <button
                      type="button"
                      onClick={() =>
                        setSelectedClaim(
                          selectedClaim === claim.claim_id
                            ? null
                            : claim.claim_id
                        )
                      }
                    >
                      {selectedClaim === claim.claim_id
                        ? "Hide Evidence"
                        : "View Evidence"}
                    </button>
                  </td>
                </tr>
              ))}

              {fraud.claims.length === 0 && (
                <tr>
                  <td colSpan={5} style={cellStyle}>
                    No suspicious claims detected.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {selected && (
        <div style={{ ...cardStyle, marginTop: 20 }}>
          <h3>Evidence: {selected.claim_id}</h3>

          {selected.indicators.map((indicator, index) => (
            <div key={`${indicator.indicator_type}-${index}`}>
              <h4>{indicator.indicator_type}</h4>
              <pre
                style={{
                  padding: 12,
                  background: "#f1f5f9",
                  borderRadius: 8,
                  overflowX: "auto"
                }}
              >
                {JSON.stringify(indicator.evidence, null, 2)}
              </pre>
            </div>
          ))}
        </div>
      )}

      <div style={{ ...cardStyle, marginTop: 24 }}>
        <h3>Network Analysis</h3>

        <p>
          Connected components: {network.connected_components}
        </p>
        <p>
          Largest component: {network.largest_component_size} nodes
        </p>
        <p>
          Shared address groups: {network.shared_address_groups.length}
        </p>
        <p>
          Shared bank-account groups: {network.shared_bank_groups.length}
        </p>

        <h4>High-Volume Providers</h4>

        <div style={{ overflowX: "auto" }}>
          <table
            style={{
              width: "100%",
              borderCollapse: "collapse"
            }}
          >
            <thead>
              <tr>
                <th style={cellStyle}>Provider</th>
                <th style={cellStyle}>Claimants</th>
                <th style={cellStyle}>Claims</th>
              </tr>
            </thead>

            <tbody>
              {network.high_volume_providers
                .slice(0, 10)
                .map(provider => (
                  <tr key={provider.provider_id}>
                    <td style={cellStyle}>{provider.provider_id}</td>
                    <td style={cellStyle}>
                      {provider.claimant_count}
                    </td>
                    <td style={cellStyle}>
                      {provider.claim_count}
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </div>

      <p style={{ marginTop: 16, color: "#64748b" }}>
        Risk indicators are investigative leads, not proof of fraud.
        Shared addresses and high provider volumes are not automatically
        classified as fraudulent.
      </p>
    </section>
  );
}
