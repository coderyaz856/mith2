"""
Animated graph builder that automatically creates an animation replay
showing the progression of agent conversations.
"""
import json
from typing import Dict, List, Any


def build_animated_graph_page(trace_data: Dict[str, Any]) -> str:
    """
    Build an HTML page with automatic animation of the agent conversation flow.
    Shows agents appearing one by one and messages flowing between them.
    """
    # Extract messages from turns structure
    messages = []
    turns = trace_data.get('turns', [])
    for turn in turns:
        turn_messages = turn.get('messages', [])
        messages.extend(turn_messages)
    
    run_id = trace_data.get('run_id', 'unknown')
    topic = trace_data.get('topic', 'Research Topic')
    
    # Extract agent sequence and debate info
    agent_sequence = []
    debate_exchanges = []
    
    for msg in messages:
        role = msg.get('role', '')
        content = msg.get('content', '')
        
        if '[DEBATE' in content:
            # Parse debate info
            import re
            match = re.search(r'\[DEBATE ([^|]+)\|([^|]+)\|', content)
            if match:
                transition = match.group(1).strip()
                speaker = match.group(2).strip()
                debate_exchanges.append({
                    'transition': transition,
                    'speaker': speaker,
                    'role': role
                })
        else:
            # Regular agent message
            if role and role not in agent_sequence:
                agent_sequence.append(role)
    
    # Convert to JSON for JavaScript
    agents_json = json.dumps(agent_sequence)
    debates_json = json.dumps(debate_exchanges)
    
    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Animated Agent Flow - {run_id[:8]}</title>
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
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0 0 10px 0;
            font-size: 2em;
        }}
        .topic {{
            font-size: 1.1em;
            opacity: 0.9;
            margin-top: 15px;
        }}
        .content {{
            padding: 30px;
        }}
        .controls {{
            display: flex;
            gap: 15px;
            align-items: center;
            justify-content: center;
            margin-bottom: 30px;
            padding: 20px;
            background: #f8fafc;
            border-radius: 8px;
        }}
        .btn {{
            padding: 12px 24px;
            border: none;
            border-radius: 6px;
            font-size: 1em;
            cursor: pointer;
            transition: all 0.3s;
            display: flex;
            align-items: center;
            gap: 8px;
            font-weight: 600;
        }}
        .btn:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }}
        .btn-play {{
            background: #10b981;
            color: white;
        }}
        .btn-pause {{
            background: #f59e0b;
            color: white;
        }}
        .btn-restart {{
            background: #3b82f6;
            color: white;
        }}
        .btn-speed {{
            background: #8b5cf6;
            color: white;
        }}
        .progress-container {{
            margin: 20px 0;
            padding: 20px;
            background: #f1f5f9;
            border-radius: 8px;
        }}
        .progress-bar {{
            width: 100%;
            height: 8px;
            background: #e2e8f0;
            border-radius: 4px;
            overflow: hidden;
        }}
        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            width: 0%;
            transition: width 0.3s;
        }}
        .progress-text {{
            margin-top: 10px;
            text-align: center;
            color: #64748b;
            font-size: 0.9em;
        }}
        .graph-container {{
            background: #f8fafc;
            padding: 30px;
            border-radius: 8px;
            min-height: 500px;
            position: relative;
        }}
        .message-overlay {{
            position: absolute;
            top: 20px;
            right: 20px;
            background: rgba(255, 255, 255, 0.95);
            padding: 15px 20px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            max-width: 300px;
            display: none;
            animation: slideIn 0.3s;
        }}
        .message-overlay.active {{
            display: block;
        }}
        @keyframes slideIn {{
            from {{
                transform: translateX(100%);
                opacity: 0;
            }}
            to {{
                transform: translateX(0);
                opacity: 1;
            }}
        }}
        .message-title {{
            font-weight: bold;
            color: #1e293b;
            margin-bottom: 8px;
        }}
        .message-content {{
            color: #64748b;
            font-size: 0.9em;
        }}
        .legend {{
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
            margin-top: 20px;
            padding: 20px;
            background: #f1f5f9;
            border-radius: 8px;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .legend-color {{
            width: 24px;
            height: 24px;
            border-radius: 4px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎬 Animated Agent Conversation Flow</h1>
            <div class="topic">{topic}</div>
        </div>
        
        <div class="content">
            <div class="controls">
                <button id="btn-play" class="btn btn-play" onclick="playAnimation()">
                    <span>▶</span> Play
                </button>
                <button id="btn-pause" class="btn btn-pause" onclick="pauseAnimation()" style="display: none;">
                    <span>⏸</span> Pause
                </button>
                <button id="btn-restart" class="btn btn-restart" onclick="restartAnimation()">
                    <span>↻</span> Restart
                </button>
                <button id="btn-speed" class="btn btn-speed" onclick="cycleSpeed()">
                    <span>⚡</span> Speed: <span id="speed-text">1x</span>
                </button>
            </div>
            
            <div class="progress-container">
                <div class="progress-bar">
                    <div id="progress-fill" class="progress-fill"></div>
                </div>
                <div class="progress-text" id="progress-text">Ready to play</div>
            </div>
            
            <div class="graph-container">
                <div id="message-overlay" class="message-overlay">
                    <div class="message-title" id="message-title">Agent Message</div>
                    <div class="message-content" id="message-content">...</div>
                </div>
                <pre class="mermaid" id="mermaid-graph">
                    graph LR
                    Start[Starting Animation...] 
                </pre>
            </div>
            
            <div class="legend">
                <div class="legend-item">
                    <div class="legend-color" style="background: #3b82f6;"></div>
                    <span><strong>Reader Agent</strong> - Initial analysis</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #ef4444;"></div>
                    <span><strong>Critic Agent</strong> - Critical evaluation</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #10b981;"></div>
                    <span><strong>Synthesizer Agent</strong> - Integration & synthesis</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #f59e0b;"></div>
                    <span><strong>Verifier Agent</strong> - Validation & verification</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #8b5cf6;"></div>
                    <span><strong>FollowUp Agent</strong> - Final refinement</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #64748b;"></div>
                    <span style="border-bottom: 2px dotted #64748b; padding-bottom: 2px;"><strong>Debate Loop</strong> - Clarification exchange</span>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        mermaid.initialize({{ 
            startOnLoad: true,
            theme: 'default',
            flowchart: {{
                curve: 'basis',
                padding: 20
            }}
        }});
        
        // Animation data
        const agentSequence = {agents_json};
        const debateExchanges = {debates_json};
        const totalSteps = agentSequence.length + debateExchanges.length;
        
        // Animation state
        let currentStep = 0;
        let isPlaying = false;
        let animationInterval = null;
        let speeds = [0.5, 1, 2, 3];
        let currentSpeedIndex = 1;
        let stepDelay = 2000; // milliseconds
        
        // Agent colors
        const colors = {{
            'reader': '#3b82f6',
            'critic': '#ef4444',
            'synthesizer': '#10b981',
            'verifier': '#f59e0b',
            'followup': '#8b5cf6'
        }};
        
        function updateGraph(step) {{
            const lines = ['graph LR'];
            const visibleAgents = agentSequence.slice(0, Math.min(step + 1, agentSequence.length));
            const visibleDebates = step > agentSequence.length ? 
                debateExchanges.slice(0, step - agentSequence.length) : [];
            
            // Add visible agents
            for (let i = 0; i < visibleAgents.length; i++) {{
                const agent = visibleAgents[i];
                const agentKey = agent.toLowerCase().replace(' ', '');
                const color = colors[agentKey] || '#64748b';
                
                lines.push(`    ${{agentKey}}["${{agent}}"]`);
                lines.push(`    style ${{agentKey}} fill:${{color}},stroke:#333,stroke-width:2px,color:#fff`);
                
                if (i > 0) {{
                    const prevAgent = visibleAgents[i-1].toLowerCase().replace(' ', '');
                    lines.push(`    ${{prevAgent}} --> ${{agentKey}}`);
                }}
            }}
            
            // Add visible debates
            visibleDebates.forEach((debate, idx) => {{
                const parts = debate.transition.split('->').map(s => s.trim());
                if (parts.length === 2) {{
                    const keyA = parts[0].toLowerCase();
                    const keyB = parts[1].toLowerCase();
                    lines.push(`    ${{keyA}} -.->|"debate ${{idx+1}}"| ${{keyB}}`);
                }}
            }});
            
            const mermaidCode = lines.join('\\n');
            const container = document.getElementById('mermaid-graph');
            container.textContent = mermaidCode;
            container.removeAttribute('data-processed');
            mermaid.init(undefined, container);
            
            // Update progress
            const progress = ((step + 1) / totalSteps) * 100;
            document.getElementById('progress-fill').style.width = progress + '%';
            document.getElementById('progress-text').textContent = 
                `Step ${{step + 1}} of ${{totalSteps}}: ${{getCurrentStepName(step)}}`;
            
            // Show message overlay
            showMessage(step);
        }}
        
        function getCurrentStepName(step) {{
            if (step < agentSequence.length) {{
                return agentSequence[step] + ' enters';
            }} else {{
                const debateIdx = step - agentSequence.length;
                if (debateIdx < debateExchanges.length) {{
                    return 'Debate: ' + debateExchanges[debateIdx].speaker;
                }}
            }}
            return 'Complete';
        }}
        
        function showMessage(step) {{
            const overlay = document.getElementById('message-overlay');
            const title = document.getElementById('message-title');
            const content = document.getElementById('message-content');
            
            if (step < agentSequence.length) {{
                title.textContent = agentSequence[step].toUpperCase() + ' Agent';
                content.textContent = `Processing and analyzing information...`;
                overlay.classList.add('active');
                setTimeout(() => overlay.classList.remove('active'), 1500);
            }} else {{
                const debateIdx = step - agentSequence.length;
                if (debateIdx < debateExchanges.length) {{
                    const debate = debateExchanges[debateIdx];
                    title.textContent = debate.speaker;
                    content.textContent = `Debating between ${{debate.transition}}`;
                    overlay.classList.add('active');
                    setTimeout(() => overlay.classList.remove('active'), 1500);
                }}
            }}
        }}
        
        function playAnimation() {{
            if (isPlaying) return;
            
            isPlaying = true;
            document.getElementById('btn-play').style.display = 'none';
            document.getElementById('btn-pause').style.display = 'flex';
            
            animationInterval = setInterval(() => {{
                if (currentStep < totalSteps) {{
                    updateGraph(currentStep);
                    currentStep++;
                }} else {{
                    pauseAnimation();
                }}
            }}, stepDelay / speeds[currentSpeedIndex]);
        }}
        
        function pauseAnimation() {{
            isPlaying = false;
            clearInterval(animationInterval);
            document.getElementById('btn-play').style.display = 'flex';
            document.getElementById('btn-pause').style.display = 'none';
        }}
        
        function restartAnimation() {{
            pauseAnimation();
            currentStep = 0;
            updateGraph(0);
            document.getElementById('progress-text').textContent = 'Ready to play';
        }}
        
        function cycleSpeed() {{
            currentSpeedIndex = (currentSpeedIndex + 1) % speeds.length;
            document.getElementById('speed-text').textContent = speeds[currentSpeedIndex] + 'x';
            
            if (isPlaying) {{
                clearInterval(animationInterval);
                playAnimation();
            }}
        }}
        
        // Initialize
        updateGraph(0);
    </script>
</body>
</html>
    """
    return html
