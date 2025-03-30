// ui.js
const UI = {
    init() {
        this.setupTabNavigation();
        this.setupDropZone();
        this.setupSearchAndFilters();
    },

    setupTabNavigation() {
        const tabs = document.querySelectorAll('.main-nav a');
        tabs.forEach(tab => {
            tab.addEventListener('click', (e) => {
                e.preventDefault();
                const targetId = tab.getAttribute('data-tab');
                
                // Update active tab
                tabs.forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                
                // Show target content
                document.querySelectorAll('.tab-content').forEach(content => {
                    content.classList.remove('active');
                });
                document.getElementById(targetId).classList.add('active');
            });
        });
    },

    setupDropZone() {
        const dropZone = document.getElementById('drop-zone');
        const fileInput = document.getElementById('file-input');
        const fileInfo = document.getElementById('file-info');

        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, preventDefaults, false);
        });

        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }

        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, highlight, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, unhighlight, false);
        });

        function highlight(e) {
            dropZone.classList.add('drag-active');
        }

        function unhighlight(e) {
            dropZone.classList.remove('drag-active');
        }

        dropZone.addEventListener('drop', handleDrop, false);

        function handleDrop(e) {
            const dt = e.dataTransfer;
            const files = dt.files;
            fileInput.files = files;
            updateFileInfo(files[0]);
        }

        fileInput.addEventListener('change', (e) => {
            updateFileInfo(e.target.files[0]);
        });

        function updateFileInfo(file) {
            if (file) {
                fileInfo.style.display = 'block';
                fileInfo.innerHTML = `
                    <div class="file-details">
                        <i class="fas fa-file"></i>
                        <span>${file.name}</span>
                        <span class="file-size">(${Utils.formatFileSize(file.size)})</span>
                    </div>
                `;
                document.getElementById('validate-btn').disabled = false;
                document.getElementById('metadata-btn').disabled = false;
            } else {
                fileInfo.style.display = 'none';
                document.getElementById('validate-btn').disabled = true;
                document.getElementById('metadata-btn').disabled = true;
            }
        }
    },

    setupSearchAndFilters() {
        const searchInput = document.getElementById('dataset-search');
        const formatFilter = document.getElementById('format-filter');
        const sortBy = document.getElementById('sort-by');

        const handleFiltersChange = Utils.debounce(() => {
            const searchTerm = searchInput.value.toLowerCase();
            const format = formatFilter.value;
            const sortMethod = sortBy.value;

            this.filterAndSortDatasets(searchTerm, format, sortMethod);
        }, 300);

        searchInput.addEventListener('input', handleFiltersChange);
        formatFilter.addEventListener('change', handleFiltersChange);
        sortBy.addEventListener('change', handleFiltersChange);
    },

    filterAndSortDatasets(searchTerm, format, sortMethod) {
        const datasets = document.querySelectorAll('.dataset-item');
        
        datasets.forEach(dataset => {
            const name = dataset.querySelector('h3').textContent.toLowerCase();
            const hasFormat = format === '' || dataset.dataset.formats.includes(format);
            const matchesSearch = name.includes(searchTerm);
            
            dataset.style.display = (matchesSearch && hasFormat) ? 'block' : 'none';
        });

        // Sort visible datasets
        const datasetList = document.getElementById('dataset-list');
        const visibleDatasets = Array.from(datasets).filter(d => d.style.display !== 'none');
        
        visibleDatasets.sort((a, b) => {
            switch (sortMethod) {
                case 'name':
                    return a.querySelector('h3').textContent.localeCompare(
                        b.querySelector('h3').textContent
                    );
                case 'date':
                    return new Date(b.dataset.updated) - new Date(a.dataset.updated);
                case 'size':
                    return b.dataset.fileCount - a.dataset.fileCount;
                default:
                    return 0;
            }
        });

        visibleDatasets.forEach(dataset => {
            datasetList.appendChild(dataset);
        });
    },

    showSpinner() {
        document.getElementById('spinner').style.display = 'block';
        document.getElementById('output-display').style.display = 'none';
    },

    hideSpinner() {
        document.getElementById('spinner').style.display = 'none';
        document.getElementById('output-display').style.display = 'block';
    },

    updateResult(content, type = 'success') {
        const output = document.getElementById('output-display');
        output.className = `code-display result-${type}`;
        output.textContent = content;
        
        // Enable/disable buttons
        document.getElementById('download-btn').disabled = !content;
        document.getElementById('copy-btn').disabled = !content;
        document.getElementById('evaluate-btn').disabled = !content;
    },

    showModal(id) {
        document.getElementById(id).style.display = 'flex';
    },

    hideModal(id) {
        document.getElementById(id).style.display = 'none';
    }
};

// Initialize UI when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    UI.init();
});