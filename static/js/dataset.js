// dataset.js
class DatasetManager {
    constructor() {
        this.datasets = [];
        this.currentDataset = null;
        this.init();
    }

    async init() {
        await this.loadDatasets();
        this.setupEventListeners();
    }

    async loadDatasets() {
        try {
            const response = await fetch('/datasets');
            const data = await response.json();
            if (data.status === 'success') {
                this.datasets = data.datasets;
                this.renderDatasetList();
            } else {
                throw new Error(data.message);
            }
        } catch (error) {
            Utils.showToast('Error loading datasets: ' + error.message, 'error');
        }
    }

    setupEventListeners() {
        const searchInput = document.getElementById('dataset-search');
        if (searchInput) {
            searchInput.addEventListener('input', Utils.debounce(() => {
                this.filterDatasets(searchInput.value);
            }, 300));
        }

        // Setup format and sort filters
        const formatFilter = document.getElementById('format-filter');
        const sortBy = document.getElementById('sort-by');
        
        if (formatFilter) {
            formatFilter.addEventListener('change', () => this.applyFilters());
        }
        if (sortBy) {
            sortBy.addEventListener('change', () => this.applyFilters());
        }
    }

    applyFilters() {
        const searchTerm = document.getElementById('dataset-search').value;
        const format = document.getElementById('format-filter').value;
        const sortMethod = document.getElementById('sort-by').value;
        
        this.filterAndSortDatasets(searchTerm, format, sortMethod);
    }

    filterDatasets(searchTerm = '') {
        const items = document.querySelectorAll('.dataset-item');
        const term = searchTerm.toLowerCase();
        
        items.forEach(item => {
            const name = item.querySelector('h3').textContent.toLowerCase();
            const description = item.querySelector('.dataset-description').textContent.toLowerCase();
            const matches = name.includes(term) || description.includes(term);
            item.style.display = matches ? 'block' : 'none';
        });
    }

    filterAndSortDatasets(searchTerm = '', format = '', sortMethod = 'name') {
        const items = document.querySelectorAll('.dataset-item');
        const term = searchTerm.toLowerCase();
        
        items.forEach(item => {
            const name = item.querySelector('h3').textContent.toLowerCase();
            const description = item.querySelector('.dataset-description').textContent.toLowerCase();
            const formats = item.dataset.formats.split(',');
            
            const matchesSearch = name.includes(term) || description.includes(term);
            const matchesFormat = !format || formats.includes(format);
            
            item.style.display = (matchesSearch && matchesFormat) ? 'block' : 'none';
        });

        // Sort visible items
        const container = document.getElementById('dataset-list');
        const visibleItems = Array.from(items).filter(item => item.style.display !== 'none');
        
        visibleItems.sort((a, b) => {
            switch (sortMethod) {
                case 'name':
                    return a.querySelector('h3').textContent.localeCompare(
                        b.querySelector('h3').textContent
                    );
                case 'date':
                    return new Date(b.dataset.updated) - new Date(a.dataset.updated);
                case 'size':
                    return parseInt(b.dataset.fileCount) - parseInt(a.dataset.fileCount);
                default:
                    return 0;
            }
        });

        // Reorder items in the DOM
        visibleItems.forEach(item => container.appendChild(item));
    }

    renderDatasetList() {
        const container = document.getElementById('dataset-list');
        if (!container) return;

        container.innerHTML = '';
        
        if (this.datasets.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-folder-open"></i>
                    <p>No datasets found</p>
                    <button class="btn btn-primary" onclick="datasetManager.showCreateModal()">
                        Create New Dataset
                    </button>
                </div>
            `;
            return;
        }

        this.datasets.forEach(dataset => {
            const element = document.createElement('div');
            element.className = 'dataset-item';
            element.dataset.formats = Object.keys(dataset.formats).join(',');
            element.dataset.updated = dataset.updated;
            element.dataset.fileCount = dataset.file_count;
            
            element.innerHTML = `
                <div class="dataset-header">
                    <h3>${dataset.name}</h3>
                    <div class="dataset-actions">
                        <button class="btn btn-icon" onclick="datasetManager.editDataset('${dataset.name}')">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn btn-icon" onclick="datasetManager.deleteDataset('${dataset.name}')">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
                <p class="dataset-description">${dataset.description || 'No description'}</p>
                <div class="dataset-stats">
                    <div class="stat">
                        <i class="fas fa-file"></i>
                        <span>${dataset.file_count} files</span>
                    </div>
                    <div class="stat">
                        <i class="fas fa-clock"></i>
                        <span>Updated ${Utils.formatDate(dataset.updated)}</span>
                    </div>
                </div>
                <div class="format-badges">
                    ${Object.entries(dataset.formats)
                        .filter(([_, count]) => count > 0)
                        .map(([format, count]) => `
                            <span class="badge badge-${format}">
                                ${format.toUpperCase()}: ${count}
                            </span>
                        `).join('')}
                </div>
            `;
            
            container.appendChild(element);
        });
    }

    showCreateModal() {
        const modal = document.getElementById('dataset-modal');
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h2>Create New Dataset</h2>
                    <button class="modal-close" onclick="this.closest('.modal').style.display='none'">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <form id="create-dataset-form" enctype="multipart/form-data">
                    <div class="form-group">
                        <label>Name</label>
                        <input type="text" name="name" required class="form-control" 
                               placeholder="Enter dataset name">
                    </div>
                    <div class="form-group">
                        <label>Description</label>
                        <textarea name="description" class="form-control" 
                                 placeholder="Enter dataset description"></textarea>
                    </div>
                    <div class="form-group">
                        <label>Initial Files (optional)</label>
                        <div class="file-upload" id="dataset-file-upload">
                            <i class="fas fa-cloud-upload-alt"></i>
                            <p>Drag & drop files here or click to browse</p>
                            <input type="file" name="files" multiple 
                                   accept=".xml,.json" class="form-control">
                        </div>
                        <div id="selected-files"></div>
                    </div>
                    <div class="form-group file-type-selection" style="display: none;">
                        <label>File Type for XML Files</label>
                        <select name="xml_type" class="form-control">
                            <option value="cmme">CMME</option>
                            <option value="mei">MEI</option>
                        </select>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" 
                                onclick="this.closest('.modal').style.display='none'">
                            Cancel
                        </button>
                        <button type="submit" class="btn btn-primary">
                            Create Dataset
                        </button>
                    </div>
                </form>
            </div>
        `;
        
        modal.style.display = 'block';
        
        // Setup file upload preview and type selection
        const fileInput = modal.querySelector('input[type="file"]');
        const selectedFiles = modal.querySelector('#selected-files');
        const fileTypeSelection = modal.querySelector('.file-type-selection');
        
        fileInput.addEventListener('change', () => {
            const files = Array.from(fileInput.files);
            selectedFiles.innerHTML = files
                .map(file => `
                    <div class="selected-file">
                        <i class="fas fa-file"></i>
                        <span>${file.name}</span>
                    </div>
                `).join('');
                
            // Show file type selection if there are XML files
            const hasXmlFiles = files.some(file => file.name.toLowerCase().endsWith('.xml'));
            fileTypeSelection.style.display = hasXmlFiles ? 'block' : 'none';
        });
        
        // Setup form submission
        document.getElementById('create-dataset-form').onsubmit = async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            try {
                await this.createDataset(formData);
                modal.style.display = 'none';
            } catch (error) {
                console.error('Error creating dataset:', error);
            }
        };
    }

    async createDataset(formData) {
        try {
            const response = await fetch('/datasets', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            if (data.status === 'success') {
                await this.loadDatasets();
                Utils.showToast('Dataset created successfully!', 'success');
            } else {
                throw new Error(data.message);
            }
        } catch (error) {
            Utils.showToast(error.message, 'error');
            throw error;
        }
    }

    async editDataset(name) {
        try {
            // Fetch dataset details
            const response = await fetch(`/datasets/${name}`);
            const data = await response.json();
            
            if (data.status !== 'success') {
                throw new Error(data.message);
            }
            
            const dataset = data.dataset;
            
            // Show edit modal
            const modal = document.getElementById('dataset-modal');
            modal.innerHTML = `
                <div class="modal-content">
                    <div class="modal-header">
                        <h2>Edit Dataset: ${dataset.name}</h2>
                        <button class="modal-close" onclick="this.closest('.modal').style.display='none'">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                    <form id="edit-dataset-form" enctype="multipart/form-data">
                        <div class="form-group">
                            <label>Description</label>
                            <textarea name="description" class="form-control" 
                                     placeholder="Enter dataset description">${dataset.description || ''}</textarea>
                        </div>
                        <div class="form-group">
                            <label>Current Files</label>
                            <div class="current-files">
                                ${Object.entries(dataset.files || {}).map(([format, files]) => `
                                    <div class="format-section">
                                        <h4>${format.toUpperCase()}</h4>
                                        ${files.map(file => `
                                            <div class="file-item">
                                                <i class="fas fa-file"></i>
                                                <span>${file}</span>
                                                <div class="file-actions">
                                                    <button type="button" class="btn btn-icon edit-attributes" 
                                                            onclick="datasetManager.viewAndEditAttributes('${dataset.name}', '${format}', '${file}')">
                                                        <i class="fas fa-edit"></i>
                                                    </button>
                                                    <button type="button" class="btn btn-icon delete-file" 
                                                            data-format="${format}" data-file="${file}">
                                                        <i class="fas fa-trash"></i>
                                                    </button>
                                                </div>
                                            </div>
                                        `).join('')}
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                        <div class="form-group">
                            <label>Add Files</label>
                            <div class="file-upload" id="dataset-file-upload">
                                <i class="fas fa-cloud-upload-alt"></i>
                                <p>Drag & drop files here or click to browse</p>
                                <input type="file" name="files" multiple 
                                       accept=".xml,.json" class="form-control">
                            </div>
                            <div id="selected-files"></div>
                        </div>
                        <div class="form-group file-type-selection" style="display: none;">
                            <label>File Type for XML Files</label>
                            <select name="xml_type" class="form-control">
                                <option value="cmme">CMME</option>
                                <option value="mei">MEI</option>
                            </select>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" 
                                    onclick="this.closest('.modal').style.display='none'">
                                Cancel
                            </button>
                            <button type="submit" class="btn btn-primary">Save Changes</button>
                        </div>
                    </form>
                </div>
            `;
            
            modal.style.display = 'block';
            
            // Setup file upload preview and type selection
            const fileInput = modal.querySelector('input[type="file"]');
            const selectedFiles = modal.querySelector('#selected-files');
            const fileTypeSelection = modal.querySelector('.file-type-selection');
            
            fileInput.addEventListener('change', () => {
                const files = Array.from(fileInput.files);
                selectedFiles.innerHTML = files
                    .map(file => `
                        <div class="selected-file">
                            <i class="fas fa-file"></i>
                            <span>${file.name}</span>
                        </div>
                    `).join('');
                    
                // Show file type selection if there are XML files
                const hasXmlFiles = files.some(file => file.name.toLowerCase().endsWith('.xml'));
                fileTypeSelection.style.display = hasXmlFiles ? 'block' : 'none';
            });
            
            // Setup delete file buttons
            const deleteButtons = modal.querySelectorAll('.delete-file');
            deleteButtons.forEach(button => {
                button.addEventListener('click', async (e) => {
                    e.preventDefault();
                    const format = button.dataset.format;
                    const filename = button.dataset.file;
                    if (await Utils.confirmAction(`Delete file ${filename}?`)) {
                        await this.deleteFile(name, format, filename);
                        button.closest('.file-item').remove();
                    }
                });
            });
            
            // Setup form submission
            document.getElementById('edit-dataset-form').onsubmit = async (e) => {
                e.preventDefault();
                const formData = new FormData(e.target);
                formData.append('name', name);
                
                try {
                    const response = await fetch(`/datasets/${name}`, {
                        method: 'PUT',
                        body: formData
                    });
                    
                    const result = await response.json();
                    if (result.status === 'success') {
                        await this.loadDatasets();
                        modal.style.display = 'none';
                        Utils.showToast('Dataset updated successfully!', 'success');
                    } else {
                        throw new Error(result.message);
                    }
                } catch (error) {
                    Utils.showToast(error.message, 'error');
                }
            };
            
        } catch (error) {
            Utils.showToast(error.message, 'error');
        }
    }

    async deleteDataset(name) {
        if (await Utils.confirmAction(`Are you sure you want to delete dataset "${name}"?`)) {
            try {
                const response = await fetch(`/datasets/${name}`, {
                    method: 'DELETE'
                });
                
                const data = await response.json();
                if (data.status === 'success') {
                    await this.loadDatasets();
                    Utils.showToast('Dataset deleted successfully!', 'success');
                } else {
                    throw new Error(data.message);
                }
            } catch (error) {
                Utils.showToast(error.message, 'error');
            }
        }
    }

    async deleteFile(datasetName, format, filename) {
        try {
            const response = await fetch(`/datasets/${datasetName}/files/${format}/${filename}`, {
                method: 'DELETE'
            });
            
            const data = await response.json();
            if (data.status === 'success') {
                Utils.showToast('File deleted successfully!', 'success');
            } else {
                throw new Error(data.message);
            }
        } catch (error) {
            Utils.showToast(error.message, 'error');
        }
    }

    async viewAndEditAttributes(datasetName, format, filename) {
        try {
            // Fetch the file content
            const response = await fetch(`/datasets/${datasetName}/files/${format}/${filename}/content`);
            const data = await response.json();
            
            if (data.status !== 'success') {
                throw new Error(data.message);
            }

            const content = data.content;
            
            // Show modal with attribute editor
            const modal = document.getElementById('dataset-modal');
            modal.innerHTML = `
                <div class="modal-content">
                    <div class="modal-header">
                        <h2>Edit Attributes: ${filename}</h2>
                        <button class="modal-close" onclick="this.closest('.modal').style.display='none'">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                    <form id="edit-attributes-form">
                        <div class="form-group">
                            <label>File Content</label>
                            <div class="attribute-editor">
                                ${this.renderAttributeEditor(format, content)}
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" 
                                    onclick="this.closest('.modal').style.display='none'">
                                Cancel
                            </button>
                            <button type="submit" class="btn btn-primary">Save Changes</button>
                        </div>
                    </form>
                </div>
            `;
            
            modal.style.display = 'block';

            // Setup form submission
            document.getElementById('edit-attributes-form').onsubmit = async (e) => {
                e.preventDefault();
                const formData = new FormData(e.target);
                const updatedContent = this.generateUpdatedContent(format, content, formData);
                
                try {
                    const response = await fetch(`/datasets/${datasetName}/files/${format}/${filename}`, {
                        method: 'PUT',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            content: updatedContent
                        })
                    });
                    
                    const result = await response.json();
                    if (result.status === 'success') {
                        modal.style.display = 'none';
                        Utils.showToast('Attributes updated successfully!', 'success');
                    } else {
                        throw new Error(result.message);
                    }
                } catch (error) {
                    Utils.showToast(error.message, 'error');
                }
            };
        } catch (error) {
            Utils.showToast(error.message, 'error');
        }
    }

    renderAttributeEditor(format, content) {
        if (format === 'mei') {
            // Parse the MEI XML
            const parser = new DOMParser();
            const doc = parser.parseFromString(content, 'text/xml');
            const notes = doc.getElementsByTagName('note');
            
            let html = '<div class="mei-attributes">';
            
            // Add section for new attributes
            html += `
                <div class="add-attribute-section">
                    <h3>Add New Attribute</h3>
                    <div class="form-group">
                        <select name="new_attribute_type" class="form-control">
                            <option value="articulation">Articulation</option>
                            <option value="dynamic">Dynamic</option>
                            <option value="ornament">Ornament</option>
                            <option value="technical">Technical Direction</option>
                            <option value="custom">Custom Attribute</option>
                        </select>
                        <input type="text" name="new_attribute_name" class="form-control" 
                               placeholder="Attribute name (for custom)" style="display: none;">
                        <input type="text" name="new_attribute_value" class="form-control" 
                               placeholder="Attribute value">
                        <button type="button" class="btn btn-secondary" onclick="datasetManager.addNewAttribute(this)">
                            Add Attribute
                        </button>
                    </div>
                </div>
                <div class="existing-attributes">
                    <h3>Existing Attributes</h3>
            `;
            
            // Display existing attributes for each note
            Array.from(notes).forEach((note, index) => {
                html += `
                    <div class="note-attributes" data-note-index="${index}">
                        <h4>Note ${index + 1}</h4>
                        <div class="attribute-group">
                            ${this.renderNoteAttributes(note)}
                        </div>
                    </div>
                `;
            });
            
            html += '</div></div>';
            return html;
        }
        
        // Add handlers for other formats as needed
        return '<div>Attribute editing not supported for this format</div>';
    }

    renderNoteAttributes(note) {
        let html = '';
        
        // Basic attributes
        const basicAttrs = ['pname', 'oct', 'dur', 'stem.dir', 'accid', 'dots', 'beam', 'tie'];
        basicAttrs.forEach(attr => {
            const value = note.getAttribute(attr) || '';
            html += `
                <div class="attribute-item">
                    <label>${attr}</label>
                    <input type="text" name="attr_${attr}" value="${value}" 
                           class="form-control" data-original-attr="${attr}">
                    ${attr !== 'pname' && attr !== 'dur' ? `
                        <button type="button" class="btn btn-icon" onclick="this.parentElement.remove()">
                            <i class="fas fa-trash"></i>
                        </button>
                    ` : ''}
                </div>
            `;
        });
        
        // Articulations
        const artics = note.getElementsByTagName('artic');
        Array.from(artics).forEach((artic, i) => {
            html += `
                <div class="attribute-item">
                    <label>Articulation ${i + 1}</label>
                    <input type="text" name="artic_${i}" value="${artic.getAttribute('type') || ''}" 
                           class="form-control" data-type="articulation">
                    <button type="button" class="btn btn-icon" onclick="this.parentElement.remove()">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            `;
        });

        // Custom attributes
        const customAttrs = Array.from(note.attributes).filter(attr => 
            !basicAttrs.includes(attr.name) && !attr.name.startsWith('xmlns'));
        customAttrs.forEach((attr, i) => {
            html += `
                <div class="attribute-item">
                    <label>${attr.name}</label>
                    <input type="text" name="custom_${attr.name}" value="${attr.value}" 
                           class="form-control" data-type="custom">
                    <button type="button" class="btn btn-icon" onclick="this.parentElement.remove()">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            `;
        });
        
        return html;
    }

    addNewAttribute(button) {
        const container = button.closest('.note-attributes').querySelector('.attribute-group');
        const type = button.parentElement.querySelector('[name="new_attribute_type"]').value;
        const value = button.parentElement.querySelector('[name="new_attribute_value"]').value;
        const customName = button.parentElement.querySelector('[name="new_attribute_name"]').value;
        
        if (!value || (type === 'custom' && !customName)) {
            Utils.showToast('Please enter all required values', 'error');
            return;
        }
        
        const newAttribute = document.createElement('div');
        newAttribute.className = 'attribute-item';
        newAttribute.innerHTML = `
            <label>${type === 'custom' ? customName : type}</label>
            <input type="text" name="${type === 'custom' ? `custom_${customName}` : `${type}_new`}" 
                   value="${value}" class="form-control" data-type="${type}">
            <button type="button" class="btn btn-icon" onclick="this.parentElement.remove()">
                <i class="fas fa-trash"></i>
            </button>
        `;
        
        container.appendChild(newAttribute);
        
        // Clear input fields
        button.parentElement.querySelector('[name="new_attribute_value"]').value = '';
        if (type === 'custom') {
            button.parentElement.querySelector('[name="new_attribute_name"]').value = '';
        }
    }

    generateUpdatedContent(format, originalContent, formData) {
        if (format === 'mei') {
            const parser = new DOMParser();
            const doc = parser.parseFromString(originalContent, 'text/xml');
            const notes = doc.getElementsByTagName('note');
            
            // Update existing attributes and add new ones
            Array.from(notes).forEach((note, index) => {
                // Update basic attributes
                for (const [key, value] of formData.entries()) {
                    if (key.startsWith('attr_')) {
                        const attrName = key.replace('attr_', '');
                        if (value) {
                            note.setAttribute(attrName, value);
                        } else {
                            note.removeAttribute(attrName);
                        }
                    }
                }
                
                // Handle articulations
                Array.from(note.getElementsByTagName('artic')).forEach(artic => {
                    artic.remove();
                });
                
                // Add new articulations
                for (const [key, value] of formData.entries()) {
                    if (key.startsWith('artic_') && value) {
                        const artic = doc.createElement('artic');
                        artic.setAttribute('type', value);
                        note.appendChild(artic);
                    }
                }

                // Handle custom attributes
                for (const [key, value] of formData.entries()) {
                    if (key.startsWith('custom_') && value) {
                        const attrName = key.replace('custom_', '');
                        note.setAttribute(attrName, value);
                    }
                }
            });
            
            return new XMLSerializer().serializeToString(doc);
        }
        
        return originalContent;
    }

    async uploadFiles(datasetName, files) {
        const formData = new FormData();
        files.forEach((file, index) => {
            formData.append(`file${index}`, file);
        });
        
        try {
            const response = await fetch(`/datasets/${datasetName}`, {
                method: 'PUT',
                body: formData
            });
            
            const data = await response.json();
            if (data.status !== 'success') {
                throw new Error(data.message);
            }
        } catch (error) {
            throw new Error(`Error uploading files: ${error.message}`);
        }
    }
}

// Create a global instance
const datasetManager = new DatasetManager();

// Add event listener for attribute type selection
document.addEventListener('change', (e) => {
    if (e.target.name === 'new_attribute_type') {
        const customNameInput = e.target.parentElement.querySelector('[name="new_attribute_name"]');
        if (customNameInput) {
            customNameInput.style.display = e.target.value === 'custom' ? 'block' : 'none';
        }
    }
});