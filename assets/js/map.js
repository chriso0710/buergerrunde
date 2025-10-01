// Map initialization and configuration
document.addEventListener('DOMContentLoaded', function() {
    // Get location data from JSON script tag
    const locationsData = JSON.parse(document.getElementById('locations-data').textContent);
    
    // Get categories configuration from JSON script tag
    const categoryConfig = JSON.parse(document.getElementById('categories-config').textContent);
    
    // Initialize map centered on Heuweiler
    const map = L.map('map').setView([48.0167, 7.8667], 14);
    
    // Add OpenStreetMap tiles
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);
    
    // Store all markers for filtering
    let allMarkers = [];
    
    // Create markers for each location
    locationsData.forEach(function(location) {
        if (location.latitude && location.longitude) {
            const config = categoryConfig[location.category] || { color: 'gray', icon: 'fas fa-map-marker-alt' };
            
            const customIcon = L.divIcon({
                html: `<div class="custom-marker" style="background-color: ${config.color};" title="${location.title}" data-bs-toggle="tooltip" data-bs-placement="top"><i class="${config.icon}"></i></div>`,
                className: 'custom-div-icon',
                iconSize: [30, 30],
                iconAnchor: [15, 15]
            });
            
            const marker = L.marker([location.latitude, location.longitude], { icon: customIcon });
            
            let popupContent = `<div class="location-popup">
                <h5>${location.title}</h5>
                <p><strong>Kategorie:</strong> ${location.category}</p>`;
            
            if (location.description) {
                popupContent += `<p>${location.description}</p>`;
            }
            
            if (location.address) {
                popupContent += `<p><strong>Adresse:</strong> ${location.address}</p>`;
            }
            
            popupContent += `<p><a href="${location.url}" class="btn btn-sm btn-outline-primary">Mehr Details</a></p>`;
            popupContent += `</div>`;
            
            marker.bindPopup(popupContent);
            marker.addTo(map);
            marker.locationCategory = location.category;
            allMarkers.push(marker);
        }
    });
    
    // Status update function
    function updateFilterStatus() {
        const activeButtons = document.querySelectorAll('[data-category].active');
        const statusElement = document.getElementById('filter-status');
        
        // Update counts for all categories
        updateCategoryCounts();
        
        if (activeButtons.length === 0) {
            statusElement.textContent = '(Alle Orte werden angezeigt)';
        } else if (activeButtons.length === 1) {
            const categoryName = activeButtons[0].getAttribute('data-category');
            if (categoryName === 'all') {
                statusElement.textContent = '(Alle Orte werden angezeigt)';
            } else {
                statusElement.textContent = `(Filter aktiv: ${categoryName})`;
            }
        } else {
            statusElement.textContent = `(${activeButtons.length} Filter aktiv)`;
        }
    }
    
    // Function to update category counts
    function updateCategoryCounts() {
        // Count total locations
        const totalCount = allMarkers.length;
        const allCountElement = document.getElementById('count-all');
        if (allCountElement) {
            allCountElement.textContent = totalCount;
        }
        
        // Count locations per category
        const categoryCounts = {};
        allMarkers.forEach(marker => {
            const category = marker.locationCategory;
            categoryCounts[category] = (categoryCounts[category] || 0) + 1;
        });
        
        // Update count badges for each category by finding the button and its badge
        const filterButtons = document.querySelectorAll('[data-category]:not([data-category="all"])');
        filterButtons.forEach(button => {
            const categoryName = button.getAttribute('data-category');
            const count = categoryCounts[categoryName] || 0;
            const badge = button.querySelector('.badge');
            if (badge) {
                badge.textContent = count;
            }
        });
    }
    
    // Simple toggle filter functionality
    const filterButtons = document.querySelectorAll('[data-category]');
    
    filterButtons.forEach(function(button) {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            
            const category = this.getAttribute('data-category');
            console.log('Button clicked:', category, 'Has active class:', this.classList.contains('active'));
            
            if (category === 'all') {
                // "Alle anzeigen" - alle anderen Filter deaktivieren
                filterButtons.forEach(btn => {
                    btn.classList.remove('active', 'btn-primary', 'btn-success');
                    if (btn.getAttribute('data-category') === 'all') {
                        btn.classList.add('btn-success', 'active');
                        btn.classList.remove('btn-outline-success');
                    } else {
                        btn.classList.add('btn-outline-primary');
                        btn.classList.remove('btn-primary');
                    }
                });
                
                // Alle Marker anzeigen
                allMarkers.forEach(marker => {
                    if (!map.hasLayer(marker)) {
                        map.addLayer(marker);
                    }
                });
                
            } else {
                // Einfacher Toggle für andere Buttons
                const isCurrentlyActive = this.classList.contains('active');
                
                if (isCurrentlyActive) {
                    // Button deaktivieren
                    this.classList.remove('btn-primary', 'active');
                    this.classList.add('btn-outline-primary');
                } else {
                    // Button aktivieren
                    this.classList.remove('btn-outline-primary');
                    this.classList.add('btn-primary', 'active');
                }
                
                console.log('After toggle, has active class:', this.classList.contains('active'));
                
                // "Alle anzeigen" Button deaktivieren
                const allButton = document.querySelector('[data-category="all"]');
                allButton.classList.remove('btn-success', 'active');
                allButton.classList.add('btn-outline-success');
                
                // Aktive Kategorien sammeln
                const activeButtons = document.querySelectorAll('[data-category]:not([data-category="all"]).active');
                const activeCategories = Array.from(activeButtons).map(btn => btn.getAttribute('data-category'));
                
                console.log('Active categories:', activeCategories);
                
                // Marker-Sichtbarkeit aktualisieren
                if (activeCategories.length === 0) {
                    // Keine Filter aktiv - alle anzeigen und "Alle" aktivieren
                    allMarkers.forEach(marker => {
                        if (!map.hasLayer(marker)) {
                            map.addLayer(marker);
                        }
                    });
                    allButton.classList.remove('btn-outline-success');
                    allButton.classList.add('btn-success', 'active');
                } else {
                    // Nur aktive Kategorien anzeigen
                    allMarkers.forEach(marker => {
                        const shouldShow = activeCategories.includes(marker.locationCategory);
                        
                        if (shouldShow) {
                            if (!map.hasLayer(marker)) {
                                map.addLayer(marker);
                            }
                        } else {
                            if (map.hasLayer(marker)) {
                                map.removeLayer(marker);
                            }
                        }
                    });
                }
            }
            
            updateFilterStatus();
        });
    });
    
    // Initial status
    updateFilterStatus();
    
    // Initialize Bootstrap tooltips for map markers
    setTimeout(() => {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('.custom-marker[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function(tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }, 100);
    
    // Fit map bounds
    if (allMarkers.length > 0) {
        const group = new L.featureGroup(allMarkers);
        map.fitBounds(group.getBounds().pad(0.1));
    }
});