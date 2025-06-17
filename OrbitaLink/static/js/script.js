document.addEventListener("DOMContentLoaded", () => {
  const socket = io();

  const clientList = document.getElementById("client-list");
  const serverList = document.getElementById("server-list");
  const clientSelect = document.getElementById("client-select");
  const serverSelect = document.getElementById("server-select");
  const canvas = document.getElementById("lineCanvas");
  const ctx = canvas.getContext("2d");

  let manualConnections = [];

  function updateList(ul, items) {
    ul.innerHTML = items.map(item => `<li>${item}</li>`).join("");
  }

  function updateDropdown(clients, servers) {
    clientSelect.innerHTML = '<option disabled selected>Select Client</option>' +
      clients.map(c => `<option value="${c}">${c}</option>`).join("");
    serverSelect.innerHTML = '<option disabled selected>Select Server</option>' +
      servers.map(s => `<option value="${s}">${s}</option>`).join("");
  }

  function drawConnections() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const bounds = canvas.getBoundingClientRect();

    manualConnections.forEach(pair => {
      const clientLi = Array.from(clientList.children).find(li => li.textContent === pair.client);
      const serverLi = Array.from(serverList.children).find(li => li.textContent === pair.server);

      if (clientLi && serverLi) {
        const c = clientLi.getBoundingClientRect();
        const s = serverLi.getBoundingClientRect();

        const x1 = c.right - bounds.left;
        const y1 = c.top + c.height / 2 - bounds.top;
        const x2 = s.left - bounds.left;
        const y2 = s.top + s.height / 2 - bounds.top;

        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.strokeStyle = "#00cc66";
        ctx.lineWidth = 2;
        ctx.stroke();
      }
    });
  }

  function connectSelected() {
  const client = clientSelect.value;
  const server = serverSelect.value;

  if (!client || !server || client === server) {
    alert("Please select both client and server");
    return;
  }

  const serverPort = {
    "Server 1": 5001,
    "Server 2": 5002,
    "Server 3": 5003
  }[server];

  if (!serverPort) {
    alert("Unknown server selected");
    return;
  }

  console.log(`🔗 Connecting client "${client}" to server "${server}" (port ${serverPort})`);

  fetch("/set_server_for_client", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ client, port: serverPort })
  }).then(() => {
    manualConnections.push({ client, server });
    drawConnections();
  });
}


  fetch('/get_connections')
    .then(res => res.json())
    .then(data => {
      updateList(clientList, data.clients);
      updateList(serverList, data.servers);
      updateDropdown(data.clients, data.servers);
    });

  socket.on("connect", () => console.log("Socket connected"));

  socket.on("status_update", (data) => {
    updateList(clientList, data.clients || []);
    updateList(serverList, data.servers || []);
    updateDropdown(data.clients || [], data.servers || []);
    drawConnections();
  });

  document.getElementById("connect-btn").addEventListener("click", function () {
    const client = clientSelect.value;
    const server = serverSelect.value;
    if (client && server) {
      fetch("/register_activity", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ client, server })
      });
    }
    connectSelected();
  });
});
