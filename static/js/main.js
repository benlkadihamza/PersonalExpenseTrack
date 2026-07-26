/**
 * Personal Expense Tracker - Modern Interactive JavaScript
 */

document.addEventListener('DOMContentLoaded', () => {
    // 1. Dark Mode Theme Switcher Initialization
    initThemeSwitcher();

    // 2. Sidebar Toggle Handler
    initSidebarToggle();

    // 3. Auto-show Bootstrap Toasts
    initToasts();

    // 4. Transaction Form Live Calculation
    initLiveCalculation();

    // 5. Delete Confirmation Modal Helper
    initDeleteModal();
});

/**
 * Handles Dark / Light mode switching and saves preference in localStorage
 */
function initThemeSwitcher() {
    const themeToggleBtn = document.getElementById('themeToggleBtn');
    const storedTheme = localStorage.getItem('theme');
    
    // Default to stored theme or HTML theme attribute
    let currentTheme = storedTheme || document.documentElement.getAttribute('data-bs-theme') || 'light';
    setTheme(currentTheme);

    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', () => {
            currentTheme = (currentTheme === 'dark') ? 'light' : 'dark';
            setTheme(currentTheme);
            localStorage.setItem('theme', currentTheme);
        });
    }
}

function setTheme(theme) {
    document.documentElement.setAttribute('data-bs-theme', theme);
    const themeIcon = document.getElementById('themeToggleIcon');
    if (themeIcon) {
        if (theme === 'dark') {
            themeIcon.className = 'bi bi-sun-fill text-warning';
        } else {
            themeIcon.className = 'bi bi-moon-stars-fill text-secondary';
        }
    }
}

/**
 * Handles sidebar collapse on mobile viewports
 */
function initSidebarToggle() {
    const sidebarCollapse = document.getElementById('sidebarCollapse');
    const sidebar = document.getElementById('sidebar');

    if (sidebarCollapse && sidebar) {
        sidebarCollapse.addEventListener('click', () => {
            sidebar.classList.toggle('active');
        });
    }
}

/**
 * Initializes and displays all flash message toasts automatically
 */
function initToasts() {
    const toastElList = [].slice.call(document.querySelectorAll('.toast'));
    toastElList.map((toastEl) => {
        const toast = new bootstrap.Toast(toastEl, { delay: 4000 });
        toast.show();
    });
}

/**
 * Real-time calculation of Net (Revenu - Dépense) on Transaction Form
 */
function initLiveCalculation() {
    const revenuInput = document.getElementById('revenu');
    const depenseInput = document.getElementById('depense');
    const netPreview = document.getElementById('netPreview');

    if (revenuInput && depenseInput && netPreview) {
        const updateNet = () => {
            const rev = parseFloat(revenuInput.value) || 0;
            const dep = parseFloat(depenseInput.value) || 0;
            const net = rev - dep;
            const currency = netPreview.getAttribute('data-currency') || 'DH';
            
            netPreview.textContent = `${net >= 0 ? '+' : ''}${net.toFixed(2)} ${currency}`;
            if (net > 0) {
                netPreview.className = 'badge bg-success-subtle text-success border border-success fs-6';
            } else if (net < 0) {
                netPreview.className = 'badge bg-danger-subtle text-danger border border-danger fs-6';
            } else {
                netPreview.className = 'badge bg-secondary-subtle text-secondary border border-secondary fs-6';
            }
        };

        revenuInput.addEventListener('input', updateNet);
        depenseInput.addEventListener('input', updateNet);
        updateNet();
    }
}

/**
 * Sets up dynamic action URL and details for deletion confirmation modal
 */
function initDeleteModal() {
    const deleteModal = document.getElementById('deleteConfirmModal');
    if (deleteModal) {
        deleteModal.addEventListener('show.bs.modal', (event) => {
            const button = event.relatedTarget ? (event.relatedTarget.closest('[data-delete-url]') || event.relatedTarget) : null;
            if (!button) return;

            const deleteUrl = button.getAttribute('data-delete-url');
            const description = button.getAttribute('data-tx-desc');
            const amount = button.getAttribute('data-tx-amount');

            const form = deleteModal.querySelector('#deleteForm');
            const descEl = deleteModal.querySelector('#deleteTxDesc');
            const amountEl = deleteModal.querySelector('#deleteTxAmount');

            if (form && deleteUrl) form.action = deleteUrl;
            if (descEl) descEl.textContent = description || 'Transaction sans description';
            if (amountEl) amountEl.textContent = amount || '';
        });

        // Clean up modal backdrop on submit
        const deleteForm = deleteModal.querySelector('#deleteForm');
        if (deleteForm) {
            deleteForm.addEventListener('submit', () => {
                const modalInstance = bootstrap.Modal.getInstance(deleteModal);
                if (modalInstance) {
                    modalInstance.hide();
                }
            });
        }
    }

    // Safety cleanup for lingering backdrops on navigation / pageshow
    window.addEventListener('pageshow', () => {
        document.querySelectorAll('.modal-backdrop').forEach(el => el.remove());
        document.body.classList.remove('modal-open');
        document.body.style.overflow = '';
        document.body.style.paddingRight = '';
    });
}
