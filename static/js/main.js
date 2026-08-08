document.addEventListener('DOMContentLoaded', function() {
    // --- Vue carte sur mobile : auto data-labels ---
    function initCardView() {
        if (window.innerWidth <= 768) {
            document.querySelectorAll('.table-card-view').forEach(function(table) {
                table.querySelectorAll('tbody tr').forEach(function(row) {
                    row.querySelectorAll('td').forEach(function(td, idx) {
                        if (!td.hasAttribute('data-label') && !td.classList.contains('td-check') && !td.classList.contains('td-actions')) {
                            var th = table.querySelectorAll('thead th')[idx];
                            if (th) td.setAttribute('data-label', th.textContent.trim());
                        }
                    });
                });
            });
        }
    }
    initCardView();
    window.addEventListener('resize', initCardView);

    // --- Validation téléphone et email ---
    document.querySelectorAll('input[data-validate="phone"]').forEach(function(input) {
        input.addEventListener('input', function() {
            var val = this.value.replace(/[^0-9+\- ]/g, '');
            this.value = val;
            this.classList.toggle('is-invalid', val.length > 0 && val.replace(/[^0-9]/g, '').length < 8);
        });
        input.addEventListener('blur', function() {
            var digits = this.value.replace(/[^0-9]/g, '');
            if (this.value.length > 0 && digits.length < 8) {
                this.classList.add('is-invalid');
            } else {
                this.classList.remove('is-invalid');
            }
        });
    });
    document.querySelectorAll('input[data-validate="email"]').forEach(function(input) {
        input.addEventListener('blur', function() {
            var re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (this.value.length > 0 && !re.test(this.value)) {
                this.classList.add('is-invalid');
            } else {
                this.classList.remove('is-invalid');
            }
        });
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
