document.addEventListener('DOMContentLoaded', () => {
    
    const path = window.location.pathname;

    if (path === '/') {
        loadDashboard();
        // Refresh every 30 seconds
        setInterval(loadDashboard, 30000);
    } else if (path === '/config') {
        loadConfigPage();
    } else if (path === '/history') {
        loadHistoryPage();
    }

});

async function loadDashboard() {
    try {
        const res = await fetch('/api/status');
        const data = await res.json();
        
        const overallContainer = document.getElementById('overall-status-container');
        const overallText = document.getElementById('overall-status-text');
        
        overallContainer.className = `glass-card overall-status bg-${data.overall_status}`;
        overallText.innerText = data.overall_status;
        overallText.className = `status-${data.overall_status}`;
        
        const grid = document.getElementById('checks-grid');
        grid.innerHTML = '';
        
        data.checks.forEach(check => {
            const card = document.createElement('div');
            card.className = `glass-card bg-${check.status}`;
            
            card.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1rem;">
                    <h3 style="margin: 0;">${check.name}</h3>
                    <span style="font-weight: bold;" class="status-${check.status}">${check.status}</span>
                </div>
                <p style="font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 0.5rem;">Host: ${check.host}</p>
                <p style="font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 1rem;">Last Run: ${check.last_run ? new Date(check.last_run).toLocaleString() : 'Never'}</p>
                <div style="background: rgba(0,0,0,0.3); padding: 0.5rem; border-radius: 4px; font-size: 0.8rem; font-family: monospace; white-space: pre-wrap; word-break: break-all; min-height: 40px;">${check.message || 'No details.'}</div>
                <div style="margin-top: 1rem; text-align: right;">
                    <button class="btn btn-primary" style="padding: 0.3rem 0.8rem; font-size: 0.8rem;" onclick="runCheckManual(${check.id})">Run Now</button>
                </div>
            `;
            grid.appendChild(card);
        });
        
    } catch (e) {
        console.error("Failed to load dashboard data", e);
    }
}

async function runCheckManual(checkId) {
    if(!confirm("Are you sure you want to run this check manually?")) return;
    try {
        const res = await fetch(`/api/checks/${checkId}/run`, { method: 'POST' });
        const data = await res.json();
        alert(`Check Completed.\nStatus: ${data.status}\nMessage: ${data.message}`);
        if(window.location.pathname === '/') {
            loadDashboard();
        } else if(window.location.pathname === '/history') {
            loadHistoryPage();
        }
    } catch(e) {
        alert("Failed to run check.");
    }
}

async function loadConfigPage() {
    // Load categories
    const catRes = await fetch('/api/categories');
    const categories = await catRes.json();
    const catSelect = document.getElementById('c_category');
    categories.forEach(c => {
        const opt = document.createElement('option');
        opt.value = c.name;
        opt.innerText = c.name;
        catSelect.appendChild(opt);
    });

    // Handle form submit
    document.getElementById('config-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const payload = {
            name: document.getElementById('c_name').value,
            category: document.getElementById('c_category').value,
            host: document.getElementById('c_host').value,
            target_path: document.getElementById('c_target').value,
            search_pattern: document.getElementById('c_pattern').value,
            ssh_user: document.getElementById('c_ssh_user').value,
            ssh_key_path: document.getElementById('c_ssh_key').value,
            is_scheduled: document.getElementById('c_scheduled').checked,
            schedule_type: document.getElementById('c_schedule_type').value
        };
        
        try {
            await fetch('/api/checks', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            });
            alert('Check added successfully');
            document.getElementById('config-form').reset();
            loadChecksTable();
        } catch(err) {
            alert('Failed to add check');
        }
    });

    loadChecksTable();
}

async function loadChecksTable() {
    const res = await fetch('/api/checks');
    const checks = await res.json();
    const tbody = document.querySelector('#checks-table tbody');
    tbody.innerHTML = '';
    
    checks.forEach(c => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${c.id}</td>
            <td>${c.name}</td>
            <td>${c.category_name}</td>
            <td>${c.host}</td>
            <td>${c.target_path}</td>
            <td>${c.is_scheduled ? c.schedule_type : 'Manual'}</td>
            <td>
                <button class="btn" style="background: var(--danger); color: white; padding: 0.3rem 0.5rem;" onclick="deleteCheck(${c.id})">Delete</button>
                <button class="btn btn-primary" style="padding: 0.3rem 0.5rem; margin-left: 0.5rem;" onclick="runCheckManual(${c.id})">Run</button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

async function deleteCheck(id) {
    if(!confirm("Delete this check?")) return;
    await fetch(`/api/checks/${id}`, { method: 'DELETE' });
    loadChecksTable();
}

async function loadHistoryPage() {
    const res = await fetch('/api/history');
    const history = await res.json();
    const tbody = document.querySelector('#history-table tbody');
    tbody.innerHTML = '';
    
    history.forEach(h => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${new Date(h.execution_time).toLocaleString()}</td>
            <td>${h.check_name}</td>
            <td class="status-${h.status}"><strong>${h.status}</strong></td>
            <td style="max-width: 400px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${h.message}">${h.message}</td>
        `;
        tbody.appendChild(tr);
    });
}
