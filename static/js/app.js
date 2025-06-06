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
    
    // Ne rien faire pour saveNewNicheBtn car il est géré ailleurs
    // Ce bouton a été supprimé, mais nous gardons le commentaire pour référence

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
        
        // Create elements safely without using innerHTML
        const wrapper = document.createElement('div');
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
        alertDiv.setAttribute('role', 'alert');
        
        // Create text node for the message (prevents script execution)
        const messageNode = document.createTextNode(message);
        alertDiv.appendChild(messageNode);
        
        // Create close button
        const closeButton = document.createElement('button');
        closeButton.className = 'btn-close';
        closeButton.setAttribute('type', 'button');
        closeButton.setAttribute('data-bs-dismiss', 'alert');
        closeButton.setAttribute('aria-label', 'Close');
        
        // Assemble the elements
        alertDiv.appendChild(closeButton);
        wrapper.appendChild(alertDiv);
        alertPlaceholder.append(wrapper);
        
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            const alert = bootstrap.Alert.getOrCreateInstance(alertDiv);
            alert.close();
        }, 5000);
    }
});
