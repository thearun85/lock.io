document.addEventListener("DOMContentLoaded", function() {

    const NODES = [
        { id: "node-1", url: "http://localhost:5000" },
        { id: "node-2", url: "http://localhost:5001" },
        { id: "node-3", url: "http://localhost:5002" },
    ];

    async function fetchNodeStatus(node) {
        try {
            const response = await fetch(`${node.url}/cluster/status`);
            if (!response.ok) throw new Error("Not OK");
            return await response.json();
        } catch (error) {
            return null;
        }
    }

    function updateNodeUI(nodeId, status) {
        const element = document.getElementById(nodeId);
        const stateEl = element.querySelector(".node-state");
        const termEl = element.querySelector(".node-term");

        // Remove all state classes
        element.classList.remove("leader", "follower", "candidate", "offline");

        if (status === null) {
            element.classList.add("offline");
            stateEl.textContent = "OFFLINE";
            termEl.textContent = "Term: -";
            return;
        }

        const state = status.state.toLowerCase();
        element.classList.add(state);
        stateEl.textContent = status.state;
        termEl.textContent = `Term: ${status.term}`;
    }

    function updateStats(statuses) {
        // Use first available node's stats
        const available = statuses.find(s => s !== null);
        if (available && available.stats) {
            document.getElementById("stats-sessions").textContent = 
                `Sessions: ${available.stats.total_session || 0}`;
            document.getElementById("stats-locks").textContent = 
                `Locks: ${available.stats.total_locks || 0}`;
            document.getElementById("stats-fence").textContent = 
                `Fence Token: ${available.stats.fence_counter || 0}`;
        }
    }

    async function pollCluster() {
        const statuses = await Promise.all(
            NODES.map(node => fetchNodeStatus(node))
        );

        NODES.forEach((node, index) => {
            updateNodeUI(node.id, statuses[index]);
        });

        updateStats(statuses);
    }

    // Poll every 500ms
    setInterval(pollCluster, 500);

    // Initial poll
    pollCluster();

});
