class App {
    constructor() {
        this.converter = window.converter;
        this.evaluator = window.evaluator;
        this.datasetManager = window.datasetManager;
        this.init();
    }

    init() {
        this.setupEventListeners();
        UI.init();
    }

    setupEventListeners() {
        // Global error handling
        window.addEventListener('error', (event) => {
            console.error('Global error:', event.error);
            Utils.showToast('An unexpected error occurred', 'error');
        });

        // Handle unhandled promise rejections
        window.addEventListener('unhandledrejection', (event) => {
            console.error('Unhandled promise rejection:', event.reason);
            Utils.showToast('An unexpected error occurred', 'error');
        });

        // Close modals when clicking outside
        window.addEventListener('click', (event) => {
            const modals = document.querySelectorAll('.modal');
            modals.forEach(modal => {
                if (event.target === modal) {
                    modal.style.display = 'none';
                }
            });
        });

        // Handle keyboard shortcuts
        document.addEventListener('keydown', (event) => {
            // Escape key closes modals
            if (event.key === 'Escape') {
                const modals = document.querySelectorAll('.modal');
                modals.forEach(modal => {
                    if (modal.style.display === 'block') {
                        modal.style.display = 'none';
                    }
                });
            }
        });
        
        // Help button
        const helpBtn = document.getElementById('help-btn');
        if (helpBtn) {
            helpBtn.addEventListener('click', () => {
                this.showHelpModal();
            });
        }
        
        // Format-specific tooltips
        document.querySelectorAll('.help-tooltip').forEach(tooltip => {
            tooltip.addEventListener('click', (e) => {
                e.preventDefault();
                const content = tooltip.getAttribute('data-help');
                Utils.showToast(content, 'info', 5000); // Show for 5 seconds
            });
        });
        
        // Early music format warning
        const sourceFormatSelect = document.getElementById('source-format');
        const targetFormatSelect = document.getElementById('target-format');
        
        const checkForEarlyMusicWarning = () => {
            // If converting from CMME to MEI, show early music warning
            if (sourceFormatSelect.value === 'cmme' && targetFormatSelect.value === 'mei') {
                // Check if warning doesn't already exist
                if (!document.querySelector('.early-music-warning')) {
                    const warning = document.createElement('div');
                    warning.className = 'early-music-warning';
                    warning.innerHTML = `
                        <i class="fas fa-info-circle"></i>
                        <span>CMME contains early music notation features. Consider using 
                        <strong>Interactive Convert</strong> for better control.</span>
                        <button class="btn-close"><i class="fas fa-times"></i></button>
                    `;
                    
                    // Add event listener to close button
                    warning.querySelector('.btn-close').addEventListener('click', () => {
                        warning.remove();
                    });
                    
                    // Insert after the format selects
                    targetFormatSelect.closest('.form-group').after(warning);
                }
            } else {
                // Remove warning if it exists
                const warning = document.querySelector('.early-music-warning');
                if (warning) {
                    warning.remove();
                }
            }
        };
        
        if (sourceFormatSelect && targetFormatSelect) {
            sourceFormatSelect.addEventListener('change', checkForEarlyMusicWarning);
            targetFormatSelect.addEventListener('change', checkForEarlyMusicWarning);
            
            // Initial check
            checkForEarlyMusicWarning();
        }
    }
    
    showHelpModal() {
        const helpModal = document.getElementById('help-modal');
        if (helpModal) {
            helpModal.style.display = 'block';
        }
    }

    showError(message) {
        Utils.showToast(message, 'error');
    }

    showSuccess(message) {
        Utils.showToast(message, 'success');
    }
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new App();
});
