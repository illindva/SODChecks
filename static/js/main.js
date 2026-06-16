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
        
        // Overall status banner removed.
        
        const grid = document.getElementById('checks-grid');
        grid.innerHTML = '';
        
        const dashboards = ['US SOD', 'SLIM HC'];
        dashboards.forEach(dbName => {
            const dbChecks = data.checks.filter(c => c.dashboard_name === dbName);
            const total = dbChecks.length;
            const passing = dbChecks.filter(c => c.status === 'PASS').length;
            const failing = dbChecks.filter(c => c.status === 'FAIL' || c.status === 'ERROR').length;
            
            let dbStatus = total === 0 ? 'UNKNOWN' : (failing > 0 ? 'FAIL' : 'PASS');
            
            let html = `
                <div class="formal-card bg-${dbStatus}" style="cursor: pointer; transition: transform 0.2s; padding: 2rem;" onclick="window.location.href='/dashboard/${encodeURIComponent(dbName)}'">
                    <h2 style="font-size: 1.5rem; margin-bottom: 0.5rem; display: flex; justify-content: space-between; color: #111827;">
                        ${dbName}
                        <span class="status-badge ${dbStatus}">${dbStatus}</span>
                    </h2>
                    <p style="color: var(--text-secondary); margin-bottom: 1.5rem; font-size: 0.95rem;">Total Checks: <strong>${total}</strong> | Passing: <strong>${passing}</strong> | Failing: <strong style="color: var(--danger)">${failing}</strong></p>
                    
                    <div style="margin-top: 1rem; border-top: 1px solid var(--card-border); padding-top: 1rem;">
                        <h4 style="margin-bottom: 0.75rem; color: var(--text-secondary); font-size: 0.85rem; text-transform: uppercase;">Checks Overview:</h4>
            `;
            
            if (dbChecks.length === 0) {
                 html += `<p style="font-size: 0.85rem; color: var(--text-secondary);">No checks configured for this dashboard.</p>`;
            } else {
                 dbChecks.forEach(c => {
                     let lastRunStr = "Never";
                     if (c.last_run) {
                         // c.last_run is from python's datetime.utcnow(), so it's in UTC but lacks 'Z'
                         let date = new Date(c.last_run + "Z");
                         lastRunStr = date.toUTCString(); // formats to GMT string
                     }
                     
                     html += `<div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.9rem; padding: 0.5rem 0; border-bottom: 1px dashed var(--card-border);">
                                 <div style="display: flex; flex-direction: column;">
                                     <span style="color: #374151; font-weight: 500;">${c.name}</span>
                                     <span style="color: var(--text-secondary); font-size: 0.75rem;">Last run: ${lastRunStr}</span>
                                 </div>
                                 <span class="status-${c.status}" style="font-weight: 600;">${c.status}</span>
                              </div>`;
                 });
            }
            html += `</div></div>`;
            grid.innerHTML += html;
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

let allChecks = [];

async function loadConfigPage() {
    const catRes = await fetch('/api/categories');
    const categories = await catRes.json();
    const catSelect = document.getElementById('c_category');
    categories.forEach(c => {
        if (['json_to_html', 'html_to_json'].includes(c.name)) return;
        
        const opt = document.createElement('option');
        opt.value = c.name;
        opt.innerText = c.name;
        catSelect.appendChild(opt);
    });

    // UI Toggles
    const osSelect = document.getElementById('c_os_type');
    osSelect.addEventListener('change', () => {
        updateFieldsForCategory(catSelect.value);
    });

    catSelect.addEventListener('change', () => {
        updateFieldsForCategory(catSelect.value);
    });
    
    // Initial call
    setTimeout(() => updateFieldsForCategory(catSelect.value), 100);

    const schedCheck = document.getElementById('c_scheduled');
    const schedOpts = document.getElementById('schedule_options');
    schedCheck.addEventListener('change', () => {
        schedOpts.style.display = schedCheck.checked ? 'block' : 'none';
    });
    
    document.getElementById('btn-cancel-edit').addEventListener('click', () => {
        resetForm();
    });

    // Handle form submit
    document.getElementById('config-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        
        let stype = document.getElementById('c_schedule_type').value;
        let cron = "";
        let hour = document.getElementById('c_sched_hour').value || "0";
        let days = document.getElementById('c_sched_days').value || "*";
        
        if (stype === 'hourly') {
            cron = `0 * * * ${days}`;
        } else if (stype === 'daily' || stype === 'weekly' || stype === 'custom_cron') {
            cron = `0 ${hour} * * ${days}`;
        }

        const payload = {
            name: document.getElementById('c_name').value,
            description: document.getElementById('c_description').value,
            dashboard_name: document.getElementById('c_dashboard').value,
            category: document.getElementById('c_category').value,
            os_type: document.getElementById('c_os_type').value,
            host: document.getElementById('c_host').value,
            target_path: document.getElementById('c_target').value,
            search_pattern: document.getElementById('c_pattern').value,
            ssh_user: document.getElementById('c_ssh_user').value,
            ssh_key_path: document.getElementById('c_ssh_key').value,
            password: document.getElementById('c_password').value,
            is_scheduled: document.getElementById('c_scheduled').checked,
            schedule_type: 'custom_cron',
            cron_expression: cron
        };
        
        const c_id = document.getElementById('c_id').value;
        let url = '/api/checks';
        let method = 'POST';
        
        if (c_id) {
            url = `/api/checks/${c_id}`;
            method = 'PUT';
        }
        
        try {
            await fetch(url, {
                method: method,
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            });
            alert(c_id ? 'Check updated successfully' : 'Check added successfully');
            resetForm();
            loadChecksTable();
        } catch(err) {
            alert('Failed to save check');
        }
    });

    document.getElementById('btn-test-connection').addEventListener('click', async () => {
        const payload = {
            id: document.getElementById('c_id').value,
            category: document.getElementById('c_category').value,
            os_type: document.getElementById('c_os_type').value,
            host: document.getElementById('c_host').value,
            target_path: document.getElementById('c_target').value,
            search_pattern: document.getElementById('c_pattern').value,
            ssh_user: document.getElementById('c_ssh_user').value,
            ssh_key_path: document.getElementById('c_ssh_key').value,
            password: document.getElementById('c_password').value
        };
        
        const btn = document.getElementById('btn-test-connection');
        const origText = btn.innerText;
        btn.innerText = 'Testing...';
        btn.disabled = true;
        
        try {
            const res = await fetch('/api/test_connection', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (res.ok) {
                alert(`Test Connection: ${data.status}\nMessage: ${data.message}`);
            } else {
                alert(`Test Connection Failed: ${data.error || 'Unknown error'}`);
            }
        } catch(err) {
            alert('Failed to test connection');
        } finally {
            btn.innerText = origText;
            btn.disabled = false;
        }
    });

    loadChecksTable();
}

function resetForm() {
    document.getElementById('config-form').reset();
    document.getElementById('c_id').value = '';
    document.getElementById('c_description').value = '';
    document.getElementById('c_dashboard').value = 'US SOD';
    document.getElementById('form-title').innerText = 'Add New Check';
    document.getElementById('btn-save').innerText = 'Save Check';
    document.getElementById('btn-cancel-edit').style.display = 'none';
    document.getElementById('schedule_options').style.display = 'none';
    updateFieldsForCategory(document.getElementById('c_category').value);
}

window.editCheck = function(id) {
    const check = allChecks.find(c => c.id === id);
    if (!check) return;
    
    document.getElementById('c_id').value = check.id;
    document.getElementById('c_name').value = check.name;
    document.getElementById('c_description').value = check.description || '';
    document.getElementById('c_dashboard').value = check.dashboard_name || 'US SOD';
    document.getElementById('c_category').value = check.category_name;
    document.getElementById('c_os_type').value = check.os_type || 'linux';
    document.getElementById('c_host').value = check.host;
    document.getElementById('c_target').value = check.target_path;
    document.getElementById('c_pattern').value = check.search_pattern || '';
    document.getElementById('c_ssh_user').value = check.ssh_user || '';
    document.getElementById('c_ssh_key').value = check.ssh_key_path || '';
    document.getElementById('c_password').value = ''; // Don't show password
    
    document.getElementById('c_scheduled').checked = check.is_scheduled;
    document.getElementById('schedule_options').style.display = check.is_scheduled ? 'block' : 'none';
    
    updateFieldsForCategory(check.category_name);
    
    document.getElementById('form-title').innerText = 'Edit Check: ' + check.name;
    document.getElementById('btn-save').innerText = 'Update Check';
    document.getElementById('btn-cancel-edit').style.display = 'inline-block';
    window.scrollTo(0,0);
}

async function loadChecksTable() {
    const res = await fetch('/api/checks');
    allChecks = await res.json();
    const tbody = document.querySelector('#checks-table tbody');
    tbody.innerHTML = '';
    
    allChecks.forEach(c => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${c.id}</td>
            <td style="font-weight: 500;">${c.name}</td>
            <td style="text-transform: capitalize;">${c.os_type || 'Linux'}</td>
            <td><span style="background: #e5e7eb; padding: 2px 6px; border-radius: 4px; font-size: 0.75rem;">${c.category_name}</span></td>
            <td>${c.host}</td>
            <td style="font-family: monospace; font-size: 0.75rem;">${c.target_path}</td>
            <td>${c.is_scheduled ? 'Scheduled' : 'Manual'}</td>
            <td style="text-align: right; white-space: nowrap;">
                <button class="btn btn-primary" style="background: #f59e0b; padding: 0.3rem 0.5rem;" onclick="editCheck(${c.id})">Edit</button>
                <button class="btn btn-danger" style="padding: 0.3rem 0.5rem; margin-left: 0.5rem;" onclick="deleteCheck(${c.id})">Delete</button>
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
            <td style="color: var(--text-secondary);">${new Date(h.execution_time).toLocaleString()}</td>
            <td style="font-weight: 500;">${h.check_name}</td>
            <td><span class="status-badge ${h.status}">${h.status}</span></td>
            <td style="max-width: 400px; overflow: hidden; text-overflow: ellipsis;"><div class="log-box" style="margin: 0; min-height: auto; padding: 0.5rem;">${h.message}</div></td>
        `;
        tbody.appendChild(tr);
    });
}

async function sendEmailReport(dashboardName) {
    let email = prompt("Enter recipient email address:", "hi.villinda@gmail.com");
    if (!email) return;

    try {
        let payload = { email: email };
        if (dashboardName) {
            payload.dashboard_name = dashboardName;
        }

        const res = await fetch('/api/send_report', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await res.json();
        if (res.ok) {
            alert(data.message);
        } else {
            alert("Error: " + (data.error || "Failed to send report"));
        }
    } catch (e) {
        alert("Failed to send report request.");
    }
}

function updateFieldsForCategory(category) {
    const groupOsType = document.getElementById('group_os_type');
    const groupHost = document.getElementById('group_host');
    const groupTarget = document.getElementById('group_target');
    const groupPattern = document.getElementById('group_pattern');
    const groupSshUser = document.getElementById('group_ssh_user');
    const groupSshKey = document.getElementById('group_ssh_key');
    const groupPassword = document.getElementById('group_password');

    const lblHost = document.getElementById('label_host');
    const lblTarget = document.getElementById('label_target');
    const lblPattern = document.getElementById('label_pattern');
    const lblSshUser = document.getElementById('label_ssh_user');
    const lblPassword = document.getElementById('label_password');

    // Default: Reset everything to visible
    groupOsType.style.display = 'block';
    groupHost.style.display = 'block';
    groupTarget.style.display = 'block';
    groupPattern.style.display = 'block';
    groupSshUser.style.display = 'block';
    groupSshKey.style.display = 'block';
    groupPassword.style.display = 'none';

    // Default labels
    lblHost.innerText = 'Host';
    lblTarget.innerText = 'Target Path (Log file or Process name)';
    lblPattern.innerText = 'Search Pattern (for Logs)';
    lblSshUser.innerText = 'SSH User (for remote)';
    lblPassword.innerText = 'Password (Windows remote)';

    // Handle OS specific toggles for standard checks
    const osVal = document.getElementById('c_os_type').value;
    if (osVal === 'windows') {
        groupSshKey.style.display = 'none';
        groupPassword.style.display = 'block';
    }

    if (category === 'linux_command') {
        groupOsType.style.display = 'none';
        groupPattern.style.display = 'none';
        groupPassword.style.display = 'none';
        groupSshKey.style.display = 'block';
        lblTarget.innerText = 'Linux Command to Execute';
    } 
    else if (category === 'windows_command') {
        groupOsType.style.display = 'none';
        groupPattern.style.display = 'none';
        groupSshKey.style.display = 'none';
        groupPassword.style.display = 'block';
        lblTarget.innerText = 'CMD Command to Execute';
    }
    else if (category === 'gemfire_oql') {
        groupOsType.style.display = 'none';
        groupTarget.style.display = 'none';
        groupSshKey.style.display = 'none';
        groupPassword.style.display = 'block';
        lblHost.innerText = 'GemFire REST API URL (e.g. http://server:8080)';
        lblPattern.innerText = 'OQL Query';
        lblSshUser.innerText = 'API Username';
        lblPassword.innerText = 'API Password';
    }
    else if (['oracle_query', 'mssql_query', 'sybase_query'].includes(category)) {
        groupOsType.style.display = 'none';
        groupSshKey.style.display = 'none';
        groupPassword.style.display = 'block';
        lblHost.innerText = 'DB Host:Port (e.g. localhost:1521)';
        lblTarget.innerText = category === 'oracle_query' ? 'DB Service Name' : 'Database Name';
        lblSshUser.innerText = 'DB User';
        lblPassword.innerText = 'DB Password';
        lblPattern.innerText = 'SQL Query';
    }
    else if (category === 'process_stats') {
        groupPattern.style.display = 'none';
        lblTarget.innerText = 'Process Name or PID';
    }
    else if (category === 'send_email') {
        groupOsType.style.display = 'none';
        groupHost.style.display = 'none';
        groupPattern.style.display = 'none';
        groupSshUser.style.display = 'none';
        groupSshKey.style.display = 'none';
        groupPassword.style.display = 'none';
        lblTarget.innerText = 'Recipient Emails (Comma-separated)';
    }
    else if (category === 'teams_notification') {
        groupOsType.style.display = 'none';
        groupHost.style.display = 'none';
        groupTarget.style.display = 'none';
        groupSshUser.style.display = 'none';
        groupSshKey.style.display = 'none';
        groupPassword.style.display = 'none';
        lblPattern.innerText = 'Message Text';
    }
    else if (['json_to_html', 'html_to_json'].includes(category)) {
        groupOsType.style.display = 'none';
        groupHost.style.display = 'none';
        groupTarget.style.display = 'none';
        groupSshUser.style.display = 'none';
        groupSshKey.style.display = 'none';
        groupPassword.style.display = 'none';
        lblPattern.innerText = category === 'json_to_html' ? 'JSON Input String' : 'HTML Input String';
    }
}
