
import { useEffect, useState } from "react";
import FraudIntelligence from "./FraudIntelligence";
import ClaimantManagement from "./ClaimantManagement";

type Dashboard = {
  claimants: number;
  claims: number;
  providers: number;
  investigations: number;
};

type Investigation = {
  investigation_id: string;
  claim_id: string;
  status: string;
  priority: string;
  assigned_analyst: string | null;
  outcome: string | null;
  created_at: string;
};

type Claim = {
  claim_id: string;
  claimant_id: string;
  claimed_amount: number;
  approved_amount: number;
  status: string;
  risk_score: number;
};

type FraudIndicator = {
  indicator_id: string;
  indicator_type: string;
  description: string;
  score: number;
  detected_at: string;
};

type ClaimEvidence = {
  claim_id: string;
  claimant_id: string;
  risk_score: number;
  risk_category: string;
  claimed_amount: number;
  approved_amount: number;
  indicators: FraudIndicator[];
  indicator_count: number;
};

type NetworkNode = {
  id: string;
  type: string;
  label: string;
  risk_score?: number;
  amount?: number;
};

type NetworkLink = {
  source: string;
  target: string;
  relationship: string;
};

type ClaimNetwork = {
  claim_id: string;
  risk_score: number;
  node_count: number;
  link_count: number;
  stored_relationship_count: number;
  nodes: NetworkNode[];
  links: NetworkLink[];
};

const API = "http://127.0.0.1:8000";

const cellStyle = {
  padding: 12,
  borderBottom: "1px solid #ddd"
};

const money = (amount: number) =>
  new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR"
  }).format(amount);

function riskColor(risk: string) {
  if (risk === "HIGH") return "#dc2626";
  if (risk === "MEDIUM") return "#d97706";
  return "#16a34a";
}

function nodeColor(type: string) {
  switch (type) {
    case "CLAIM":
      return "#dc2626";
    case "CLAIMANT":
      return "#2563eb";
    case "INVOICE":
      return "#d97706";
    case "PROVIDER":
      return "#16a34a";
    default:
      return "#64748b";
  }
}

function NetworkGraph({
  network
}: {
  network: ClaimNetwork;
}) {
  const [selectedNodeId, setSelectedNodeId] =
    useState<string | null>(null);

  const selectedNode = network.nodes.find(
    node => node.id === selectedNodeId
  );

  // Arrange the nodes in a circle around the claim.
  // This works for networks with different node counts.
  const width = 760;
  const height = 400;
  const centerX = width / 2;
  const centerY = height / 2;

  const mainClaimId = `CLAIM:${network.claim_id}`;

  const otherNodes = network.nodes.filter(
    node => node.id !== mainClaimId
  );

  const positions = new Map<
    string,
    { x: number; y: number }
  >();

  positions.set(mainClaimId, {
    x: centerX,
    y: centerY
  });

  otherNodes.forEach((node, index) => {
    const angle =
      -Math.PI / 2 +
      (2 * Math.PI * index) /
        Math.max(otherNodes.length, 1);

    positions.set(node.id, {
      x: centerX + Math.cos(angle) * 250,
      y: centerY + Math.sin(angle) * 135
    });
  });

  return (
    <div>
      <div
        style={{
          overflowX: "auto",
          border: "1px solid #dbe2ea",
          borderRadius: 12,
          padding: 12,
          marginTop: 16
        }}
      >
        <svg
          viewBox={`0 0 ${width} ${height}`}
          style={{
            width: "100%",
            minWidth: 550,
            display: "block"
          }}
          role="img"
          aria-label="Claim relationship network"
        >
          {network.links.map((link, index) => {
            const source = positions.get(link.source);
            const target = positions.get(link.target);

            if (!source || !target) return null;

            const middleX =
              (source.x + target.x) / 2;
            const middleY =
              (source.y + target.y) / 2;

            return (
              <g key={`${link.source}-${link.target}-${index}`}>
                <line
                  x1={source.x}
                  y1={source.y}
                  x2={target.x}
                  y2={target.y}
                  stroke="#94a3b8"
                  strokeWidth={2}
                />
                <text
                  x={middleX}
                  y={middleY - 9}
                  textAnchor="middle"
                  fontSize={10}
                  fill="#64748b"
                >
                  {link.relationship.replace(/_/g, " ")}
                </text>
              </g>
            );
          })}

          {network.nodes.map(node => {
            const position = positions.get(node.id);

            if (!position) return null;

            const isSelected =
              selectedNodeId === node.id;

            return (
              <g
                key={node.id}
                transform={`translate(${position.x}, ${position.y})`}
                onClick={() => setSelectedNodeId(node.id)}
                style={{ cursor: "pointer" }}
                role="button"
                tabIndex={0}
                onKeyDown={event => {
                  if (
                    event.key === "Enter" ||
                    event.key === " "
                  ) {
                    event.preventDefault();
                    setSelectedNodeId(node.id);
                  }
                }}
              >
                <circle
                  r={isSelected ? 36 : 30}
                  fill={nodeColor(node.type)}
                  stroke={isSelected ? "#111827" : "#fff"}
                  strokeWidth={isSelected ? 4 : 2}
                />
                <text
                  y={5}
                  textAnchor="middle"
                  fill="white"
                  fontWeight="bold"
                  fontSize={10}
                >
                  {node.type}
                </text>
                <text
                  y={51}
                  textAnchor="middle"
                  fill="currentColor"
                  fontSize={11}
                  fontWeight="600"
                >
                  {node.label.length > 27
                    ? node.label.slice(0, 24) + "..."
                    : node.label}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: 18,
          marginTop: 12
        }}
      >
        {[
          "CLAIM",
          "CLAIMANT",
          "INVOICE",
          "PROVIDER"
        ].map(type => (
          <span
            key={type}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 7
            }}
          >
            <span
              style={{
                width: 12,
                height: 12,
                borderRadius: "50%",
                background: nodeColor(type)
              }}
            />
            {type}
          </span>
        ))}
      </div>

      {selectedNode && (
        <div
          style={{
            border: "1px solid #dbe2ea",
            borderRadius: 10,
            padding: 16,
            marginTop: 16
          }}
        >
          <h3>Selected Network Node</h3>
          <p>
            <strong>Type:</strong> {selectedNode.type}
          </p>
          <p>
            <strong>Name:</strong> {selectedNode.label}
          </p>
          <p>
            <strong>ID:</strong> {selectedNode.id}
          </p>

          {selectedNode.risk_score !== undefined && (
            <p>
              <strong>Risk Score:</strong>{" "}
              {selectedNode.risk_score}
            </p>
          )}

          {selectedNode.amount !== undefined && (
            <p>
              <strong>Invoice Amount:</strong>{" "}
              {money(selectedNode.amount)}
            </p>
          )}

          <button
            onClick={() => setSelectedNodeId(null)}
          >
            Clear Selection
          </button>
        </div>
      )}
    </div>
  );
}

export default function App() {
  const [dashboard, setDashboard] =
    useState<Dashboard | null>(null);
  const [claims, setClaims] = useState<Claim[]>([]);
  const [investigations, setInvestigations] =
    useState<Investigation[]>([]);

  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [updatingId, setUpdatingId] =
    useState<string | null>(null);

  const [evidence, setEvidence] =
    useState<ClaimEvidence | null>(null);
  const [evidenceLoading, setEvidenceLoading] =
    useState(false);
  const [evidenceError, setEvidenceError] =
    useState("");
  const [selectedClaimId, setSelectedClaimId] =
    useState<string | null>(null);

  const [network, setNetwork] =
    useState<ClaimNetwork | null>(null);
  const [networkLoading, setNetworkLoading] =
    useState(false);
  const [networkError, setNetworkError] =
    useState("");
  const [networkClaimId, setNetworkClaimId] =
    useState<string | null>(null);

  async function loadData() {
    setLoading(true);
    setError("");

    try {
      const [
        dashboardResponse,
        claimsResponse,
        investigationResponse
      ] = await Promise.all([
        fetch(`${API}/api/dashboard`),
        fetch(`${API}/api/claims?limit=5000`),
        fetch(`${API}/api/investigations`)
      ]);

      if (
        !dashboardResponse.ok ||
        !claimsResponse.ok ||
        !investigationResponse.ok
      ) {
        throw new Error("Failed to load insurance data");
      }

      const dashboardData: Dashboard =
        await dashboardResponse.json();
      const claimData: Claim[] =
        await claimsResponse.json();
      const investigationData: Investigation[] =
        await investigationResponse.json();

      setDashboard(dashboardData);
      setClaims(claimData);
      setInvestigations(investigationData);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to connect to FastAPI."
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  async function updateInvestigation(item: Investigation) {
    if (item.status === "CLOSED") return;

    const nextStatus =
      item.status === "NEW"
        ? "IN_PROGRESS"
        : "CLOSED";

    let outcome: string | null = null;

    if (nextStatus === "CLOSED") {
      const entered = window.prompt(
        "Enter investigation outcome (Confirmed Fraud, No Fraud, or Inconclusive):"
      );

      if (!entered || !entered.trim()) return;

      outcome = entered.trim();
    }

    setUpdatingId(item.investigation_id);
    setError("");

    try {
      const response = await fetch(
        `${API}/api/investigations/${encodeURIComponent(
          item.investigation_id
        )}`,
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            status: nextStatus,
            outcome
          })
        }
      );

      if (!response.ok) {
        const result = await response.json();
        throw new Error(
          result.detail || "Investigation update failed"
        );
      }

      await loadData();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Investigation update failed"
      );
    } finally {
      setUpdatingId(null);
    }
  }

  async function viewEvidence(claimId: string) {
    setSelectedClaimId(claimId);
    setEvidence(null);
    setEvidenceError("");
    setEvidenceLoading(true);

    try {
      const response = await fetch(
        `${API}/api/claims/${encodeURIComponent(claimId)}/evidence`
      );

      if (!response.ok) {
        throw new Error("Unable to load fraud evidence");
      }

      const result: ClaimEvidence =
        await response.json();

      setEvidence(result);
    } catch (err) {
      setEvidenceError(
        err instanceof Error
          ? err.message
          : "Failed to fetch evidence"
      );
    } finally {
      setEvidenceLoading(false);
    }
  }

  function closeEvidence() {
    setSelectedClaimId(null);
    setEvidence(null);
    setEvidenceError("");
    setEvidenceLoading(false);
  }

  async function viewNetwork(claimId: string) {
    setNetworkClaimId(claimId);
    setNetwork(null);
    setNetworkError("");
    setNetworkLoading(true);

    try {
      const response = await fetch(
        `${API}/api/network/${encodeURIComponent(claimId)}`
      );

      if (!response.ok) {
        throw new Error("Unable to load claim network");
      }

      const result: ClaimNetwork =
        await response.json();

      setNetwork(result);
    } catch (err) {
      setNetworkError(
        err instanceof Error
          ? err.message
          : "Failed to fetch network"
      );
    } finally {
      setNetworkLoading(false);
    }
  }

  function closeNetwork() {
    setNetworkClaimId(null);
    setNetwork(null);
    setNetworkError("");
    setNetworkLoading(false);
  }

  const highRisk = claims.filter(
    c => c.risk_score >= 70
  );

  const mediumRisk = claims.filter(
    c => c.risk_score >= 35 && c.risk_score < 70
  );

  const lowRisk = claims.filter(
    c => c.risk_score < 35
  );

  const suspicious = claims
    .filter(c => c.risk_score >= 35)
    .sort((a, b) => b.risk_score - a.risk_score);

  return (
    <main>
      <header>
        <div>
          <p className="eyebrow">RISK & COMPLIANCE</p>
          <h1>Insurance Fraud Intelligence</h1>
          <p>
            Suspicious claims | Risk scoring | Investigation
          </p>
        </div>

        <span className="pill">
          Synthetic environment
        </span>
      </header>

      <section className="cards">
        {[
          ["Claimants", dashboard?.claimants],
          ["Total Claims", dashboard?.claims],
          ["Providers", dashboard?.providers],
          ["Investigations", dashboard?.investigations]
        ].map(([label, value]) => (
          <article key={String(label)}>
            <p>{label}</p>
            <strong>{value ?? "..."}</strong>
          </article>
        ))}
      </section>

      <section className="panel">
        <h2>Fraud Risk Analysis</h2>
        <p>
          Risk scores calculated using explainable detection rules.
        </p>

        <section className="cards">
          <article>
            <p>High Risk</p>
            <strong style={{ color: "#dc2626" }}>
              {highRisk.length}
            </strong>
          </article>

          <article>
            <p>Medium Risk</p>
            <strong style={{ color: "#d97706" }}>
              {mediumRisk.length}
            </strong>
          </article>

          <article>
            <p>Low Risk</p>
            <strong style={{ color: "#16a34a" }}>
              {lowRisk.length}
            </strong>
          </article>
        </section>

        <button onClick={loadData} disabled={loading}>
          {loading ? "Loading..." : "Refresh Data"}
        </button>
      </section>

      <section className="panel">
        <h2>Suspicious Insurance Claims</h2>
        <p>Claims requiring further investigation.</p>

        <div style={{ overflowX: "auto" }}>
          <table
            style={{
              width: "100%",
              borderCollapse: "collapse"
            }}
          >
            <thead>
              <tr>
                {[
                  "Claim ID",
                  "Claimant",
                  "Claimed Amount",
                  "Status",
                  "Risk Score",
                  "Risk Level",
                  "Evidence",
                  "Network"
                ].map(name => (
                  <th
                    key={name}
                    style={{
                      ...cellStyle,
                      textAlign: "left"
                    }}
                  >
                    {name}
                  </th>
                ))}
              </tr>
            </thead>

            <tbody>
              {suspicious.map(claim => (
                <tr key={claim.claim_id}>
                  <td style={cellStyle}>
                    {claim.claim_id}
                  </td>
                  <td style={cellStyle}>
                    {claim.claimant_id}
                  </td>
                  <td style={cellStyle}>
                    {money(claim.claimed_amount)}
                  </td>
                  <td style={cellStyle}>
                    {claim.status}
                  </td>
                  <td style={cellStyle}>
                    <strong>{claim.risk_score}</strong>
                  </td>
                  <td style={cellStyle}>
                    <strong
                      style={{
                        color: riskColor(
                          claim.risk_score >= 70
                            ? "HIGH"
                            : "MEDIUM"
                        )
                      }}
                    >
                      {claim.risk_score >= 70
                        ? "HIGH"
                        : "MEDIUM"}
                    </strong>
                  </td>
                  <td style={cellStyle}>
                    <button
                      disabled={evidenceLoading}
                      onClick={() =>
                        viewEvidence(claim.claim_id)
                      }
                    >
                      View Evidence
                    </button>
                  </td>
                  <td style={cellStyle}>
                    <button
                      disabled={networkLoading}
                      onClick={() =>
                        viewNetwork(claim.claim_id)
                      }
                    >
                      View Network
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {!loading && suspicious.length === 0 && (
          <p>No suspicious claims returned by the API.</p>
        )}
      </section>

      {selectedClaimId && (
        <section className="panel">
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              gap: 16
            }}
          >
            <div>
              <h2>Fraud Evidence Details</h2>
              <p>Claim: {selectedClaimId}</p>
            </div>

            <button onClick={closeEvidence}>
              Close Details
            </button>
          </div>

          {evidenceLoading && (
            <p>Loading fraud evidence...</p>
          )}

          {evidenceError && (
            <p className="error">{evidenceError}</p>
          )}

          {evidence && (
            <>
              <section className="cards">
                <article>
                  <p>Claim ID</p>
                  <strong>{evidence.claim_id}</strong>
                </article>

                <article>
                  <p>Claimant ID</p>
                  <strong>{evidence.claimant_id}</strong>
                </article>

                <article>
                  <p>Risk Score</p>
                  <strong
                    style={{
                      color: riskColor(
                        evidence.risk_category
                      )
                    }}
                  >
                    {evidence.risk_score}
                  </strong>
                </article>

                <article>
                  <p>Risk Category</p>
                  <strong
                    style={{
                      color: riskColor(
                        evidence.risk_category
                      )
                    }}
                  >
                    {evidence.risk_category}
                  </strong>
                </article>
              </section>

              <section className="cards">
                <article>
                  <p>Claimed Amount</p>
                  <strong>
                    {money(evidence.claimed_amount)}
                  </strong>
                </article>

                <article>
                  <p>Approved Amount</p>
                  <strong>
                    {money(evidence.approved_amount)}
                  </strong>
                </article>

                <article>
                  <p>Detected Indicators</p>
                  <strong>
                    {evidence.indicator_count}
                  </strong>
                </article>
              </section>

              <h3>Detected Fraud Indicators</h3>

              {evidence.indicators.length === 0 ? (
                <p>
                  No fraud indicators recorded for this claim.
                </p>
              ) : (
                <div style={{ overflowX: "auto" }}>
                  <table
                    style={{
                      width: "100%",
                      borderCollapse: "collapse"
                    }}
                  >
                    <thead>
                      <tr>
                        {[
                          "Indicator Type",
                          "Description",
                          "Detected At"
                        ].map(heading => (
                          <th
                            key={heading}
                            style={{
                              ...cellStyle,
                              textAlign: "left"
                            }}
                          >
                            {heading}
                          </th>
                        ))}
                      </tr>
                    </thead>

                    <tbody>
                      {evidence.indicators.map(item => (
                        <tr key={item.indicator_id}>
                          <td style={cellStyle}>
                            <strong>
                              {item.indicator_type.replace(
                                /_/g,
                                " "
                              )}
                            </strong>
                          </td>
                          <td style={cellStyle}>
                            {item.description}
                          </td>
                          <td style={cellStyle}>
                            {item.detected_at &&
                            !Number.isNaN(Date.parse(item.detected_at))
                              ? new Date(item.detected_at).toLocaleString("en-IN")
                              : "Not recorded"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              <p>
                These indicators identify suspicious activity.
                They do not establish confirmed fraud.
              </p>
            </>
          )}
        </section>
      )}

      {networkClaimId && (
        <section className="panel">
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              gap: 16
            }}
          >
            <div>
              <h2>Suspicious Relationship Network</h2>
              <p>Claim: {networkClaimId}</p>
            </div>

            <button onClick={closeNetwork}>
              Close Network
            </button>
          </div>

          {networkLoading && (
            <p>Loading relationship network...</p>
          )}

          {networkError && (
            <p className="error">{networkError}</p>
          )}

          {network && (
            <>
              <section className="cards">
                <article>
                  <p>Network Nodes</p>
                  <strong>{network.node_count}</strong>
                </article>
                <article>
                  <p>Connections</p>
                  <strong>{network.link_count}</strong>
                </article>
                <article>
                  <p>Stored Relationships</p>
                  <strong>
                    {network.stored_relationship_count}
                  </strong>
                </article>
                <article>
                  <p>Claim Risk Score</p>
                  <strong>{network.risk_score}</strong>
                </article>
              </section>

              <NetworkGraph
                key={network.claim_id}
                network={network}
              />

              <p>
                This graph shows recorded claim relationships.
                Connections alone do not prove fraud.
              </p>
            </>
          )}
        </section>
      )}

      <section className="panel">
        <h2>Investigation Management</h2>
        <p>
          Track suspicious claims assigned to fraud analysts.
        </p>

        <div style={{ overflowX: "auto" }}>
          <table
            style={{
              width: "100%",
              borderCollapse: "collapse"
            }}
          >
            <thead>
              <tr>
                {[
                  "Investigation ID",
                  "Claim ID",
                  "Priority",
                  "Assigned Analyst",
                  "Status",
                  "Outcome",
                  "Action"
                ].map(heading => (
                  <th
                    key={heading}
                    style={{
                      ...cellStyle,
                      textAlign: "left"
                    }}
                  >
                    {heading}
                  </th>
                ))}
              </tr>
            </thead>

            <tbody>
              {investigations.map(item => (
                <tr key={item.investigation_id}>
                  <td style={cellStyle}>
                    {item.investigation_id}
                  </td>
                  <td style={cellStyle}>
                    {item.claim_id}
                  </td>
                  <td style={cellStyle}>
                    <strong
                      style={{
                        color: riskColor(item.priority)
                      }}
                    >
                      {item.priority}
                    </strong>
                  </td>
                  <td style={cellStyle}>
                    {item.assigned_analyst ?? "Unassigned"}
                  </td>
                  <td style={cellStyle}>
                    {item.status}
                  </td>
                  <td style={cellStyle}>
                    {item.outcome ?? "Pending"}
                  </td>
                  <td style={cellStyle}>
                    {item.status === "NEW" && (
                      <button
                        disabled={updatingId !== null}
                        onClick={() =>
                          updateInvestigation(item)
                        }
                      >
                        {updatingId === item.investigation_id
                          ? "Updating..."
                          : "Start Investigation"}
                      </button>
                    )}

                    {item.status === "IN_PROGRESS" && (
                      <button
                        disabled={updatingId !== null}
                        onClick={() =>
                          updateInvestigation(item)
                        }
                      >
                        {updatingId === item.investigation_id
                          ? "Updating..."
                          : "Close Investigation"}
                      </button>
                    )}

                    {item.status === "CLOSED" && (
                      <span style={{ color: "#16a34a" }}>
                        Completed
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {!loading && investigations.length === 0 && (
          <p>No investigations created yet.</p>
        )}
      </section>


      {error && (
        <p className="error">{error}</p>
      )}

      {/* Automated Fraud Detection and Network Analysis */}
      <ClaimantManagement onChanged={loadData} />
      <FraudIntelligence />

      <footer>
        Insurance Fraud Detection | Synthetic Data Only
      </footer>
    </main>
  );
}
