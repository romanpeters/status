const outputBox = document.getElementById('output-box');
let intervalId = null;

async function fetchStatus(args) {
    let url = `/api/status?`;
    if (args.monitor_name) url += `name=${encodeURIComponent(args.monitor_name)}&`;
    if (args.monitor) url += `type=${encodeURIComponent(args.monitor)}&`;
    if (args.up) url += `status=up&`;
    if (args.down) url += `status=down&`;

    try {
        const response = await fetch(url);
        const data = await response.json();
        formatStatus(data);
    } catch (error) {
        console.error('Error fetching status:', error);
        outputBox.textContent = 'Error fetching status.';
    }
}

function formatStatus(results) {
    outputBox.innerHTML = ''; // Clear previous output

    if (!results || results.length === 0) {
        outputBox.textContent = 'No monitors to display.';
        return;
    }

    // Group results by monitor_type
    const groups = results.reduce((acc, result) => {
        (acc[result.monitor_type] = acc[result.monitor_type] || []).push(result);
        return acc;
    }, {});

    for (const monitorType in groups) {
        const groupResults = groups[monitorType];

        const groupDiv = document.createElement('div');
        groupDiv.classList.add('terminal-group');

        groupResults.forEach(result => {
            const line = document.createElement('div');
            line.classList.add('line');

            const nameSpan = document.createElement('span');
            nameSpan.classList.add('name');
            const isUp = result.status === 'OK' || (typeof result.status === 'number' && result.status >= 200 && result.status < 300);
            nameSpan.innerHTML = `<span class="bold ${isUp ? '' : 'down'}">${result.name}</span> (${result.host_or_url})`;

            const statusSpan = document.createElement('span');
            statusSpan.classList.add('status');
            const statusLabel = isUp
                ? `[<span class="emoji">✅</span><span class="status-text">Up</span>]`
                : `[<span class="emoji">🔴</span><span class="status-text">Down</span>]`;
            
            statusSpan.innerHTML = `
                <span class="status-label">${statusLabel}</span>
                <span class="status-code">${result.status}</span>
                <span class="status-message">- ${result.message}</span>
            `;

            line.appendChild(nameSpan);
            line.appendChild(statusSpan);
            groupDiv.appendChild(line);
        });

        outputBox.appendChild(groupDiv);
    }
}

async function init() {
    try {
        const response = await fetch('/api/args');
        const args = await response.json();

        fetchStatus(args);

        if (args.follow) {
            const interval = args.interval ? args.interval * 1000 : 5000;
            intervalId = setInterval(() => fetchStatus(args), interval);
        }
    } catch (error) {
        console.error('Error fetching args:', error);
        outputBox.textContent = 'Error fetching initial arguments.';
    }
}

init();