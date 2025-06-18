document.addEventListener('DOMContentLoaded', () => {
  const noradDropdown = document.getElementById('norad-select');
  const unitsContainer = document.getElementById('units-container');
  const socket = io();
  const logList = document.getElementById("log-list");

  let refreshInterval = null;

  function logMessage(message) {
    const entry = document.createElement('div');
    entry.textContent = `🛰️ ${new Date().toLocaleTimeString()} - ${message}`;
    logList.prepend(entry);
  }

  // Fetch NORAD ID list and populate dropdown
  fetch('/api/norad-list')
    .then(response => response.json())
    .then(data => {
      data.forEach(sat => {
        const option = document.createElement('option');
        option.value = sat.norad_cat_id;
        option.textContent = `${sat.norad_cat_id} - ${sat.name}`;
        noradDropdown.appendChild(option);
      });
    })
    .catch(err => {
      console.error("Error fetching NORAD list:", err);
    });

  // Fetch and render satellite info
  function fetchAndRenderSatellite(noradId) {
    if (!noradId) return;

    fetch(`/api/satellite/${noradId}`)
      .then(res => res.json())
      .then(data => {
        unitsContainer.innerHTML = ''; // Clear old cards
        renderSatelliteCard(data);
        logMessage(`Auto-refreshed data for sat_name: ${data.name} NORAD_ID: ${data.norad_cat_id}`);
      })
      .catch(err => {
        console.error("Error fetching satellite data:", err);
        logMessage(`Error fetching data for NORAD_ID: ${noradId}`);
      });
  }

  noradDropdown.addEventListener('change', () => {
    const noradId = noradDropdown.value;
    fetchAndRenderSatellite(noradId);

    if (refreshInterval) clearInterval(refreshInterval);
    refreshInterval = setInterval(() => {
      fetchAndRenderSatellite(noradId);
    }, 60000); // Every 60 seconds
  });

  function renderSatelliteCard(sat) {
    const card = document.createElement('div');
    card.className = 'unit-card';

    card.innerHTML = `
      <h3>${sat.name}</h3>
      <p><strong>NORAD ID:</strong> ${sat.norad_cat_id}</p>
      <p><strong>Status:</strong> ${sat.status}</p>
      <p><strong>Country:</strong> ${sat.countries || 'N/A'}</p>
      <p><strong>Launched:</strong> ${sat.launched || 'Unknown'}</p>
      <p><strong>Operator:</strong> ${sat.operator || 'N/A'}</p>
      ${sat.image ? `<img src="${sat.image}" alt="${sat.name}" style="width: 100%; max-height: 200px; object-fit: contain;">` : ''}
      ${sat.website ? `<p><a href="${sat.website}" target="_blank">More Info</a></p>` : ''}
    `;

    unitsContainer.appendChild(card);
  }

  socket.on("log", (log) => {
    const logItem = document.createElement("div");
    logItem.textContent = log;
    logList.appendChild(logItem);
    logList.scrollTop = logList.scrollHeight;
  });
});
