// utils.js
const Utils = {
    showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `
            <i class="fas fa-${type === 'success' ? 'check-circle' : 
                           type === 'error' ? 'exclamation-circle' : 
                           'info-circle'}"></i>
            <span>${message}</span>`
        ;

        const container = document.getElementById('toast-container');
        container.appendChild(toast);

        setTimeout(() => {
            toast.classList.add('fade-out');
            setTimeout(() => container.removeChild(toast), 300);
        }, 3000);
    },

    async confirmAction(message) {
        return new Promise((resolve) => {
            const modal = document.getElementById('confirm-modal');
            const messageEl = document.getElementById('confirm-message');
            messageEl.textContent = message;

            const handleYes = () => {
                modal.style.display = 'none';
                cleanup();
                resolve(true);
            };

            const handleNo = () => {
                modal.style.display = 'none';
                cleanup();
                resolve(false);
            };

            const cleanup = () => {
                document.getElementById('confirm-yes').removeEventListener('click', handleYes);
                document.getElementById('confirm-no').removeEventListener('click', handleNo);
            };

            document.getElementById('confirm-yes').addEventListener('click', handleYes);
            document.getElementById('confirm-no').addEventListener('click', handleNo);

            modal.style.display = 'block';
        });
    },

    formatDate(dateString) {
        return new Date(dateString).toLocaleDateString(undefined, {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    },

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },

    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    validateFileName(filename, format) {
        const extension = filename.split('.').pop().toLowerCase();
        switch(format) {
            case 'cmme':
            case 'mei':
                return extension === 'xml';
            case 'json':
                return extension === 'json';
            default:
                return false;
        }
    },

    async copyToClipboard(text) {
        try {
            await navigator.clipboard.writeText(text);
            this.showToast('Copied to clipboard!', 'success');
        } catch (err) {
            this.showToast('Failed to copy to clipboard', 'error');
        }
    },

    downloadFile(content, filename) {
        const blob = new Blob([content], { 
            type: content.startsWith('{') ? 'application/json' : 'text/xml' 
        });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }
};