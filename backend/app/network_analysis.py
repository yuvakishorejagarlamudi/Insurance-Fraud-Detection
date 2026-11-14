
import sqlite3
import json
from pathlib import Path
from collections import defaultdict, deque

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "insurance_fraud.db"


def analyze_network():
    if not DB_PATH.is_file():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    conn = sqlite3.connect(
        f"file:{DB_PATH.as_posix()}?mode=ro",
        uri=True
    )
    conn.row_factory = sqlite3.Row

    try:
        # Build the graph from claim and invoice relationships.
        graph = defaultdict(set)

        rows = conn.execute("""
            SELECT DISTINCT
                c.claim_id,
                c.claimant_id,
                i.provider_id
            FROM claims c
            JOIN invoices i ON i.claim_id = c.claim_id
        """).fetchall()

        for row in rows:
            claim = row["claim_id"]
            claimant = row["claimant_id"]
            provider = row["provider_id"]

            graph[claim].add(claimant)
            graph[claimant].add(claim)

            graph[claim].add(provider)
            graph[provider].add(claim)

        # Add explicit relationship edges.
        edges = conn.execute("""
            SELECT source_id, target_id
            FROM relationship_edges
        """).fetchall()

        for edge in edges:
            source = edge["source_id"]
            target = edge["target_id"]

            graph[source].add(target)
            graph[target].add(source)

        # Find connected components.
        visited = set()
        components = []

        for node in graph:
            if node in visited:
                continue

            queue = deque([node])
            visited.add(node)
            component = []

            while queue:
                current = queue.popleft()
                component.append(current)

                for neighbor in graph[current]:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append(neighbor)

            components.append(component)

        components.sort(key=len, reverse=True)

        # Shared addresses are leads, not automatic fraud.
        address_groups = conn.execute("""
            SELECT
                address_hash,
                COUNT(*) AS claimant_count
            FROM claimants
            GROUP BY address_hash
            HAVING COUNT(*) > 1
            ORDER BY claimant_count DESC
        """).fetchall()

        # Providers sharing bank accounts may warrant review.
        bank_groups = conn.execute("""
            SELECT
                bank_account_hash,
                COUNT(*) AS provider_count
            FROM providers
            GROUP BY bank_account_hash
            HAVING COUNT(*) > 1
            ORDER BY provider_count DESC
        """).fetchall()

        # Find providers associated with many different claimants.
        provider_patterns = conn.execute("""
            SELECT
                i.provider_id,
                COUNT(DISTINCT c.claimant_id) AS claimant_count,
                COUNT(DISTINCT c.claim_id) AS claim_count
            FROM invoices i
            JOIN claims c ON c.claim_id = i.claim_id
            GROUP BY i.provider_id
            HAVING COUNT(DISTINCT c.claimant_id) >= 10
            ORDER BY claimant_count DESC, i.provider_id
        """).fetchall()

        return {
            "nodes": len(graph),
            "explicit_edges": len(edges),
            "connected_components": len(components),
            "largest_component_size": (
                len(components[0]) if components else 0
            ),
            "shared_address_groups": [
                dict(row) for row in address_groups
            ],
            "shared_bank_groups": [
                dict(row) for row in bank_groups
            ],
            "high_volume_providers": [
                dict(row) for row in provider_patterns
            ],
        }

    finally:
        conn.close()


if __name__ == "__main__":
    result = analyze_network()

    print("\nSUSPICIOUS NETWORK ANALYSIS")
    print("=" * 55)

    print("Total graph nodes:", result["nodes"])
    print("Explicit relationship edges:", result["explicit_edges"])
    print("Connected components:", result["connected_components"])
    print("Largest component size:", result["largest_component_size"])

    print(
        "Shared address groups:",
        len(result["shared_address_groups"])
    )
    print(
        "Shared provider bank groups:",
        len(result["shared_bank_groups"])
    )
    print(
        "High-volume providers:",
        len(result["high_volume_providers"])
    )

    print("\nTOP PROVIDER PATTERNS")

    for provider in result["high_volume_providers"][:5]:
        print(
            provider["provider_id"],
            "| Claimants:", provider["claimant_count"],
            "| Claims:", provider["claim_count"]
        )

    print("\nSTEP 43: NETWORK ANALYSIS EXECUTED")
