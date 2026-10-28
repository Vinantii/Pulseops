const $ = (selector) => document.querySelector(selector);

async function fetchJSON(url) {
    const response = await fetch(url, { cache: "no-store" });

    if (!response.ok) {
        throw new Error(`Request failed: ${url} (status ${response.status})`);
    }

    return response.json();
}

function formatDate(value) {
    if (!value) return "—";

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) return String(value);

    return date.toLocaleString();
}

function formatPercent(value) {
    const number = Number(value);

    return Number.isFinite(number)
        ? `${number.toFixed(1)}%`
        : "—";
}

function setProgressBar(id, value, isWarning = false) {
    const element = $(id);
    if (!element) return;

    const number = Number(value);
    element.style.width = Number.isFinite(number)
        ? `${Math.min(100, Math.max(0, number))}%`
        : "0%";

    element.classList.toggle("warning", Boolean(isWarning));
}

function updateStatus(state) {
    if (!state) return;

    const status = String(state.status || "UNKNOWN").toUpperCase();
    const statusElement = $("#serviceStatus");
    if (statusElement) {
        statusElement.textContent = status;
        statusElement.className = `status-pill ${status.toLowerCase()}`;
    }

    const serviceName = $("#serviceName");
    if (serviceName) {
        serviceName.textContent = state.service || "DemoApp";
    }

    const healthDetail = $("#healthDetail");
    if (healthDetail) {
        if (state.health === "OK") {
            healthDetail.textContent = "Health check OK · 0 failures";
        } else if (state.health === "FAILED") {
            const count = state.consecutive_failures ?? 0;
            healthDetail.textContent = `Health check FAILED · ${count} failure${count === 1 ? "" : "s"}`;
        } else {
            healthDetail.textContent = "Waiting for first monitor reading";
        }
    }

    const cpu = Number(state.cpu) || 0;
    const memory = Number(state.memory) || 0;
    const disk = Number(state.disk) || 0;

    const cpuWarning = cpu >= 85;
    const memWarning = memory >= 85;
    const diskWarning = disk >= 90;

    $("#cpuValue").textContent = formatPercent(cpu);
    $("#memoryValue").textContent = formatPercent(memory);
    $("#diskValue").textContent = formatPercent(disk);

    $("#cpuValue").classList.toggle("warning", cpuWarning);
    $("#memoryValue").classList.toggle("warning", memWarning);
    $("#diskValue").classList.toggle("warning", diskWarning);

    $("#cpuCard").classList.toggle("warning", cpuWarning);
    $("#memoryCard").classList.toggle("warning", memWarning);
    $("#diskCard").classList.toggle("warning", diskWarning);

    const cpuState = $("#cpuState");
    const memState = $("#memoryState");
    const diskState = $("#diskState");

    cpuState.textContent = cpuWarning ? "Warning: CPU >= 85%" : "System CPU usage";
    memState.textContent = memWarning ? "Warning: RAM >= 85%" : "System RAM usage";
    diskState.textContent = diskWarning ? "Warning: Disk >= 90%" : "System disk usage";

    cpuState.classList.toggle("warning", cpuWarning);
    memState.classList.toggle("warning", memWarning);
    diskState.classList.toggle("warning", diskWarning);

    setProgressBar("#cpuBar", cpu, cpuWarning);
    setProgressBar("#memoryBar", memory, memWarning);
    setProgressBar("#diskBar", disk, diskWarning);

    $("#lastUpdated").textContent =
        state.updated_at
            ? formatDate(state.updated_at)
            : "No readings yet";
}

function updateSummary(summary) {
    if (!summary) return;

    $("#totalIncidents").textContent = summary.total ?? 0;
    $("#openCount").textContent = summary.open ?? 0;
    $("#recoveredCount").textContent = summary.recovered ?? 0;
    $("#unresolvedCount").textContent = summary.unresolved ?? 0;
}

function renderIncidents(incidents) {
    const tbody = $("#incidentRows");
    tbody.replaceChildren();

    if (!incidents || !incidents.length) {
        const row = document.createElement("tr");
        const cell = document.createElement("td");

        cell.colSpan = 7;
        cell.className = "empty-state";
        cell.textContent = "No incidents recorded yet.";

        row.appendChild(cell);
        tbody.appendChild(row);
        return;
    }

    for (const incident of incidents) {
        const row = document.createElement("tr");

        const incidentCode =
            incident.incident_code ||
            `INC-${String(incident.id || 0).padStart(4, "0")}`;

        const values = [
            incidentCode,
            incident.service ?? "DemoApp",
            incident.failure_type ?? "Unknown",
            formatDate(incident.detected_at),
            incident.recovery_attempts ?? 0,
            formatDate(incident.resolved_at),
        ];

        values.forEach((value, index) => {
            const cell = document.createElement("td");
            cell.textContent = value ?? "—";

            if (index === 0) {
                cell.className = "incident-id";
            }

            row.appendChild(cell);
        });

        const statusCell = document.createElement("td");
        const badge = document.createElement("span");
        const status = String(incident.status || "OPEN").toUpperCase();

        badge.className = `table-status ${status.toLowerCase()}`;
        badge.textContent = status;

        statusCell.appendChild(badge);
        row.appendChild(statusCell);
        tbody.appendChild(row);
    }
}

function drawChart(metrics) {
    const canvas = $("#metricsChart");
    if (!canvas) return;

    const container = canvas.parentElement;
    const width = container.clientWidth || 800;
    const height = 260;
    const ratio = window.devicePixelRatio || 1;

    canvas.width = width * ratio;
    canvas.height = height * ratio;

    const context = canvas.getContext("2d");
    context.setTransform(ratio, 0, 0, ratio, 0, 0);
    context.clearRect(0, 0, width, height);

    const padding = { top: 16, right: 18, bottom: 28, left: 42 };
    const chartWidth = Math.max(10, width - padding.left - padding.right);
    const chartHeight = Math.max(10, height - padding.top - padding.bottom);

    context.font = "11px -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif";
    context.textAlign = "right";
    context.textBaseline = "middle";

    // Horizontal percentage grid (0%, 25%, 50%, 75%, 100%)
    for (let value = 0; value <= 100; value += 25) {
        const y = padding.top + chartHeight * (1 - value / 100);

        context.beginPath();
        context.strokeStyle = "#202d42";
        context.lineWidth = 1;
        context.moveTo(padding.left, y);
        context.lineTo(width - padding.right, y);
        context.stroke();

        context.fillStyle = "#91a2ba";
        context.fillText(`${value}%`, padding.left - 8, y);
    }

    if (!metrics || !metrics.length) {
        context.fillStyle = "#91a2ba";
        context.textAlign = "center";
        context.font = "13px -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif";
        context.fillText(
            "Waiting for historical resource measurements...",
            width / 2,
            height / 2
        );
        return;
    }

    const series = [
        { key: "cpu", color: "#55d6be" },
        { key: "memory", color: "#66a8ff" },
        { key: "disk", color: "#b39aff" },
    ];

    for (const item of series) {
        const points = [];

        context.beginPath();
        context.strokeStyle = item.color;
        context.lineWidth = 2.5;
        context.lineJoin = "round";
        context.lineCap = "round";

        metrics.forEach((measurement, index) => {
            const x = padding.left +
                (metrics.length === 1
                    ? chartWidth / 2
                    : (index * chartWidth) / (metrics.length - 1));

            const rawVal = Number(measurement[item.key]) || 0;
            const value = Math.min(100, Math.max(0, rawVal));
            const y = padding.top + chartHeight * (1 - value / 100);

            points.push({ x, y });

            if (index === 0) {
                context.moveTo(x, y);
            } else {
                context.lineTo(x, y);
            }
        });

        context.stroke();

        // Draw point dots
        context.fillStyle = item.color;
        for (const pt of points) {
            context.beginPath();
            context.arc(pt.x, pt.y, metrics.length > 20 ? 2 : 3, 0, Math.PI * 2);
            context.fill();
        }
    }
}

async function refreshDashboard() {
    try {
        const [status, summary, incidents, metrics] = await Promise.all([
            fetchJSON("/api/status"),
            fetchJSON("/api/summary"),
            fetchJSON("/api/incidents"),
            fetchJSON("/api/metrics"),
        ]);

        updateStatus(status);
        updateSummary(summary);
        renderIncidents(incidents);
        drawChart(metrics);

        const errorBanner = $("#dashboardError");
        if (errorBanner) {
            errorBanner.hidden = true;
        }
    } catch (error) {
        console.error("Dashboard refresh failed:", error);

        const errorBanner = $("#dashboardError");
        if (errorBanner) {
            errorBanner.textContent =
                "Unable to load dashboard data. Check that the database and PulseOps Flask server are available.";
            errorBanner.hidden = false;
        }
    }
}

// Initial fetch on page load
refreshDashboard();

// Auto refresh every 5 seconds
setInterval(refreshDashboard, 5000);

// Redraw chart on window resize
window.addEventListener("resize", async () => {
    try {
        const metrics = await fetchJSON("/api/metrics");
        drawChart(metrics);
    } catch (error) {
        console.error("Chart resize failed:", error);
    }
});
