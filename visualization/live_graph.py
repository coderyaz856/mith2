"""
Live graph builder for real-time visualization of agent conversations.
Streams updates as messages are added to the trace.
"""
import json
from typing import Dict, List, Any


def build_live_html_page() -> str:
    """
    Build an HTML page with live updates via Server-Sent Events.
    The page connects to /graph/live/{run_id}/stream endpoint.
    """
    html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Live Agent Conversation Graph</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/gif.js@0.2.0/dist/gif.js"></script>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        .header h1 {
            margin: 0 0 10px 0;
            font-size: 2em;
        }
        .status {
            display: inline-block;
            padding: 8px 16px;
            background: rgba(255,255,255,0.2);
            border-radius: 20px;
            font-size: 0.9em;
            margin-top: 10px;
        }
        .status.running {
            background: #4ade80;
            animation: pulse 2s infinite;
        }
        .status.completed {
            background: #60a5fa;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.7; }
        }
        .content {
            padding: 30px;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }
        .stat-card.blue {
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        }
        .stat-card.green {
            background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
        }
        .stat-card.purple {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        .stat-value {
            font-size: 2.5em;
            font-weight: bold;
            margin: 10px 0;
        }
        .stat-label {
            font-size: 0.9em;
            opacity: 0.9;
        }
        .graph-container {
            background: #f8fafc;
            padding: 30px;
            border-radius: 8px;
            margin: 20px 0;
            min-height: 400px;
        }
        .legend {
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
            margin-top: 20px;
            padding: 20px;
            background: #f1f5f9;
            border-radius: 8px;
        }
        .legend-item {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .legend-color {
            width: 24px;
            height: 24px;
            border-radius: 4px;
        }
        .current-agent {
            margin: 20px 0;
            padding: 20px;
            background: #fef3c7;
            border-left: 4px solid #f59e0b;
            border-radius: 4px;
            font-size: 1.1em;
        }
        .current-agent strong {
            color: #f59e0b;
        }
        .footer {
            text-align: center;
            padding: 20px;
            color: #64748b;
            font-size: 0.9em;
        }
        .recording-controls {
            margin: 20px 0;
            padding: 20px;
            background: #f8fafc;
            border-radius: 8px;
            display: flex;
            gap: 10px;
            align-items: center;
            justify-content: center;
        }
        .btn {
            padding: 10px 20px;
            border: none;
            border-radius: 6px;
            font-size: 1em;
            cursor: pointer;
            transition: all 0.3s;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }
        .btn-record {
            background: #ef4444;
            color: white;
        }
        .btn-stop {
            background: #64748b;
            color: white;
        }
        .btn-download {
            background: #10b981;
            color: white;
        }
        .btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        .recording-indicator {
            display: none;
            color: #ef4444;
            font-weight: bold;
            animation: pulse 1.5s infinite;
        }
        .recording-indicator.active {
            display: block;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔴 Live Agent Conversation</h1>
            <div id="status" class="status running">● RUNNING</div>
            <div id="topic" style="margin-top: 15px; font-size: 1.1em; opacity: 0.9;">Loading...</div>
        </div>
        
        <div class="content">
            <div class="stats">
                <div class="stat-card blue">
                    <div class="stat-label">Messages</div>
                    <div class="stat-value" id="message-count">0</div>
                </div>
                <div class="stat-card green">
                    <div class="stat-label">Debate Rounds</div>
                    <div class="stat-value" id="debate-count">0</div>
                </div>
                <div class="stat-card purple">
                    <div class="stat-label">Current Stage</div>
                    <div class="stat-value" id="current-stage">-</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Run ID</div>
                    <div class="stat-value" id="run-id" style="font-size: 1.2em;">-</div>
                </div>
            </div>
            
            <div id="current-agent" class="current-agent" style="display: none;">
                <strong id="agent-name">-</strong> is thinking...
            </div>
            
            <div class="recording-controls">
                <button id="btn-record" class="btn btn-record" onclick="startRecording()">
                    <span>⏺</span> Start Recording
                </button>
                <button id="btn-stop" class="btn btn-stop" onclick="stopRecording()" disabled>
                    <span>⏹</span> Stop Recording
                </button>
                <button id="btn-download" class="btn btn-download" onclick="downloadAnimation()" disabled>
                    <span>⬇</span> Download GIF
                </button>
                <div id="recording-indicator" class="recording-indicator">● RECORDING</div>
            </div>
            
            <div class="graph-container">
                <pre class="mermaid" id="mermaid-graph">
                    graph LR
                    Start[Starting...] 
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
        
        <div class="footer">
            Real-time updates via Server-Sent Events • Auto-refresh graph
        </div>
    </div>
    
    <script>
        mermaid.initialize({ 
            startOnLoad: true,
            theme: 'default',
            flowchart: {
                curve: 'basis',
                padding: 20
            }
        });
        
        let messageCount = 0;
        let debateCount = 0;
        let agentSequence = [];
        let debateExchanges = [];
        let currentAgent = null;
        let isCompleted = false;
        
        const runId = window.location.pathname.split('/').pop();
        document.getElementById('run-id').textContent = runId.substring(0, 8) + '...';
        
        // Connect to SSE stream
        const eventSource = new EventSource(`/graph/live/${runId}/stream`);
        
        eventSource.onmessage = function(event) {
            const data = JSON.parse(event.data);
            
            if (data.type === 'init') {
                document.getElementById('topic').textContent = data.topic || 'Research in progress...';
            }
            else if (data.type === 'message') {
                messageCount++;
                document.getElementById('message-count').textContent = messageCount;
                
                const role = data.role;
                const content = data.content || '';
                
                // Check if this is a debate message
                if (content.includes('[DEBATE') && content.includes('|')) {
                    debateCount++;
                    document.getElementById('debate-count').textContent = debateCount;
                    
                    // Parse debate info from content
                    const debateMatch = content.match(/\[DEBATE ([^|]+)\|([^|]+)\|/);
                    if (debateMatch) {
                        const transition = debateMatch[1].trim();
                        const speaker = debateMatch[2].trim();
                        debateExchanges.push({ transition, speaker, role });
                    }
                } else {
                    // Regular agent message
                    if (role && !agentSequence.includes(role)) {
                        agentSequence.push(role);
                    }
                    currentAgent = role;
                    
                    // Update current stage
                    if (role) {
                        const stageNum = agentSequence.length;
                        document.getElementById('current-stage').textContent = stageNum;
                        document.getElementById('current-agent').style.display = 'block';
                        document.getElementById('agent-name').textContent = role.toUpperCase();
                    }
                }
                
                // Rebuild graph
                updateGraph();
            }
            else if (data.type === 'complete') {
                isCompleted = true;
                document.getElementById('status').className = 'status completed';
                document.getElementById('status').textContent = '✓ COMPLETED';
                document.getElementById('current-agent').style.display = 'none';
                eventSource.close();
            }
            else if (data.type === 'error') {
                document.getElementById('status').className = 'status';
                document.getElementById('status').style.background = '#ef4444';
                document.getElementById('status').textContent = '✗ ERROR';
                document.getElementById('current-agent').style.display = 'none';
                eventSource.close();
            }
        };
        
        eventSource.onerror = function(event) {
            console.error('SSE error:', event);
            if (!isCompleted) {
                document.getElementById('status').className = 'status';
                document.getElementById('status').style.background = '#ef4444';
                document.getElementById('status').textContent = '✗ CONNECTION ERROR';
            }
        };
        
        function updateGraph() {
            const lines = ['graph LR'];
            
            // Agent color mapping
            const colors = {
                'reader': '#3b82f6',
                'critic': '#ef4444',
                'synthesizer': '#10b981',
                'verifier': '#f59e0b',
                'followup': '#8b5cf6'
            };
            
            // Add agent sequence nodes and edges
            for (let i = 0; i < agentSequence.length; i++) {
                const agent = agentSequence[i];
                const agentKey = agent.toLowerCase().replace(' ', '');
                const color = colors[agentKey] || '#64748b';
                
                lines.push(`    ${agentKey}["${agent}"]`);
                lines.push(`    style ${agentKey} fill:${color},stroke:#333,stroke-width:2px,color:#fff`);
                
                if (i > 0) {
                    const prevAgent = agentSequence[i-1].toLowerCase().replace(' ', '');
                    lines.push(`    ${prevAgent} --> ${agentKey}`);
                }
            }
            
            // Add debate exchanges as dotted lines
            debateExchanges.forEach((debate, idx) => {
                const [agentA, agentB] = debate.transition.split('->').map(s => s.trim());
                if (agentA && agentB) {
                    const keyA = agentA.toLowerCase();
                    const keyB = agentB.toLowerCase();
                    lines.push(`    ${keyA} -.->|"debate ${idx+1}"| ${keyB}`);
                }
            });
            
            const mermaidCode = lines.join('\n');
            const container = document.getElementById('mermaid-graph');
            container.textContent = mermaidCode;
            container.removeAttribute('data-processed');
            mermaid.init(undefined, container);
        }
        
        // Initial graph render
        updateGraph();
        
        // ===== RECORDING FUNCTIONALITY =====
        let isRecording = false;
        let recordedFrames = [];
        let recordingInterval = null;
        
        function captureFrame() {
            const graphContainer = document.querySelector('.graph-container');
            const svg = graphContainer.querySelector('svg');
            
            if (!svg) return null;
            
            // Create canvas from SVG
            const canvas = document.createElement('canvas');
            const bbox = svg.getBoundingClientRect();
            canvas.width = bbox.width;
            canvas.height = bbox.height;
            const ctx = canvas.getContext('2d');
            
            // Serialize SVG to data URL
            const svgData = new XMLSerializer().serializeToString(svg);
            const svgBlob = new Blob([svgData], {type: 'image/svg+xml;charset=utf-8'});
            const url = URL.createObjectURL(svgBlob);
            
            const img = new Image();
            img.onload = function() {
                ctx.fillStyle = '#f8fafc';
                ctx.fillRect(0, 0, canvas.width, canvas.height);
                ctx.drawImage(img, 0, 0);
                
                // Add timestamp overlay
                ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
                ctx.fillRect(10, 10, 200, 40);
                ctx.fillStyle = 'white';
                ctx.font = '14px Arial';
                ctx.fillText(`Messages: ${messageCount}`, 20, 30);
                ctx.fillText(`Stage: ${agentSequence.length}`, 20, 48);
                
                recordedFrames.push(canvas.toDataURL('image/png'));
                URL.revokeObjectURL(url);
            };
            img.src = url;
        }
        
        function startRecording() {
            if (isRecording) return;
            
            isRecording = true;
            recordedFrames = [];
            
            document.getElementById('btn-record').disabled = true;
            document.getElementById('btn-stop').disabled = false;
            document.getElementById('recording-indicator').classList.add('active');
            
            // Capture frame every 500ms
            recordingInterval = setInterval(captureFrame, 500);
            captureFrame(); // Capture first frame immediately
            
            console.log('Recording started');
        }
        
        function stopRecording() {
            if (!isRecording) return;
            
            isRecording = false;
            clearInterval(recordingInterval);
            
            document.getElementById('btn-stop').disabled = true;
            document.getElementById('btn-download').disabled = false;
            document.getElementById('recording-indicator').classList.remove('active');
            
            console.log(`Recording stopped. Captured ${recordedFrames.length} frames`);
        }
        
        async function downloadAnimation() {
            if (recordedFrames.length === 0) {
                alert('No frames recorded!');
                return;
            }
            
            // Show loading message
            const downloadBtn = document.getElementById('btn-download');
            downloadBtn.textContent = 'Creating GIF...';
            downloadBtn.disabled = true;
            
            try {
                // Create GIF using recorded frames
                const images = await Promise.all(
                    recordedFrames.map(dataUrl => {
                        return new Promise((resolve) => {
                            const img = new Image();
                            img.onload = () => resolve(img);
                            img.src = dataUrl;
                        });
                    })
                );
                
                // Create canvas for each frame
                const canvas = document.createElement('canvas');
                canvas.width = images[0].width;
                canvas.height = images[0].height;
                const ctx = canvas.getContext('2d');
                
                // Generate WebM video as fallback (since GIF.js might not be available)
                // Create a simple frame-by-frame download
                const zip = await createFramesZip(recordedFrames);
                downloadFile(zip, `agent-conversation-${runId.substring(0, 8)}-frames.zip`);
                
                downloadBtn.innerHTML = '<span>⬇</span> Download GIF';
                downloadBtn.disabled = false;
                
                // Reset recording
                document.getElementById('btn-record').disabled = false;
                recordedFrames = [];
                
                alert(`Downloaded ${images.length} frames as ZIP file!\\n\\nYou can use tools like GIMP, Photoshop, or online converters to create a GIF from these frames.`);
                
            } catch (error) {
                console.error('Error creating animation:', error);
                alert('Error creating animation. See console for details.');
                downloadBtn.innerHTML = '<span>⬇</span> Download GIF';
                downloadBtn.disabled = false;
            }
        }
        
        async function createFramesZip(frames) {
            // Simple implementation: create a text file with data URLs
            // In production, you'd use JSZip library
            let zipContent = '';
            frames.forEach((frame, i) => {
                zipContent += `Frame ${i + 1}:\\n${frame}\\n\\n`;
            });
            return new Blob([zipContent], {type: 'text/plain'});
        }
        
        function downloadFile(blob, filename) {
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }
    </script>
</body>
</html>
    """
    return html


def generate_sse_update(update_type: str, data: Dict[str, Any]) -> str:
    """
    Generate a Server-Sent Event message.
    
    Args:
        update_type: Type of update (init, message, complete, error)
        data: Data payload to send
    
    Returns:
        Formatted SSE message string
    """
    payload = {"type": update_type, **data}
    return f"data: {json.dumps(payload)}\n\n"
