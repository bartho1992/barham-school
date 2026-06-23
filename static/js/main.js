document.addEventListener('DOMContentLoaded', function() {
    // Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });

    // tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
      return new bootstrap.Tooltip(tooltipTriggerEl)
    })

    // Student search for documents
    const searchInput = document.getElementById('search-eleve');
    const searchResults = document.getElementById('search-results');
    
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            const q = this.value;
            if (q.length < 2) {
                searchResults.innerHTML = '';
                return;
            }
            
            fetch(`/api/eleves/search?q=${q}`)
                .then(response => response.json())
                .then(data => {
                    searchResults.innerHTML = '';
                    data.forEach(el => {
                        const div = document.createElement('div');
                        div.className = 'list-group-item list-group-item-action cursor-pointer p-2 border rounded mb-1';
                        div.style.cursor = 'pointer';
                        div.innerHTML = `<strong>${el.prenom} ${el.nom}</strong> <br> <small>${el.classe} | ${el.code}</small>`;
                        div.addEventListener('click', () => selectEleve(el));
                        searchResults.appendChild(div);
                    });
                });
        });
    }
});

function selectEleve(el) {
    document.getElementById('search-eleve').value = `${el.prenom} ${el.nom}`;
    document.getElementById('search-results').innerHTML = '';
    
    // Update links in document cards
    const routes = {
        'certificat': `/documents/certificat/${el.id}`,
        'carte': `/documents/carte/${el.id}`,
        'entree': `/documents/billet_entree/${el.id}`,
        'sortie': `/documents/billet_sortie/${el.id}`,
        'renvoi': `/documents/billet_renvoi/${el.id}`,
        'demeure': `/documents/mise_en_demeure/${el.id}`
    };
    
    // This assumes we add IDs to the cards in index.html
    const cards = document.querySelectorAll('.doc-card');
    cards.forEach(card => {
        const type = card.dataset.type;
        if (routes[type]) {
            card.href = routes[type];
            card.classList.remove('disabled');
            card.querySelector('small').innerText = `Eleve: ${el.prenom} ${el.nom}`;
        }
    });
}
