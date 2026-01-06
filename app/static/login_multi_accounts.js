/**
 * Gestion du login avec support multi-comptes (événements multiples)
 * 
 * À intégrer dans les pages de login (index.html, photographer.html, admin.html)
 * 
 * Usage:
 *   Remplacer la fonction login() existante par celle-ci
 */

async function loginWithMultiAccountSupport(username, password) {
    try {
        const response = await fetch('/api/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ username, password }),
        });

        const data = await response.json();

        // Cas 1: Login normal (un seul compte)
        if (response.ok && data.access_token) {
            localStorage.setItem('token', data.access_token);
            
            // Redirection selon le type (à adapter selon la page)
            // Pour index.html: window.location.href = '/gallery';
            // Pour photographer.html: charger le dashboard photographe
            // Pour admin.html: charger le dashboard admin
            
            return { success: true, token: data.access_token };
        }
        
        // Cas 2: Plusieurs comptes détectés
        if (response.ok && data.multiple_accounts) {
            // Stocker les infos dans sessionStorage
            sessionStorage.setItem('login_accounts', JSON.stringify({
                accounts: data.accounts,
                credentials: { username, password }
            }));
            
            // Rediriger vers la page de sélection
            window.location.href = '/select-event';
            
            return { success: true, multipleAccounts: true };
        }
        
        // Cas 3: Erreur (mauvais mdp, etc.)
        return { 
            success: false, 
            error: data.detail || 'Erreur de connexion' 
        };
        
    } catch (error) {
        console.error('Erreur login:', error);
        return { success: false, error: 'Erreur de connexion' };
    }
}

// ============================================================================
// EXEMPLE D'INTÉGRATION dans index.html, photographer.html, admin.html
// ============================================================================

/*

// REMPLACER la fonction login() existante par :

async function login(e) {
    if (e) e.preventDefault();
    
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;

    if (!username || !password) {
        showAlert('Veuillez remplir tous les champs', 'error');
        return;
    }

    const result = await loginWithMultiAccountSupport(username, password);
    
    if (result.success) {
        if (result.multipleAccounts) {
            // Redirection automatique vers /select-event
            // Géré par loginWithMultiAccountSupport
        } else {
            // Login réussi, redirection normale
            // POUR INDEX.HTML (users):
            window.location.href = '/gallery';
            
            // POUR PHOTOGRAPHER.HTML:
            // loadDashboard();
            
            // POUR ADMIN.HTML:
            // loadDashboard();
        }
    } else {
        showAlert(result.error || 'Identifiant ou mot de passe incorrect', 'error');
    }
}

*/

// ============================================================================
// FONCTION UTILITAIRE : Détecter si l'utilisateur vient de event_selector
// ============================================================================

function isReturningFromEventSelector() {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.has('from_selector');
}

// ============================================================================
// AUTO-LOGIN après sélection d'événement
// ============================================================================

// Si l'utilisateur revient de la sélection avec un token, auto-redirect
if (localStorage.getItem('token') && !isReturningFromEventSelector()) {
    // Vérifier le type d'utilisateur et rediriger
    fetch('/api/me', {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
    })
    .then(r => r.json())
    .then(user => {
        if (user.user_type === 'admin') {
            window.location.href = '/admin';
        } else if (user.user_type === 'photographer') {
            window.location.href = '/photographer';
        } else {
            window.location.href = '/gallery';
        }
    })
    .catch(() => {
        // Token invalide, rester sur la page de login
        localStorage.removeItem('token');
    });
}

