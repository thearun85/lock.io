// Configuration
const NODES = [
    { id: 1, url: 'http://localhost:5000', name: 'NODE 1' },
    { id: 2, url: 'http://localhost:5001', name: 'NODE 2' },
    { id: 3, url: 'http://localhost:5002', name: 'NODE 3' }
];

// State
let isConnected = false;

// DOM Elements
const statusIndicator = document.getElementById('status-indicator');
const statusText = document.getElementById('status-text');
const nodesContainer = document.getElementById('nodes-container');

// Initialize
function init() {
    console.log('Dashboard initialized');
    connect();
}

// Simulate connection
function connect() {
    setTimeout(() => {
        isConnected = true;
        updateConnectionStatus();
        startPolling();
    }, 1000);
}

// Update connection status indicator
function updateConnectionStatus() {
    if (isConnected) {
        statusIndicator.style.color = '#4caf50';
        statusText.textContent = 'Connected';
    } else {
        statusIndicator.style.color = '#f44336';
        statusText.textContent = 'Disconnected';
    }
}

// Fetch cluster status from all nodes
async function fetchClusterStatus() {
    const promises = NODES.map(async (node) => {
        try {
            const response = await fetch(`${node.url}/admin/cluster`);
            const data = await response.json();
            return {
                ...node,
                status: 'healthy',
                data: data
            };
        } catch (error) {
            console.error(`Failed to fetch from ${node.name}:`, error);
            return {
                ...node,
                status: 'dead',
                data: null
            };
        }
    });
    
    return await Promise.all(promises);
}

// Update node cards in UI
function updateNodeCards(nodesData) {
    // Clear existing cards
    nodesContainer.innerHTML = '';
    
    // Create card for each node
    nodesData.forEach(node => {
        const card = document.createElement('div');
        
        // Determine node role and styling
        let role = 'UNKNOWN';
        let cardClass = 'node-card';
        let term = '-';
        let uptime = '-';
        
        if (node.status === 'dead') {
            cardClass += ' dead';
            role = 'DEAD';
        } else if (node.data) {
            role = node.data.is_leader ? 'LEADER' : 'FOLLOWER';
            cardClass += node.data.is_leader ? ' leader' : ' follower';
            term = node.data.raft_term || node.data.term || '-';
            // You can calculate uptime if available in your API
        }
        
        card.className = cardClass;
        card.innerHTML = `
            <div class="node-header">
                <span class="node-name">${node.name}</span>
                <span class="node-role">${role}</span>
            </div>
            <div class="node-info">
                <div class="node-info-item">
                    <span class="node-info-label">Health:</span>
                    <span>${node.status === 'healthy' ? 'Healthy' : 'Dead'}</span>
                </div>
                <div class="node-info-item">
                    <span class="node-info-label">Term:</span>
                    <span>${term}</span>
                </div>
                <div class="node-info-item">
                    <span class="node-info-label">Ready:</span>
                    <span>${node.data?.is_ready ? 'Yes' : 'No'}</span>
                </div>
            </div>
        `;
        
        nodesContainer.appendChild(card);
    });
}

// Poll cluster status every 2 seconds
async function pollClusterStatus() {
    const nodesData = await fetchClusterStatus();
    updateNodeCards(nodesData);
    updateMetrics(nodesData);
    detectEvents(nodesData);
    console.log('Cluster status updated:', nodesData);
}

// Start polling
function startPolling() {
    console.log('Starting cluster polling...');
    
    // Initial fetch
    pollClusterStatus();
    
    // Poll every 2 seconds
    setInterval(pollClusterStatus, 2000);
    
    // Generate random events every 3-8 seconds for demo purposes
}

// Start on page load
window.addEventListener('DOMContentLoaded', init);

// Update metrics display
function updateMetrics(nodesData) {
    // Get data from the leader node
    const leaderNode = nodesData.find(node => node.data?.is_leader);
    
    if (!leaderNode || !leaderNode.data) {
        console.log('No leader found, skipping metrics update');
        return;
    }
    
    const data = leaderNode.data;
    
    // Update each metric
    document.getElementById('metric-sessions').textContent = data.total_sessions || 0;
    document.getElementById('metric-locks').textContent = data.total_locks || 0;
    document.getElementById('metric-fence').textContent = data.fence_counter || 0;
    
    // Calculate ops/sec (you'll need to track this over time)
    // For now just show 0
    document.getElementById('metric-ops').textContent = '0';
    
    // Uptime calculation (if you have created_at or similar)
    document.getElementById('metric-uptime').textContent = '-';
}

// Previous state tracking for detecting changes
let previousState = {
    leader: null,
    term: null,
    sessions: 0,
    locks: 0,
    fenceCounter: 0
};

// Add event to the stream
function addEvent(type, message) {
    const eventsContainer = document.getElementById('events-container');
    
    // Create event element
    const event = document.createElement('div');
    event.className = `event ${type}`;
    
    // Get current time
    const now = new Date();
    const timeStr = now.toLocaleTimeString('en-US', { 
        hour12: false, 
        hour: '2-digit', 
        minute: '2-digit', 
        second: '2-digit' 
    });
    
    // Set content
    event.innerHTML = `
        <span class="event-time">${timeStr}</span>
        <span class="event-message">${message}</span>
    `;
    
    // Add to top of container
    eventsContainer.insertBefore(event, eventsContainer.firstChild);
    
    // Keep only last 50 events
    while (eventsContainer.children.length > 50) {
        eventsContainer.removeChild(eventsContainer.lastChild);
    }
}

// Detect and emit events based on state changes
function detectEvents(nodesData) {
    const leaderNode = nodesData.find(node => node.data?.is_leader);
    
    if (!leaderNode || !leaderNode.data) return;
        
        // DEBUG: Log the actual data
        console.log('Leader data:', leaderNode.data);
        console.log('Previous state:', previousState);
    
    const data = leaderNode.data;
    const currentLeader = leaderNode.id;
    const currentTerm = data.raft_term || data.term;
    const currentSessions = data.total_sessions || 0;
    const currentLocks = data.total_locks || 0;
    const currentFence = data.fence_counter || 0;
    
    // Detect leader change
    if (previousState.leader !== null && previousState.leader !== currentLeader) {
        addEvent('election', `Leader elected (${leaderNode.name})`);
    }
    
    // Detect term change
    if (previousState.term !== null && previousState.term !== currentTerm) {
        addEvent('election', `Term changed: ${previousState.term} → ${currentTerm}`);
    }
    
    // Detect session changes
    if (previousState.sessions !== null) {
        if (currentSessions > previousState.sessions) {
            const diff = currentSessions - previousState.sessions;
            addEvent('session', `${diff} session${diff > 1 ? 's' : ''} created`);
        } else if (currentSessions < previousState.sessions) {
            const diff = previousState.sessions - currentSessions;
            addEvent('session', `${diff} session${diff > 1 ? 's' : ''} expired/deleted`);
        }
    }
    
    // Detect lock changes
    if (previousState.locks !== null) {
        if (currentLocks > previousState.locks) {
            const diff = currentLocks - previousState.locks;
            addEvent('lock', `${diff} lock${diff > 1 ? 's' : ''} acquired`);
        } else if (currentLocks < previousState.locks) {
            const diff = previousState.locks - currentLocks;
            addEvent('lock', `${diff} lock${diff > 1 ? 's' : ''} released`);
        }
    }
    
    // Detect fence token increase (indicates lock acquisition)
    if (previousState.fenceCounter !== null && currentFence > previousState.fenceCounter) {
        addEvent('lock', `Fence token: ${currentFence}`);
    }
    
    // Update previous state
    previousState.leader = currentLeader;
    previousState.term = currentTerm;
    previousState.sessions = currentSessions;
    previousState.locks = currentLocks;
    previousState.fenceCounter = currentFence;
}

// Generate random simulated events
function generateRandomEvent() {
    const eventTypes = [
        { type: 'session', messages: [
            'Session created (worker-{id})',
            'Session expired (worker-{id})'
        ]},
        { type: 'lock', messages: [
            'Lock acquired (resource-{id}) #{fence}',
            'Lock released (resource-{id})'
        ]},
        { type: 'keepalive', messages: [
            'Keepalive (worker-{id})'
        ]}
    ];
    
    const randomType = eventTypes[Math.floor(Math.random() * eventTypes.length)];
    const randomMessage = randomType.messages[Math.floor(Math.random() * randomType.messages.length)];
    
    // Replace placeholders
    const id = Math.floor(Math.random() * 10) + 1;
    const fence = Math.floor(Math.random() * 200) + 1;
    const message = randomMessage.replace('{id}', id).replace('{fence}', fence);
    
    addEvent(randomType.type, message);
}
