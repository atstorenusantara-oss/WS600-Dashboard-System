let trendChart = null;
let windRoseChart = null;
let currentLogs = [];
let lastLogId = null;
const previewRows = [];

function switchTab(tab) {
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));

    const activeBtn = document.querySelector(`button[onclick="switchTab('${tab}')"]`);
    if (activeBtn) activeBtn.classList.add('active');

    const activeView = document.getElementById(`${tab}-view`);
    if (activeView) activeView.classList.add('active');

    if (tab === 'logs') fetchLogs();
    if (tab === 'windrose') fetchWindRoseData();
    if (tab === 'settings') loadSettings();
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
    // Preview table removed from UI, updating only logs view if active
    if (data.id === lastLogId) return;
    lastLogId = data.id;

    if (document.getElementById('logs-view').classList.contains('active')) {
        fetchLogs();
    }
}

async function fetchLogs() {
    try {
        const start = document.getElementById('start-date').value;
        const end = document.getElementById('end-date').value;

        let url = '/api/logs?limit=100';
        if (start && end) {
            url += `&start_date=${start}&end_date=${end}`;
        }

        console.log("Fetching logs from:", url);
        const response = await fetch(url);
        const logs = await response.json();
        currentLogs = logs;

        const tbody = document.getElementById('logs-body');
        if (!logs || logs.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding: 2rem;">Tidak ada data ditemukan. Klik "Tampilkan" untuk memuat atau periksa range tanggal.</td></tr>';
            return;
        }

        tbody.innerHTML = logs.map(row => `
            <tr>
                <td>${row.timestamp}</td>
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

async function exportToExcel() {
    try {
        console.log("Exporting to Excel (Server Side)...");
        const startDate = document.getElementById('start-date').value;
        const endDate = document.getElementById('end-date').value;

        let url = `/api/export-excel?limit=5000`;
        if (startDate && endDate) {
            url += `&start_date=${startDate}&end_date=${endDate}`;
        }

        const response = await fetch(url);

        // Cek apakah server mengirim JSON (USB saved) atau Blob (Download)
        const contentType = response.headers.get("content-type");
        if (contentType && contentType.indexOf("application/json") !== -1) {
            const result = await response.json();
            if (result.status === "saved_to_usb") {
                alert(`✅ BERHASIL!\nLaporan telah disimpan langsung ke Flashdisk.\n\nFolder: ${result.path}`);
            } else {
                alert("Gagal simpan ke USB: " + (result.detail || "Error tidak diketahui"));
            }
        } else if (response.ok) {
            // Flashdisk tidak ada, download via browser
            const blob = await response.blob();
            const urlBlob = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = urlBlob;
            a.download = `Laporan_Cuaca_${new Date().getTime()}.xlsx`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            alert("⚠️ Flashdisk tidak ditemukan.\nLaporan telah di-download ke folder Downloads PC ini.");
        } else {
            const err = await response.json();
            alert("Gagal Export: " + (err.detail || "Server Error"));
        }
    } catch (err) {
        console.error("Excel Export Error:", err);
        alert("Gagal Export Excel: " + err.message);
    }
}

async function exportToPDF() {
    try {
        console.log("Exporting to PDF...");
        if (!currentLogs || currentLogs.length === 0) {
            alert("Belum ada data untuk di-export. Klik tombol 'Tampilkan' dulu.");
            return;
        }

        const { jsPDF } = window.jspdf;
        if (!jsPDF) {
            alert("Eror: Library PDF belum siap.");
            return;
        }

        const doc = new jsPDF('l', 'mm', 'a4');
        const fileName = `Laporan_Cuaca_${new Date().getTime()}.pdf`;

        // Style PDF Header
        doc.setFillColor(37, 99, 235);
        doc.rect(0, 0, 297, 25, 'F');
        doc.setTextColor(255, 255, 255);
        doc.setFontSize(22);

        // Add Logo if exists
        const logo = document.getElementById('app-logo');
        if (logo) {
            try {
                // Posisi: x=10, y=5, ukuran: 15x15 mm
                doc.addImage(logo, 'PNG', 10, 5, 15, 15);
                doc.text("INSALUSI WEATHER STATION REPORT", 30, 17);
            } catch (e) {
                console.error("Gagal menambahkan logo ke PDF:", e);
                doc.text("INSALUSI WEATHER STATION REPORT", 14, 17);
            }
        } else {
            doc.text("INSALUSI WEATHER STATION REPORT", 14, 17);
        }

        doc.setTextColor(100, 100, 100);
        doc.setFontSize(10);
        doc.text(`Dicetak pada: ${new Date().toLocaleString()}`, 14, 32);

        // Add Chart Image
        const chartCanvas = document.getElementById('trendChart');
        if (chartCanvas) {
            const chartImg = chartCanvas.toDataURL("image/png");
            doc.addImage(chartImg, 'PNG', 14, 40, 269, 70);
        }

        // Add Content Table
        const tableData = currentLogs.map(row => [
            row.timestamp,
            row.wind_speed.toFixed(2),
            row.wind_direction.toFixed(0),
            row.temperature.toFixed(1),
            row.humidity.toFixed(0),
            row.pressure.toFixed(1),
            row.rain_total.toFixed(2)
        ]);

        doc.autoTable({
            startY: 120,
            head: [['Waktu', 'Kec. Angin (m/s)', 'Arah (°)', 'Suhu (°C)', 'Lembab (%)', 'Tekan (hPa)', 'Hujan (mm)']],
            body: tableData,
            theme: 'striped',
            headStyles: { fillColor: [37, 99, 235], textColor: [255, 255, 255] },
            styles: { fontSize: 9 }
        });

        // --- HALAMAN 2: WIND ROSE ANALYSIS ---
        doc.addPage('l', 'mm', 'a4');

        // Header Halaman 2
        doc.setFillColor(37, 99, 235);
        doc.rect(0, 0, 297, 25, 'F');
        doc.setTextColor(255, 255, 255);
        doc.setFontSize(22);
        if (logo) {
            doc.addImage(logo, 'PNG', 10, 5, 15, 15);
            doc.text("INSALUSI WEATHER STATION REPORT", 30, 17);
        } else {
            doc.text("INSALUSI WEATHER STATION REPORT", 14, 17);
        }

        doc.setTextColor(37, 99, 235);
        doc.setFontSize(18);
        doc.text("Analisis Mawar Angin (Wind Rose)", 14, 40);

        doc.setDrawColor(200, 200, 200);
        doc.line(14, 45, 283, 45);

        // Tambahkan Grafik Wind Rose
        const roseCanvas = document.getElementById('windRoseChart');
        if (roseCanvas) {
            const roseImg = roseCanvas.toDataURL("image/png");
            doc.addImage(roseImg, 'PNG', 14, 55, 130, 130);
        }

        // Hitung statistik secara mandiri (agar tidak kosong jika tab wind rose belum dibuka)
        const roseBins = new Array(16).fill(0);
        const roseLabels = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW'];
        let totalSpd = 0; let maxSpd = 0;

        currentLogs.forEach(row => {
            const idx = Math.round(row.wind_direction / 22.5) % 16;
            roseBins[idx]++;
            totalSpd += row.wind_speed;
            if (row.wind_speed > maxSpd) maxSpd = row.wind_speed;
        });

        const domIdx = roseBins.indexOf(Math.max(...roseBins));
        const avgSpd = totalSpd / currentLogs.length;

        // Tambahkan Ringkasan Analisis di Sisi Kanan
        doc.setTextColor(50, 50, 50);
        doc.setFontSize(14);
        doc.text("Ringkasan Analisis Statistik", 160, 65);

        doc.setFontSize(11);
        const statsX = 160;
        let statsY = 80;
        const spacing = 12;

        const summaryData = [
            ["Arah Dominan", roseLabels[domIdx]],
            ["Kecepatan Rerata", avgSpd.toFixed(2) + " m/s"],
            ["Kecepatan Maksimum", maxSpd.toFixed(2) + " m/s"],
            ["Total Sampel", currentLogs.length.toString()],
            ["Periode Laporan", document.getElementById('start-date').value + " s/d " + document.getElementById('end-date').value]
        ];

        summaryData.forEach(([label, value]) => {
            doc.setTextColor(100, 100, 100);
            doc.text(label + ":", statsX, statsY);
            doc.setTextColor(0, 0, 0);
            doc.setFont("helvetica", "bold");
            doc.text(value, statsX + 50, statsY);
            doc.setFont("helvetica", "normal");
            statsY += spacing;
        });

        // --- TRY TO SAVE TO USB VIA SERVER ---
        const pdfBlob = doc.output('blob');
        const formData = new FormData();
        formData.append('file', pdfBlob, fileName);

        const usbResponse = await fetch('/api/save-usb', {
            method: 'POST',
            body: formData
        });

        const result = await usbResponse.json();
        if (result.status === "saved_to_usb") {
            alert(`✅ BERHASIL!\nPDF telah disimpan langsung ke Flashdisk.\n\nFolder: ${result.path}`);
        } else {
            // Fallback: Simpan via browser
            doc.save(fileName);
            alert("⚠️ Flashdisk tidak ditemukan.\nLaporan PDF telah di-download ke folder Downloads PC.");
        }

    } catch (err) {
        console.error("PDF Export Error:", err);
        alert("Gagal Export PDF: " + err.message);
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
                    grid: { color: 'rgba(156, 163, 175, 0.1)' },
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

    // Update colors based on theme
    const style = getComputedStyle(document.body);
    const textColor = style.getPropertyValue('--text-secondary').trim();
    const gridColor = body.classList.contains('light-theme') ? 'rgba(0,0,0,0.1)' : 'rgba(255,255,255,0.1)';

    trendChart.options.scales.y.ticks.color = textColor;
    trendChart.options.scales.x.ticks.color = textColor;
    trendChart.options.scales.y.grid.color = gridColor;

    trendChart.update();

    const paramName = paramSelector.options[paramSelector.selectedIndex].text;
    document.getElementById('chart-title').innerText = `${paramName} Trend`;
    document.getElementById('chart-subtitle').innerText = `${paramName} analysis over time`;
}

function updateChartParam() {
    updateChart();
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
            text.innerText = "Cek USB TTL";
        } else if (!status.sensor_responding) {
            dot.classList.add('warning');
            text.innerText = "Cek Wiring Sensor";
        } else {
            dot.classList.add('active');
            text.innerText = "Sensor Terhubung (Live)";
        }
    } catch (err) {
        console.error("Error fetching status:", err);
    }
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

// Theme Management
const themeToggle = document.getElementById('theme-toggle');
const body = document.body;

const savedTheme = localStorage.getItem('theme');
if (savedTheme === 'light') {
    body.classList.add('light-theme');
    updateThemeIcon(true);
}

themeToggle.addEventListener('click', () => {
    const isLight = body.classList.toggle('light-theme');
    localStorage.setItem('theme', isLight ? 'light' : 'dark');
    updateThemeIcon(isLight);
    if (trendChart) updateChart();
});

function toggleRoseCustomDates() {
    const period = document.getElementById('rose-period').value;
    document.getElementById('rose-custom-dates').style.display = period === 'custom' ? 'flex' : 'none';
    if (period !== 'custom') fetchWindRoseData();
}

async function fetchWindRoseData() {
    try {
        const period = document.getElementById('rose-period').value;
        let url = '/api/logs?limit=5000'; // Ambil lebih banyak data untuk statistik

        if (period === 'today') {
            const today = new Date().toISOString().split('T')[0];
            url += `&start_date=${today}&end_date=${today}`;
        } else if (period === '7days') {
            const end = new Date();
            const start = new Date();
            start.setDate(end.getDate() - 7);
            url += `&start_date=${start.toISOString().split('T')[0]}&end_date=${end.toISOString().split('T')[0]}`;
        } else if (period === '30days') {
            const end = new Date();
            const start = new Date();
            start.setDate(end.getDate() - 30);
            url += `&start_date=${start.toISOString().split('T')[0]}&end_date=${end.toISOString().split('T')[0]}`;
        } else if (period === 'custom') {
            const start = document.getElementById('rose-start').value;
            const end = document.getElementById('rose-end').value;
            if (start && end) url += `&start_date=${start}&end_date=${end}`;
        }

        const response = await fetch(url);
        const data = await response.json();
        processWindRose(data);
    } catch (err) {
        console.error("Error fetching wind rose data:", err);
    }
}

function processWindRose(data) {
    if (!data || data.length === 0) {
        alert("Tidak ada data untuk periode ini.");
        return;
    }

    // 16 Arah
    const bins = new Array(16).fill(0);
    const binSpeeds = new Array(16).fill(0);
    const labels = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW'];

    let totalSpeed = 0;
    let maxSpeed = 0;

    data.forEach(row => {
        const angle = row.wind_direction;
        const index = Math.round(angle / 22.5) % 16;
        bins[index]++;
        binSpeeds[index] += row.wind_speed;
        totalSpeed += row.wind_speed;
        if (row.wind_speed > maxSpeed) maxSpeed = row.wind_speed;
    });

    const percentages = bins.map(count => (count / data.length * 100).toFixed(1));

    // Tentukan warna berdasarkan rata-rata kecepatan di arah tersebut
    const bgColors = bins.map((count, i) => {
        if (count === 0) return 'rgba(148, 163, 184, 0.2)';
        const avg = binSpeeds[i] / count;
        if (avg < 2) return 'rgba(34, 211, 238, 0.7)';   // Cyan (Rendah < 2m/s)
        if (avg <= 5) return 'rgba(251, 191, 36, 0.7)'; // Yellow (Sedang 2-5m/s)
        return 'rgba(239, 68, 68, 0.7)';               // Red (Tinggi > 5m/s)
    });

    // Update Stats UI
    const maxFreqIndex = bins.indexOf(Math.max(...bins));
    document.getElementById('dominant-dir').innerText = labels[maxFreqIndex];
    document.getElementById('avg-speed').innerText = (totalSpeed / data.length).toFixed(2) + " m/s";
    document.getElementById('max-speed').innerText = maxSpeed.toFixed(2) + " m/s";
    document.getElementById('rose-count').innerText = data.length;

    renderWindRoseChart(labels, percentages, bgColors);
}

function renderWindRoseChart(labels, data, bgColors) {
    const ctx = document.getElementById('windRoseChart').getContext('2d');

    if (windRoseChart) windRoseChart.destroy();

    const isLight = document.body.classList.contains('light-theme');

    windRoseChart = new Chart(ctx, {
        type: 'polarArea',
        data: {
            labels: labels,
            datasets: [{
                label: 'Frekuensi (%)',
                data: data,
                backgroundColor: bgColors,
                borderColor: isLight ? '#ffffff' : '#0f172a',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                r: {
                    grid: { color: isLight ? 'rgba(0,0,0,0.05)' : 'rgba(255,255,255,0.05)' },
                    angleLines: { color: isLight ? 'rgba(0,0,0,0.1)' : 'rgba(255,255,255,0.1)' },
                    pointLabels: {
                        display: true,
                        centerPointLabels: true,
                        font: { size: 12, weight: 'bold' },
                        color: isLight ? '#0f172a' : '#f9fafb'
                    },
                    ticks: {
                        display: false
                    }
                }
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'bottom',
                    labels: {
                        color: '#2300ebff',
                        generateLabels: (chart) => [
                            { text: 'Angin Tenang (<2 m/s)', fillStyle: 'rgba(34, 211, 238, 0.7)' },
                            { text: 'Angin Sedang (2-5 m/s)', fillStyle: 'rgba(251, 191, 36, 0.7)' },
                            { text: 'Angin Kencang (>5 m/s)', fillStyle: 'rgba(239, 68, 68, 0.7)' }
                        ]
                    }
                },
                tooltip: {
                    callbacks: {
                        label: (context) => `Frekuensi: ${context.raw}%`
                    }
                }
            }
        }
    });
}

function updateThemeIcon(isLight) {
    const icon = document.getElementById('theme-icon');
    if (isLight) {
        icon.innerHTML = '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>';
    } else {
        icon.innerHTML = `
            <circle cx="12" cy="12" r="5"></circle>
            <line x1="12" y1="1" x2="12" y2="3"></line>
            <line x1="12" y1="21" x2="12" y2="23"></line>
            <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line>
            <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line>
            <line x1="1" y1="12" x2="3" y2="12"></line>
            <line x1="21" y1="12" x2="23" y2="12"></line>
            <line x1="4.22" y1="18.36" x2="5.64" y2="16.93"></line>
            <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>
        `;
    }
}

async function fetchForecast() {
    try {
        const response = await fetch('/api/forecast');
        const data = await response.json();

        if (data.error) {
            document.getElementById('ai-status').innerText = "Tunggu...";
            return;
        }

        document.getElementById('fore-temp').innerText = data.prediction_1h.temperature;
        document.getElementById('fore-hum').innerText = data.prediction_1h.humidity;
        document.getElementById('fore-wind').innerText = data.prediction_1h.wind_speed;

        document.getElementById('ai-status').innerText = "Prediksi Aktif";
        document.getElementById('ai-confidence').innerText = `Keyakinan: ${data.confidence} (${new Date().toLocaleTimeString()})`;
    } catch (err) {
        console.error("Error fetching AI forecast:", err);
    }
}

fetchLatest();
fetchStatus();
fetchForecast();

setInterval(() => {
    fetchLatest();
    fetchStatus();
}, 2000);

// Forecast diupdate setiap 30 detik agar tidak berat
setInterval(fetchForecast, 30000);

async function loadSettings() {
    try {
        const response = await fetch('/api/settings');
        const settings = await response.json();

        document.getElementById('set-poll').value = settings.poll_interval;
        document.getElementById('set-save').value = settings.save_interval;
        document.getElementById('set-port').value = settings.com_port;
        document.getElementById('set-baud').value = settings.baudrate;
    } catch (err) {
        console.error("Error loading settings:", err);
    }
}

async function saveSettings() {
    const status = document.getElementById('save-status');
    status.innerText = "⏳ Menyimpan...";
    status.style.color = "var(--text-secondary)";

    const settings = {
        poll_interval: parseInt(document.getElementById('set-poll').value),
        save_interval: parseInt(document.getElementById('set-save').value),
        com_port: document.getElementById('set-port').value,
        baudrate: parseInt(document.getElementById('set-baud').value)
    };

    try {
        const response = await fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(settings)
        });

        if (response.ok) {
            status.innerText = "✅ Pengaturan berhasil disimpan!";
            status.style.color = "var(--accent-green)";
            setTimeout(() => { status.innerText = ""; }, 3000);
        } else {
            throw new Error("Failed to save");
        }
    } catch (err) {
        status.innerText = "❌ Gagal menyimpan pengaturan.";
        status.style.color = "#ef4444";
        console.error("Error saving settings:", err);
    }
}

function updateClock() {
    const now = new Date();

    // Format Waktu: HH:MM:SS
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    const seconds = String(now.getSeconds()).padStart(2, '0');
    document.getElementById('clock-time').textContent = `${hours}:${minutes}:${seconds}`;

    // Format Tanggal: Hari, DD MMM YYYY
    const days = ['Minggu', 'Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu'];
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des'];

    const dayName = days[now.getDay()];
    const date = now.getDate();
    const monthName = months[now.getMonth()];
    const year = now.getFullYear();

    document.getElementById('clock-date').textContent = `${dayName}, ${date} ${monthName} ${year}`;
}

// Jalankan jam pertama kali
updateClock();
// Update jam setiap detik
setInterval(updateClock, 1000);
