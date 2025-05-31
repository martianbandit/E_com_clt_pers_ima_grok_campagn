// MarkEasy - Animations et interactions modernes

document.addEventListener('DOMContentLoaded', function() {
    // Animation d'apparition au scroll
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
            }
        });
    }, observerOptions);

    // Observer tous les éléments avec la classe fade-in-up
    document.querySelectorAll('.fade-in-up').forEach(el => {
        observer.observe(el);
    });

    // Toggle pour les prix annuels/mensuels
    const billingToggle = document.getElementById('billingToggle');
    if (billingToggle) {
        billingToggle.addEventListener('change', function() {
            const monthlyElements = document.querySelectorAll('.monthly-price, .monthly-btn');
            const annualElements = document.querySelectorAll('.annual-price, .annual-btn');
            
            if (this.checked) {
                // Afficher les prix annuels
                monthlyElements.forEach(el => el.classList.add('d-none'));
                annualElements.forEach(el => el.classList.remove('d-none'));
            } else {
                // Afficher les prix mensuels
                monthlyElements.forEach(el => el.classList.remove('d-none'));
                annualElements.forEach(el => el.classList.add('d-none'));
            }
        });
    }

    // Smooth scroll pour les liens d'ancre
    document.querySelectorAll('a[href^="\\#"]').forEach(link => {
        link.addEventListener('click', function(e) {
            const targetId = this.getAttribute('href');
            const targetElement = document.querySelector(targetId);
            
            if (targetElement) {
                e.preventDefault();
                targetElement.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // Animation de compteur pour les statistiques
    function animateCounters() {
        const counters = document.querySelectorAll('[data-count]');
        
        counters.forEach(counter => {
            const target = parseInt(counter.dataset.count);
            const duration = 2000; // 2 secondes
            const increment = target / (duration / 16); // 60 FPS
            let current = 0;
            
            const timer = setInterval(() => {
                current += increment;
                if (current >= target) {
                    current = target;
                    clearInterval(timer);
                }
                counter.textContent = Math.floor(current);
            }, 16);
        });
    }

    // Déclencher les animations de compteur quand la section est visible
    const statsSection = document.querySelector('.stats-section');
    if (statsSection) {
        const statsObserver = new IntersectionObserver(function(entries) {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    animateCounters();
                    statsObserver.unobserve(entry.target);
                }
            });
        }, { threshold: 0.5 });
        
        statsObserver.observe(statsSection);
    }

    // Effet de parallaxe léger pour le hero
    window.addEventListener('scroll', function() {
        const scrolled = window.pageYOffset;
        const heroSection = document.querySelector('.hero-section');
        
        if (heroSection && scrolled < window.innerHeight) {
            heroSection.style.transform = `translateY(${scrolled * 0.5}px)`;
        }
    });

    // Animation des cartes au survol
    document.querySelectorAll('.feature-card, .testimonial-card, .pricing-card').forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-5px) scale(1.02)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0) scale(1)';
        });
    });
});