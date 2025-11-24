"""Build visual graphs of agent conversation flows from trace data."""
from __future__ import annotations

from typing import Any
import json


def build_mermaid_flowchart(trace_data: dict[str, Any]) -> str:
    """Generate a Mermaid flowchart from trace data.
    
    Shows the agent pipeline with debate loops and message counts.
    """
    lines = ["flowchart TD"]
    lines.append("    Start([Start: Topic]) --> Reader")
    
    # Extract roles and debate patterns
    if not trace_data.get("turns"):
        lines.append("    Reader --> End([No data])")
        return "\n".join(lines)
    
    turn = trace_data["turns"][0]  # Focus on first turn for visualization
    messages = turn.get("messages", [])
    
    # Track agent sequence and debate exchanges
    agent_sequence = []
    debate_exchanges = []
    
    i = 0
    while i < len(messages):
        msg = messages[i]
        role = msg.get("role", "")
        content = msg.get("content", "")
        
        # Check if this is a debate message
        if "[DEBATE" in content:
            # Extract debate info
            debate_marker = content.split("]")[0] + "]"
            if "->" in debate_marker and "|" in debate_marker:
                parts = debate_marker.split("|")
                agents_part = parts[0].replace("[DEBATE", "").strip()
                action_part = parts[1].strip() if len(parts) > 1 else ""
                
                # Collect the 3-message debate sequence
                if i + 2 < len(messages):
                    debate_exchanges.append({
                        "from_to": agents_part,
                        "messages": [messages[i], messages[i+1], messages[i+2]]
                    })
                    i += 3
                    continue
        
        # Regular agent message
        agent_sequence.append(role)
        i += 1
    
    # Build main flow
    prev_agent = "Reader"
    agent_nodes = {"reader": "Reader[Reader<br/>Extracts findings]"}
    
    for idx, role in enumerate(agent_sequence):
        if role == "reader":
            continue
        
        role_display = role.capitalize()
        node_id = role
        
        # Define node shapes and descriptions
        if role == "critic":
            agent_nodes[role] = f"{role_display}[Critic<br/>Challenges claims]"
        elif role == "synthesizer":
            agent_nodes[role] = f"{role_display}[Synthesizer<br/>Merges perspectives]"
        elif role == "verifier":
            agent_nodes[role] = f"{role_display}[Verifier<br/>Assesses quality]"
        elif role == "followup":
            agent_nodes[role] = f"{role_display}[FollowUp<br/>Proposes questions]"
        else:
            agent_nodes[role] = f"{role_display}[{role_display}]"
    
    # Add nodes
    for node_id, node_def in agent_nodes.items():
        lines.append(f"    {node_def}")
    
    # Add main flow edges
    flow_sequence = ["reader"] + [r for r in agent_sequence if r != "reader"]
    for i in range(len(flow_sequence) - 1):
        from_agent = flow_sequence[i].capitalize()
        to_agent = flow_sequence[i + 1].capitalize()
        lines.append(f"    {from_agent} --> {to_agent}")
    
    # Add debate subgraphs
    for idx, debate in enumerate(debate_exchanges):
        from_to = debate["from_to"]
        if "->" in from_to:
            agents = from_to.split("->")
            if len(agents) == 2:
                from_agent = agents[0].strip().capitalize()
                to_agent = agents[1].strip().capitalize()
                
                debate_id = f"D{idx}"
                lines.append(f"    {from_agent} -.->|debate| {debate_id}{{{{Debate}}}}")
                lines.append(f"    {debate_id} -.->|clarified| {to_agent}")
    
    # End node
    if flow_sequence:
        last_agent = flow_sequence[-1].capitalize()
        lines.append(f"    {last_agent} --> End([Complete])")
    
    # Style
    lines.append("    style Start fill:#e1f5e1")
    lines.append("    style End fill:#ffe1e1")
    lines.append("    style Reader fill:#cce5ff")
    lines.append("    style Critic fill:#ffcccc")
    lines.append("    style Synthesizer fill:#ccffcc")
    lines.append("    style Verifier fill:#ffecb3")
    lines.append("    style Followup fill:#e1bee7")
    
    return "\n".join(lines)


def build_html_page(trace_data: dict[str, Any]) -> str:
    """Generate a full HTML page with embedded Mermaid visualization."""
    mermaid_chart = build_mermaid_flowchart(trace_data)
    
    # Count messages and debates
    total_messages = 0
    debate_count = 0
    if trace_data.get("turns"):
        for turn in trace_data["turns"]:
            messages = turn.get("messages", [])
            total_messages += len(messages)
            for msg in messages:
                if "[DEBATE" in msg.get("content", ""):
                    debate_count += 1
    
    debate_rounds = debate_count // 3  # Each debate has 3 messages (ask, answer, synthesis)
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Agent Conversation Flow - {trace_data.get('run_id', 'Unknown')}</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            padding: 30px;
        }}
        h1 {{
            color: #333;
            margin-bottom: 10px;
            font-size: 28px;
        }}
        .metadata {{
            background: #f5f5f5;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 25px;
            display: flex;
            gap: 30px;
            flex-wrap: wrap;
        }}
        .metadata-item {{
            display: flex;
            flex-direction: column;
        }}
        .metadata-label {{
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 5px;
        }}
        .metadata-value {{
            font-size: 16px;
            color: #333;
            font-weight: 600;
        }}
        .chart-container {{
            background: #fafafa;
            padding: 30px;
            border-radius: 8px;
            margin-bottom: 20px;
            overflow-x: auto;
        }}
        .legend {{
            background: #f0f0f0;
            padding: 15px;
            border-radius: 8px;
            margin-top: 20px;
        }}
        .legend h3 {{
            margin-top: 0;
            color: #555;
            font-size: 16px;
        }}
        .legend-items {{
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .legend-color {{
            width: 20px;
            height: 20px;
            border-radius: 4px;
            border: 1px solid #ddd;
        }}
        .actions {{
            display: flex;
            gap: 15px;
            margin-top: 20px;
        }}
        .btn {{
            padding: 10px 20px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            text-decoration: none;
            display: inline-block;
            transition: all 0.3s;
        }}
        .btn-primary {{
            background: #667eea;
            color: white;
        }}
        .btn-primary:hover {{
            background: #5568d3;
        }}
        .btn-secondary {{
            background: #e0e0e0;
            color: #333;
        }}
        .btn-secondary:hover {{
            background: #d0d0d0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 Multi-Agent Conversation Flow</h1>
        
        <div class="metadata">
            <div class="metadata-item">
                <div class="metadata-label">Run ID</div>
                <div class="metadata-value">{trace_data.get('run_id', 'N/A')[:12]}...</div>
            </div>
            <div class="metadata-item">
                <div class="metadata-label">Topic</div>
                <div class="metadata-value">{trace_data.get('topic', 'N/A')[:50]}...</div>
            </div>
            <div class="metadata-item">
                <div class="metadata-label">Status</div>
                <div class="metadata-value">{trace_data.get('status', 'N/A').upper()}</div>
            </div>
            <div class="metadata-item">
                <div class="metadata-label">Total Messages</div>
                <div class="metadata-value">{total_messages}</div>
            </div>
            <div class="metadata-item">
                <div class="metadata-label">Debate Rounds</div>
                <div class="metadata-value">{debate_rounds}</div>
            </div>
            <div class="metadata-item">
                <div class="metadata-label">Turns</div>
                <div class="metadata-value">{len(trace_data.get('turns', []))}</div>
            </div>
        </div>
        
        <div class="chart-container">
            <div class="mermaid">
{mermaid_chart}
            </div>
        </div>
        
        <div class="legend">
            <h3>Legend</h3>
            <div class="legend-items">
                <div class="legend-item">
                    <div class="legend-color" style="background: #cce5ff;"></div>
                    <span>Reader - Extracts findings</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #ffcccc;"></div>
                    <span>Critic - Challenges claims</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #ccffcc;"></div>
                    <span>Synthesizer - Merges perspectives</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #ffecb3;"></div>
                    <span>Verifier - Assesses quality</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #e1bee7;"></div>
                    <span>FollowUp - Proposes questions</span>
                </div>
                <div class="legend-item">
                    <span>━━━ Main flow</span>
                </div>
                <div class="legend-item">
                    <span>┈┈┈ Debate clarification</span>
                </div>
            </div>
        </div>
        
        <div class="actions">
            <a href="/api/runs/{trace_data.get('run_id', '')}/trace" class="btn btn-primary">View Full Trace JSON</a>
            <a href="/api/runs/{trace_data.get('run_id', '')}/insight" class="btn btn-secondary">View Insight Report</a>
            <a href="/" class="btn btn-secondary">Back to Home</a>
        </div>
    </div>
    
    <script>
        mermaid.initialize({{ 
            startOnLoad: true,
            theme: 'default',
            flowchart: {{
                useMaxWidth: true,
                htmlLabels: true,
                curve: 'basis'
            }}
        }});
    </script>
</body>
</html>"""
    return html
