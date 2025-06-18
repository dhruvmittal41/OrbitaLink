document.addEventListener("DOMContentLoaded", () => {
  const socket = io();

  const satelliteSelect = document.getElementById("satellite-select");
  const unitsContainer = document.getElementById("units-container");
  const serverStatus = document.getElementById("server-status");
  const logList = document.getElementById("log-list");

  if (!satelliteSelect || !unitsContainer || !serverStatus || !logList) {
    console.error("One or more DOM elements not found. Check HTML IDs.");
    return;
  }

  // 🔹 Update server status on connect
  socket.on("connect", () => {
    serverStatus.textContent = "Connected";
    serverStatus.style.color = "green";
    socket.emit("get_satellite_list");
  });

  // 🔹 Populate satellite dropdown
  socket.on("satellite_list", (sats) => {
    satelliteSelect.innerHTML = "";
    sats.forEach((sat) => {
      const option = document.createElement("option");
      option.value = sat.id;
      option.textContent = sat.name;
      satelliteSelect.appendChild(option);
    });

    // 🔹 Auto-fetch data for first satellite
    if (sats.length > 0) {
      socket.emit("get_satellite_data", sats[0].id);
    }
  });

  // 🔹 On user change
  satelliteSelect.addEventListener("change", () => {
    const selectedId = satelliteSelect.value;
    socket.emit("get_satellite_data", selectedId);
  });

  // 🔹 Render satellite client data
  socket.on("client_data_update", (data) => {
    unitsContainer.innerHTML = "";

    const client = data.clients[0];
    if (!client) return;

    const card = document.createElement("div");
    card.className = "unit-card";
    card.style = "background:#fff;border:1px solid #ccc;border-radius:8px;padding:1rem;margin:1rem;box-shadow:0 2px 5px rgba(0,0,0,0.05);";

    card.innerHTML = `
      <h2>Satellite: ${client.name}</h2>
      <p><strong>IP:</strong> ${client.ip}</p>
      <p><strong>Lat:</strong> ${client.lat}</p>
      <p><strong>Lon:</strong> ${client.lon}</p>
      <p><strong>TLE Line 1:</strong> ${client.tle_line1}</p>
      <p><strong>TLE Line 2:</strong> ${client.tle_line2}</p>
      <p><strong>Azimuth:</strong> ${client.az}°</p>
      <p><strong>Elevation:</strong> ${client.el}°</p>
      <p><strong>Time:</strong> ${client.time}</p>
      <p><strong>Temp:</strong> ${client.temp}°C</p>
      <p><strong>Humidity:</strong> ${client.humidity}%</p>
    `;
    unitsContainer.appendChild(card);
  });

  // 🔹 Log stream
  socket.on("log", (log) => {
    const logItem = document.createElement("div");
    logItem.textContent = log;
    logList.appendChild(logItem);
    logList.scrollTop = logList.scrollHeight;
  });
});
