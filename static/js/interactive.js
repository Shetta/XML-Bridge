// interactive.js
class InteractiveConverter {
    constructor() {
        this.sessionId = null;
        this.pendingDecisions = [];
        this.conversionHistory = [];
        this.setupEventListeners();
    }

    setupEventListeners() {
        // Interactive conversion button
        document.getElementById('interactive-btn').addEventListener('click', () => {
            this.startInteractiveConversion();
        });

        // Set up event delegation for decision resolution
        document.addEventListener('click', (e) => {
            // Handle decision option selection
            if (e.target.matches('.decision-option')) {
                const decisionId = e.target.closest('.decision-panel').dataset.decisionId;
                const choice = e.target.dataset.value;
                this.resolveDecision(decisionId, choice);
            }

            // Handle cancel interactive session
            if (e.target.matches('#cancel-interactive')) {
                this.cancelSession();
            }
        });

        // Store preference checkbox
        document.addEventListener('change', (e) => {
            if (e.target.matches('#store-preference')) {
                // Update UI based on preference storage choice
                const savePreference = e.target.checked;
                document.querySelectorAll('.decision-option').forEach(btn => {
                    if (savePreference) {
                        btn.textContent += ' (Save preference)';
                    } else {
                        btn.textContent = btn.textContent.replace(' (Save preference)', '');
                    }
                });
            }
        });
    }

    async startInteractiveConversion() {
        // Check if there's a file
        if (!window.converter.currentFile) {
            Utils.showToast('Please select a file first', 'error');
            return;
        }

        const sourceFormat = document.getElementById('source-format').value;
        const targetFormat = document.getElementById('target-format').value;

        UI.showSpinner();
        document.getElementById('interactive-panel').style.display = 'block';
        document.getElementById('interactive-header').textContent = 
            `Interactive Conversion: ${sourceFormat.toUpperCase()} to ${targetFormat.toUpperCase()}`;

        try {
            const formData = new FormData();
            formData.append('file', window.converter.currentFile);
            formData.append('source_format', sourceFormat);
            formData.append('target_format', targetFormat);

            const response = await fetch('/interactive/start', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (data.status === 'success') {
                this.sessionId = data.session_id;
                
                // Show session info
                document.getElementById('session-id').textContent = data.session_id;
                document.getElementById('pending-count').textContent = data.pending_decisions;
                
                // Get first decision if any
                if (data.pending_decisions > 0) {
                    await this.getNextDecision();
                } else {
                    // No decisions needed, complete conversion
                    await this.completeConversion();
                }
                
                Utils.showToast('Interactive session started', 'success');
            } else {
                throw new Error(data.message);
            }
        } catch (error) {
            Utils.showToast(error.message, 'error');
            document.getElementById('interactive-panel').style.display = 'none';
        } finally {
            UI.hideSpinner();
        }
    }

    async getNextDecision() {
        if (!this.sessionId) return;
        
        try {
            const response = await fetch(`/interactive/decisions/${this.sessionId}`);
            const data = await response.json();
            
            if (data.status === 'success' && data.decisions.pending.length > 0) {
                const decision = data.decisions.pending[0];
                this.renderDecision(decision);
            } else {
                // No more decisions, complete conversion
                await this.completeConversion();
            }
        } catch (error) {
            Utils.showToast(`Error getting next decision: ${error.message}`, 'error');
        }
    }

    renderDecision(decision) {
        const decisionPanel = document.getElementById('decision-panel');
        decisionPanel.innerHTML = '';
        decisionPanel.dataset.decisionId = decision.id;
        
        // Create decision UI
        const decisionEl = document.createElement('div');
        decisionEl.className = 'decision';
        decisionEl.innerHTML = `
            <h3>${this.formatDecisionType(decision.type)}</h3>
            <p class="decision-description">${decision.description}</p>
            <div class="decision-context">
                <strong>Context:</strong> ${decision.context}
            </div>
            ${decision.impact ? `
                <div class="decision-impact">
                    <strong>Impact:</strong> ${decision.impact}
                </div>
            ` : ''}
            <div class="decision-options">
                <h4>Choose an option:</h4>
                <div class="options-list"></div>
            </div>
            <div class="preference-option">
                <label>
                    <input type="checkbox" id="store-preference">
                    Remember this choice for similar situations
                </label>
            </div>
        `;
        
        decisionPanel.appendChild(decisionEl);
        
        // Add options
        const optionsList = decisionEl.querySelector('.options-list');
        decision.options.forEach(option => {
            const optionBtn = document.createElement('button');
            optionBtn.className = 'btn decision-option';
            optionBtn.dataset.value = typeof option === 'object' ? JSON.stringify(option) : option;
            optionBtn.textContent = this.formatOption(option);
            
            // Highlight default option if provided
            if (decision.default_option && 
                (option === decision.default_option || 
                 JSON.stringify(option) === JSON.stringify(decision.default_option))) {
                optionBtn.classList.add('default-option');
                optionBtn.textContent += ' (Recommended)';
            }
            
            optionsList.appendChild(optionBtn);
        });
        
        // Show the decision panel
        document.getElementById('decision-container').style.display = 'block';
    }

    formatDecisionType(type) {
        // Convert decision type enum to readable title
        const typeMap = {
            'attribute_mapping': 'Attribute Mapping Decision',
            'structure_choice': 'Structure Choice Decision',
            'metadata_resolution': 'Metadata Resolution',
            'format_specific': 'Format-Specific Feature',
            'ambiguous_notation': 'Ambiguous Notation',
            'missing_information': 'Missing Information'
        };
        
        return typeMap[type] || 'Decision Required';
    }

    formatOption(option) {
        if (typeof option === 'object') {
            // Format object option nicely
            return Object.entries(option)
                .map(([key, value]) => `${key}: ${value}`)
                .join(', ');
        }
        return String(option);
    }

    async resolveDecision(decisionId, choice) {
        try {
            UI.showSpinner();
            
            // Parse choice if it's a stringified JSON
            let parsedChoice = choice;
            try {
                if (choice.startsWith('{') || choice.startsWith('[')) {
                    parsedChoice = JSON.parse(choice);
                }
            } catch (e) {
                // If parsing fails, use the original string
                parsedChoice = choice;
            }
            
            const savePreference = document.getElementById('store-preference').checked;
            
            const response = await fetch('/interactive/resolve', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    session_id: this.sessionId,
                    decision_id: decisionId,
                    choice: parsedChoice,
                    save_preference: savePreference
                })
            });
            
            const data = await response.json();
            
            if (data.status === 'success') {
                // Add to history
                this.conversionHistory.push({
                    decision_id: decisionId,
                    choice: parsedChoice
                });
                
                // Update session info
                document.getElementById('pending-count').textContent = 
                    data.pending_decisions || 0;
                
                // Check if conversion is complete
                if (data.session_status === 'completed') {
                    // Conversion is complete with this decision
                    UI.updateResult(data.result);
                    document.getElementById('decision-container').style.display = 'none';
                    
                    Utils.showToast('Conversion completed successfully', 'success');
                    
                    // Enable evaluation
                    document.getElementById('evaluate-btn').disabled = false;
                    window.converter.currentResult = data.result;
                    
                    // Update the progress section
                    this.updateCompletionInfo();
                } else {
                    // Get next decision
                    await this.getNextDecision();
                }
            } else {
                throw new Error(data.message);
            }
        } catch (error) {
            Utils.showToast(`Error resolving decision: ${error.message}`, 'error');
        } finally {
            UI.hideSpinner();
        }
    }

    async completeConversion() {
        try {
            UI.showSpinner();
            
            const response = await fetch(`/interactive/status/${this.sessionId}`);
            const data = await response.json();
            
            if (data.status === 'success') {
                if (data.session_status.completion_info) {
                    // Session already has completed conversion result
                    const result = data.session_status.completion_info.result;
                    UI.updateResult(result);
                    
                    window.converter.currentResult = result;
                    document.getElementById('evaluate-btn').disabled = false;
                    
                    Utils.showToast('Conversion completed successfully', 'success');
                    this.updateCompletionInfo();
                } else {
                    // Need to trigger final conversion
                    await fetch(`/interactive/complete/${this.sessionId}`, {
                        method: 'POST'
                    })
                    .then(res => res.json())
                    .then(data => {
                        if (data.status === 'success') {
                            UI.updateResult(data.result);
                            window.converter.currentResult = data.result;
                            document.getElementById('evaluate-btn').disabled = false;
                            
                            Utils.showToast('Conversion completed successfully', 'success');
                            this.updateCompletionInfo();
                        } else {
                            throw new Error(data.message);
                        }
                    });
                }
                
                // Hide decision UI
                document.getElementById('decision-container').style.display = 'none';
            } else {
                throw new Error(data.message || 'Error completing conversion');
            }
        } catch (error) {
            Utils.showToast(`Error completing conversion: ${error.message}`, 'error');
        } finally {
            UI.hideSpinner();
        }
    }

    updateCompletionInfo() {
        const progressSection = document.getElementById('interactive-progress');
        progressSection.innerHTML = `
            <h3>Conversion Progress</h3>
            <div class="progress-complete">
                <i class="fas fa-check-circle"></i>
                <p>Interactive conversion completed successfully!</p>
                <p>${this.conversionHistory.length} decisions were made during this session.</p>
            </div>
            <button id="review-conversion" class="btn btn-secondary">
                <i class="fas fa-history"></i> Review Conversion History
            </button>
        `;
        
        // Add event listener for review button
        document.getElementById('review-conversion').addEventListener('click', () => {
            this.showConversionHistory();
        });
    }

    showConversionHistory() {
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h2>Conversion History</h2>
                    <button class="modal-close">&times;</button>
                </div>
                <div class="conversion-history">
                    <h3>Session ID: ${this.sessionId}</h3>
                    <div class="history-items">
                        ${this.conversionHistory.map((item, index) => `
                            <div class="history-item">
                                <h4>Decision ${index + 1}</h4>
                                <div class="history-choice">
                                    <strong>Choice:</strong> 
                                    <pre>${typeof item.choice === 'object' ? 
                                        JSON.stringify(item.choice, null, 2) : 
                                        item.choice}</pre>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Show the modal
        modal.style.display = 'block';
        
        // Add event listeners
        modal.querySelector('.modal-close').addEventListener('click', () => {
            modal.remove();
        });
        
        // Close when clicking outside
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.remove();
            }
        });
    }

    async cancelSession() {
        if (!this.sessionId) return;
        
        if (await Utils.confirmAction('Are you sure you want to cancel this interactive conversion session?')) {
            try {
                await fetch(`/interactive/cancel/${this.sessionId}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        reason: 'User cancelled'
                    })
                });
                
                this.sessionId = null;
                this.pendingDecisions = [];
                this.conversionHistory = [];
                
                // Hide UI
                document.getElementById('interactive-panel').style.display = 'none';
                document.getElementById('decision-container').style.display = 'none';
                
                Utils.showToast('Interactive session cancelled', 'info');
            } catch (error) {
                Utils.showToast(`Error cancelling session: ${error.message}`, 'error');
            }
        }
    }
}

// Initialize interactive converter when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.interactiveConverter = new InteractiveConverter();
});