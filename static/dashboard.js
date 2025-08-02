class SmartFarmDashboard {
    constructor() {
        this.charts = {};
        this.data = {
            temperature: [],
            humidity: [],
            soil: [],
            timestamps: []
        };
        this.maxDataPoints = 20;
        this.currentMode = 'manual';
        
        this.init();
    }

    // Initialize the dashboard by setting up charts, event listeners, and data fetching
    init() {
        this.initCharts();
        this.initEventListeners();
        this.startDataFetching();
    }

    initCharts() {
        // Temperature & Humidity Chart
        const tempHumCtx = document.getElementById('tempHumChart').getContext('2d');
        this.charts.tempHum = new Chart(tempHumCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Temperature (°C)',
                    data: [],
                    borderColor: '#e74c3c',
                    backgroundColor: 'rgba(231, 76, 60, 0.1)',
                    tension: 0.4,
                    fill: false
                }, {
                    label: 'Humidity (%)',
                    data: [],
                    borderColor: '#3498db',
                    backgroundColor: 'rgba(52, 152, 219, 0.1)',
                    tension: 0.4,
                    fill: false
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(0,0,0,0.1)'
                        }
                    },
                    x: {
                        grid: {
                            color: 'rgba(0,0,0,0.1)'
                        }
                    }
                },
                plugins: {
                    legend: {
                        position: 'top'
                    }
                }
            }
        });

        // Soil Moisture Chart
        const soilCtx = document.getElementById('soilChart').getContext('2d');
        this.charts.soil = new Chart(soilCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Soil Moisture (%)',
                    data: [],
                    borderColor: '#27ae60',
                    backgroundColor: 'rgba(39, 174, 96, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        grid: {
                            color: 'rgba(0,0,0,0.1)'
                        }
                    },
                    x: {
                        grid: {
                            color: 'rgba(0,0,0,0.1)'
                        }
                    }
                },
                plugins: {
                    legend: {
                        position: 'top'
                    }
                }
            }
        });
    }

    initEventListeners() {
        // Mode selector
        const modeRadios = document.querySelectorAll('input[name="mode"]');
        modeRadios.forEach(radio => {
            radio.addEventListener('change', (e) => {
                this.changeMode(e.target.value);
            });
        });

        // Pump button
        document.getElementById('pump-btn').addEventListener('click', () => {
            this.togglePump();
        });
    }

    // Change pump mode
    async changeMode(mode) {
        try {
            const response = await fetch('/api/pump', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    action: 'set_mode',
                    mode: mode
                })
            });

            const result = await response.json();
            if (result.status === 'ok') {
                this.currentMode = mode;
                this.updatePumpButton();
                document.getElementById('pump-mode').textContent = 
                    mode.charAt(0).toUpperCase() + mode.slice(1);
            }
        } catch (error) {
            console.error('Error changing mode:', error);
        }
    }

    // Toggle pump state
    async togglePump() {
        if (this.currentMode !== 'manual') return;

        try {
            const response = await fetch('/api/pump', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    action: 'toggle'
                })
            });

            const result = await response.json();
            if (result.status === 'ok') {
                this.updatePumpStatus(result.pump);
            }
        } catch (error) {
            console.error('Error toggling pump:', error);
        }
    }

    // Update pump button based on current mode
    updatePumpButton() {
        const pumpBtn = document.getElementById('pump-btn');
        
        if (this.currentMode === 'auto') {
            pumpBtn.disabled = true;
            pumpBtn.innerHTML = '<span class="pump-icon">🤖</span><span class="pump-text">Auto Mode</span>';
        } else {
            pumpBtn.disabled = false;
            const currentState = document.getElementById('pump-status').textContent.toLowerCase();
            this.updatePumpStatus(currentState);
        }
    }

    // Update pump status display
    updatePumpStatus(state) {
        const pumpBtn = document.getElementById('pump-btn');
        const pumpStatus = document.getElementById('pump-status');
        
        pumpStatus.textContent = state.toUpperCase();
        
        if (this.currentMode === 'manual') {
            if (state === 'on') {
                pumpBtn.className = 'pump-button on';
                pumpBtn.innerHTML = '<span class="pump-icon">⏹️</span><span class="pump-text">Turn OFF</span>';
            } else {
                pumpBtn.className = 'pump-button off';
                pumpBtn.innerHTML = '<span class="pump-icon">▶️</span><span class="pump-text">Turn ON</span>';
            }
        }
    }

    // Fetch data from server
    async fetchData() {
        try {
            const response = await fetch('/api/data');
            const data = await response.json();
            
            this.updateSensorDisplay(data);
            this.updateCharts(data);
            
            // Update mode if changed from server
            if (data.mode !== this.currentMode) {
                this.currentMode = data.mode;
                document.querySelector(`input[value="${data.mode}"]`).checked = true;
                document.getElementById('pump-mode').textContent = 
                    data.mode.charAt(0).toUpperCase() + data.mode.slice(1);
                this.updatePumpButton();
            }
            
            this.updatePumpStatus(data.pump);
            
        } catch (error) {
            console.error('Error fetching data:', error);
        }
    }

    // Update sensor display with fetched data
    updateSensorDisplay(data) {
        document.getElementById('temperature').textContent = 
            data.temperature !== null ? data.temperature : '--';
        document.getElementById('humidity').textContent = 
            data.humidity !== null ? data.humidity : '--';
        document.getElementById('soil').textContent = 
            data.soil_percent !== null ? data.soil_percent : '--';
    }

    // Update charts with new data
    updateCharts(data) {
        const now = new Date().toLocaleTimeString();
        
        // Add new data
        this.data.timestamps.push(now);
        this.data.temperature.push(data.temperature);
        this.data.humidity.push(data.humidity);
        this.data.soil.push(data.soil_percent);
        
        // Remove old data if exceeding max points
        if (this.data.timestamps.length > this.maxDataPoints) {
            this.data.timestamps.shift();
            this.data.temperature.shift();
            this.data.humidity.shift();
            this.data.soil.shift();
        }
        
        // Update charts
        this.charts.tempHum.data.labels = [...this.data.timestamps];
        this.charts.tempHum.data.datasets[0].data = [...this.data.temperature];
        this.charts.tempHum.data.datasets[1].data = [...this.data.humidity];
        this.charts.tempHum.update('none');
        
        this.charts.soil.data.labels = [...this.data.timestamps];
        this.charts.soil.data.datasets[0].data = [...this.data.soil];
        this.charts.soil.update('none');
    }

    // Start fetching data periodically
    startDataFetching() {
        this.fetchData(); 
        setInterval(() => {
            this.fetchData();
        }, 2000); 
    }
}

// Initialize dashboard when page loads
document.addEventListener('DOMContentLoaded', () => {
    new SmartFarmDashboard();
});
