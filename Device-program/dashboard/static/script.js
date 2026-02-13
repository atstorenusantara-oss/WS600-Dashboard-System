let trendChart = null;
let currentLogs = [];
let lastLogId = null;
const previewRows = [];

function switchTab(tab) {
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));

    if (tab === 'monitor') {
        document.querySelector('button[onclick="switchTab(\'monitor\')"]').classList.add('active');
        document.getElementById('monitor-view').classList.add('active');
    } else {
        document.querySelector('button[onclick="switchTab(\'logs\')"]').classList.add('active');
        document.getElementById('logs-view').classList.add('active');
        fetchLogs();
    }
}

async function fetchLatest() {
    try {
        const response = await fetch('/api/latest');
        const data = await response.json();

        if (data.error) return;

        // Update Speed
        document.getElementById('speed-value').innerText = `${data.wind_speed.toFixed(2)} m/s`;
        const speedPercent = Math.min((data.wind_speed / 20) * 100, 100);
        document.getElementById('speed-bar').style.width = `${speedPercent}%`;
        document.getElementById('speed-desc').innerText = getBeaufortScale(data.wind_speed);

        // Update Direction
        document.getElementById('dir-value').innerText = `${data.wind_direction.toFixed(1)}°`;
        document.getElementById('dir-cardinal').innerText = `(${getCardinal(data.wind_direction)})`;
        document.getElementById('wind-needle').style.transform = `rotate(${data.wind_direction}deg)`;

        // Update Weather
        document.getElementById('temp-value').innerText = `${data.temperature.toFixed(1)} °C`;
        document.getElementById('hum-value').innerText = `${data.humidity.toFixed(1)} %`;
        document.getElementById('pres-value').innerText = `${data.pressure.toFixed(1)} hPa`;
        document.getElementById('rain-value').innerText = `${data.rain_total.toFixed(2)} mm`;

        // Update Preview Table
        updatePreview(data);

    } catch (err) {
        console.error("Error fetching latest data:", err);
    }
}

function updatePreview(data) {
    if (data.id === lastLogId) return;
    lastLogId = data.id;

    // If logs tab is active, refresh logs too
    if (document.getElementById('logs-view').classList.contains('active')) {
        fetchLogs();
    }

    const time = data.timestamp.split(' ')[1];
    previewRows.unshift({
        time: time,
        speed: data.wind_speed,
        dir: data.wind_direction,
        temp: data.temperature
    });

    if (previewRows.length > 5) previewRows.pop();

    const tbody = document.getElementById('preview-body');
    tbody.innerHTML = previewRows.map(row => `
        <tr>
            <td>${row.time}</td>
            <td>${row.speed.toFixed(2)}</td>
            <td>${row.dir.toFixed(0)}°</td>
            <td>${row.temp.toFixed(1)}</td>
        </tr>
    `).join('');
}

async function fetchLogs() {
    try {
        const response = await fetch('/api/logs?limit=100');
        const logs = await response.json();
        currentLogs = logs;

        const tbody = document.getElementById('logs-body');
        tbody.innerHTML = logs.map(row => `
            <tr>
                <td>${row.timestamp.split(' ')[1]}</td>
                <td>${row.wind_speed.toFixed(1)}</td>
                <td>${row.wind_direction.toFixed(0)}°</td>
                <td>${row.temperature.toFixed(1)}</td>
                <td>${row.humidity.toFixed(0)}</td>
                <td>${row.pressure.toFixed(0)}</td>
                <td>${row.rain_total.toFixed(1)}</td>
            </tr>
        `).join('');

        updateChart();
    } catch (err) {
        console.error("Error fetching logs:", err);
    }
}

function initChart() {
    const ctx = document.getElementById('trendChart').getContext('2d');
    trendChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Value',
                data: [],
                borderColor: '#2563eb',
                backgroundColor: 'rgba(37, 99, 235, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.4,
                pointRadius: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: false,
                    grid: { color: '#1f2937' },
                    ticks: { color: '#9ca3af' }
                },
                x: {
                    grid: { display: false },
                    ticks: { color: '#9ca3af', maxRotation: 45, minRotation: 45 }
                }
            },
            plugins: {
                legend: { display: false }
            }
        }
    });
}

function updateChart() {
    if (!trendChart) initChart();

    const paramSelector = document.getElementById('param-selector');
    if (!paramSelector) return;

    const param = paramSelector.value;
    const labels = currentLogs.map(row => row.timestamp.split(' ')[1]).reverse();
    const data = currentLogs.map(row => row[param]).reverse();

    trendChart.data.labels = labels;
    trendChart.data.datasets[0].data = data;

    // Update colors based on param
    const colors = {
        wind_speed: '#22c55e',
        wind_direction: '#22d3ee',
        temperature: '#ef4444',
        humidity: '#a855f7',
        pressure: '#eab308',
        rain_total: '#3b82f6'
    };

    trendChart.data.datasets[0].borderColor = colors[param] || '#2563eb';
    trendChart.data.datasets[0].backgroundColor = (colors[param] || '#2563eb') + '20';

    trendChart.update();

    // Update Titles
    const paramName = paramSelector.options[paramSelector.selectedIndex].text;
    document.getElementById('chart-title').innerText = `${paramName} Trend`;
    document.getElementById('chart-subtitle').innerText = `${paramName} analysis over time`;
}

function updateChartParam() {
    updateChart();
}

function getCardinal(angle) {
    const directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'];
    const index = Math.round(angle / 45) % 8;
    return directions[index];
}

function getBeaufortScale(speed) {
    if (speed < 0.5) return "Calm";
    if (speed < 1.5) return "Light Air";
    if (speed < 3.3) return "Light Breeze";
    if (speed < 5.5) return "Gentle Breeze";
    if (speed < 8.0) return "Moderate Breeze";
    if (speed < 10.8) return "Fresh Breeze";
    return "Strong Breeze+";
}

async function fetchStatus() {
    try {
        const response = await fetch('/api/status');
        const status = await response.json();

        const dot = document.getElementById('status-dot');
        const text = document.getElementById('status-text');

        dot.classList.remove('active', 'warning', 'error');

        if (!status.port_connected) {
            dot.classList.add('error');
            text.innerText = "Cek USB TTL-nya";
        } else if (!status.sensor_responding) {
            dot.classList.add('warning');
            text.innerText = "Cek sensor atau wiring sensor";
        } else {
            dot.classList.add('active');
            text.innerText = "Sensor Terhubung (Live)";
        }
    } catch (err) {
        console.error("Error fetching status:", err);
    }
}

// Initial Fetch
fetchLatest();
fetchStatus();
// Update every 2 seconds
setInterval(() => {
    fetchLatest();
    fetchStatus();
}, 2000);
