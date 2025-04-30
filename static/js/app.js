document.addEventListener('DOMContentLoaded', function() {
    // Utilitaire pour ajouter des écouteurs d'événements de manière sécurisée
    function addSafeEventListener(elementId, eventType, callback) {
        const element = document.getElementById(elementId);
        if (element) {
            element.addEventListener(eventType, callback);
        }
    }
    // Initialize Bootstrap tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    });

    // Initialize Bootstrap popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'))
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl)
    });
    
    // Gestion sécurisée du bouton de sauvegarde de niche (s'il existe)
    addSafeEventListener('saveNewNicheBtn', 'click', function() {
        // Logique de sauvegarde de niche si nécessaire
    });

    // Handle boutique form submission
    const boutiqueForm = document.getElementById('boutique-form');
    if (boutiqueForm) {
        boutiqueForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = {
                name: document.getElementById('boutique-name').value,
                description: document.getElementById('boutique-description').value,
                target_demographic: document.getElementById('target-demographic').value
            };
            
            fetch('/api/boutiques', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(formData),
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // Show success message
                    showAlert('Boutique added successfully!', 'success');
                    // Reset form
                    boutiqueForm.reset();
                    // Refresh the page after a short delay
                    setTimeout(() => {
                        window.location.reload();
                    }, 1500);
                } else {
                    showAlert('Error: ' + data.error, 'danger');
                }
            })
            .catch((error) => {
                showAlert('Error: ' + error, 'danger');
            });
        });
    }

    // Handle niche form submission
    const nicheForm = document.getElementById('niche-form');
    if (nicheForm) {
        nicheForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = {
                name: document.getElementById('niche-name').value,
                description: document.getElementById('niche-description').value,
                key_characteristics: document.getElementById('key-characteristics').value
            };
            
            fetch('/api/niches', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(formData),
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // Show success message
                    showAlert('Niche market added successfully!', 'success');
                    // Reset form
                    nicheForm.reset();
                    // Refresh the page after a short delay
                    setTimeout(() => {
                        window.location.reload();
                    }, 1500);
                } else {
                    showAlert('Error: ' + data.error, 'danger');
                }
            })
            .catch((error) => {
                showAlert('Error: ' + error, 'danger');
            });
        });
    }

    // Handle persona generation buttons
    const personaButtons = document.querySelectorAll('.generate-persona-btn');
    personaButtons.forEach(button => {
        button.addEventListener('click', function() {
            const profileIndex = this.getAttribute('data-profile-index');
            const personaContainer = document.getElementById('persona-' + profileIndex);
            const loadingSpinner = this.querySelector('.spinner-border');
            const buttonText = this.querySelector('.btn-text');
            
            // Show loading state
            if (loadingSpinner) loadingSpinner.classList.remove('d-none');
            if (buttonText) buttonText.textContent = 'Generating...';
            this.disabled = true;
            
            fetch('/generate_persona/' + profileIndex, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    if (personaContainer) {
                        personaContainer.textContent = data.persona;
                        personaContainer.classList.remove('text-muted');
                    }
                    // Show success message
                    showAlert('Persona generated successfully!', 'success');
                } else {
                    showAlert('Error: ' + data.error, 'danger');
                }
            })
            .catch(error => {
                showAlert('Error: ' + error, 'danger');
            })
            .finally(() => {
                // Restore button state
                if (loadingSpinner) loadingSpinner.classList.add('d-none');
                if (buttonText) buttonText.textContent = 'Generate Persona';
                this.disabled = false;
            });
        });
    });

    // Function to display alerts
    function showAlert(message, type = 'info') {
        const alertPlaceholder = document.getElementById('alert-placeholder');
        if (!alertPlaceholder) return;
        
        const wrapper = document.createElement('div');
        wrapper.innerHTML = `
            <div class="alert alert-${type} alert-dismissible fade show" role="alert">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
        `;
        
        alertPlaceholder.append(wrapper);
        
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            const alert = bootstrap.Alert.getOrCreateInstance(wrapper.querySelector('.alert'));
            alert.close();
        }, 5000);
    }
});
