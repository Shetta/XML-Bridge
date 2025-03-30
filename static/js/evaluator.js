// evaluator.js
class Evaluator {
    constructor() {
        this.currentEvaluation = null;
        this.setupEventListeners();
    }

    setupEventListeners() {
        // Tab switching
        document
            .querySelectorAll(".evaluation-details .tab-btn")
            .forEach((button) => {
                button.addEventListener("click", () => {
                    // Update active tab button
                    document
                        .querySelectorAll(".evaluation-details .tab-btn")
                        .forEach((btn) => {
                            btn.classList.remove("active");
                        });
                    button.classList.add("active");

                    // Show corresponding content
                    const tabId = button.getAttribute("data-tab");
                    document
                        .querySelectorAll(".evaluation-details .tab-content")
                        .forEach((content) => {
                            content.classList.remove("active");
                        });
                    document.getElementById(tabId).classList.add("active");
                });
            });

        // Add report generation button
        const reportBtn = document.createElement("button");
        reportBtn.className = "btn btn-secondary";
        reportBtn.innerHTML =
            '<i class="fas fa-file-download"></i> Generate Report';
        reportBtn.addEventListener("click", () => this.generateReport());

        // Add to panel if it exists
        const panel = document.querySelector(".evaluation-panel");
        if (panel) {
            panel.appendChild(reportBtn);
        }
    }

    async evaluateConversion(sourceFile, resultFile, sourceFormat, targetFormat) {
        try {
            UI.showSpinner();

            const formData = new FormData();
            formData.append("source_file", sourceFile);
            formData.append("result_file", resultFile);

            const response = await fetch(
                `/evaluate/conversion?source_format=${sourceFormat}&target_format=${targetFormat}`,
                {
                    method: "POST",
                    body: formData,
                }
            );

            const data = await response.json();

            if (data.status === "success") {
                this.currentEvaluation = data.evaluation;
                this.displayEvaluation(data.evaluation);
                Utils.showToast("Evaluation completed successfully", "success");

                // Show evaluation panel
                document.querySelector(".evaluation-panel").style.display = "block";
            } else {
                throw new Error(data.message);
            }
        } catch (error) {
            Utils.showToast(error.message, "error");
            console.error("Evaluation error:", error);
        } finally {
            UI.hideSpinner();
        }
    }

    displayEvaluation(evaluation) {
        this.currentEvaluation = evaluation;

        // Update metrics with improved display
        const accuracyMetric = document.getElementById("accuracy-metric");
        accuracyMetric.textContent = evaluation.summary.accuracy;
        this.setMetricColor(accuracyMetric, this.parsePercentage(evaluation.summary.accuracy));

        const preservedMetric = document.getElementById("preserved-metric");
        preservedMetric.textContent = evaluation.summary.elements_preserved;
        this.setMetricColor(preservedMetric, this.getPreservedPercentage(evaluation.summary.elements_preserved));

        const lossMetric = document.getElementById("loss-metric");
        lossMetric.textContent = evaluation.summary.data_loss;
        this.setMetricColor(lossMetric, this.getLossPercentage(evaluation.summary.data_loss), true);

        const timeMetric = document.getElementById("time-metric");
        timeMetric.textContent = evaluation.summary.conversion_time;

        // Update data loss analysis
        const severityValue = document.getElementById("severity-value");
        severityValue.textContent = this.capitalizeSeverity(evaluation.data_loss_details.severity);
        severityValue.className = `severity-${evaluation.data_loss_details.severity}`;

        // Update lost elements with better formatting
        const lostElementsList = document.getElementById("lost-elements-list");
        if (evaluation.data_loss_details.lost_elements.length > 0) {
            lostElementsList.innerHTML = evaluation.data_loss_details.lost_elements
                .map(
                    (elem) => `<li class="lost-element">
                  <div class="element-info">
                      <span class="element-name">${elem.element}</span>
                      ${elem.count ? `<span class="element-count">(${elem.count} elements)</span>` : ''}
                  </div>
                  ${elem.location ? `<div class="element-location">${elem.location}</div>` : ''}
              </li>`
                )
                .join("");
        } else {
            lostElementsList.innerHTML = `<li class="no-issues">No elements were lost during conversion</li>`;
        }

        // Update modified content with better formatting
        const modifiedContentList = document.getElementById("modified-content-list");
        if (evaluation.data_loss_details.modified_content.length > 0) {
            modifiedContentList.innerHTML = evaluation.data_loss_details.modified_content
                .map(
                    (mod) => `<li class="modification">
                  <div class="modification-header">${mod.element}</div>
                  <div class="modification-content">
                      <div class="original">Original: <span>${this.escapeHtml(mod.original)}</span></div>
                      <div class="modified">Modified: <span>${this.escapeHtml(mod.modified)}</span></div>
                  </div>
              </li>`
                )
                .join("");
        } else {
            modifiedContentList.innerHTML = `<li class="no-issues">No significant content modifications detected</li>`;
        }

        // Update validation results
        const validationErrorsList = document.getElementById("validation-errors-list");
        if (evaluation.validation.errors.length > 0) {
            validationErrorsList.innerHTML = evaluation.validation.errors
                .map((error) => `<li class="validation-error">${error}</li>`)
                .join("");
        } else {
            validationErrorsList.innerHTML = `<li class="no-issues">No validation errors detected</li>`;
        }

        const validationWarningsList = document.getElementById("validation-warnings-list");
        if (evaluation.validation.warnings.length > 0) {
            validationWarningsList.innerHTML = evaluation.validation.warnings
                .map((warning) => `<li class="validation-warning">${warning}</li>`)
                .join("");
        } else {
            validationWarningsList.innerHTML = `<li class="no-issues">No validation warnings</li>`;
        }

        // Update recommendations with better formatting
        const recommendationsList = document.getElementById("recommendations-list");
        if (evaluation.recommendations.length > 0) {
            recommendationsList.innerHTML = evaluation.recommendations
                .map((rec) => `<li class="recommendation"><i class="fas fa-check-circle"></i> ${rec}</li>`)
                .join("");
        } else {
            recommendationsList.innerHTML = `<li class="no-issues">No specific recommendations needed</li>`;
        }

        // Add conversion summary
        this.addConversionSummary(evaluation);

        // Show evaluation panel
        document.querySelector(".evaluation-panel").style.display = "block";
    }

    // Add a new method to display conversion summary
    addConversionSummary(evaluation) {
        // Find or create summary section
        let summarySection = document.getElementById("conversion-summary");
        if (!summarySection) {
            summarySection = document.createElement("div");
            summarySection.id = "conversion-summary";
            summarySection.className = "conversion-summary";

            // Insert at the top of the evaluation panel
            const evalPanel = document.querySelector(".evaluation-panel");
            evalPanel.insertBefore(summarySection, evalPanel.firstChild);
        }

        // Parse quality level from accuracy
        const accuracy = this.parsePercentage(evaluation.summary.accuracy);
        let qualityLevel, qualityClass;

        if (accuracy >= 90) {
            qualityLevel = "Excellent";
            qualityClass = "excellent";
        } else if (accuracy >= 75) {
            qualityLevel = "Good";
            qualityClass = "good";
        } else if (accuracy >= 60) {
            qualityLevel = "Fair";
            qualityClass = "fair";
        } else {
            qualityLevel = "Needs Improvement";
            qualityClass = "poor";
        }

        // Create summary content
        summarySection.innerHTML = `
        <h3>Conversion Quality Summary</h3>
        <div class="quality-indicator ${qualityClass}">
          <div class="quality-badge">
            <i class="fas ${accuracy >= 75 ? 'fa-check-circle' : 'fa-info-circle'}"></i>
            <span>${qualityLevel}</span>
          </div>
          <div class="quality-details">
            <p>Accuracy: <strong>${evaluation.summary.accuracy}</strong></p>
            <p>Elements Preserved: <strong>${evaluation.summary.elements_preserved}</strong></p>
            <p>Data Loss Severity: <strong>${this.capitalizeSeverity(evaluation.data_loss_details.severity)}</strong></p>
          </div>
        </div>
        <p class="summary-note">
          ${this.getSummaryDescription(accuracy, evaluation.data_loss_details.severity)}
        </p>
      `;
    }

    // Helper to get summary description
    getSummaryDescription(accuracy, severity) {
        if (accuracy >= 90) {
            return "The conversion was highly successful with excellent preservation of musical content.";
        } else if (accuracy >= 75) {
            return "The conversion completed successfully with good preservation of core musical elements.";
        } else if (accuracy >= 60) {
            return "The conversion completed with some data loss. Review the details below.";
        } else if (severity === "high") {
            return "Significant data loss occurred during conversion. Manual intervention may be needed.";
        } else {
            return "The conversion completed but with lower accuracy than expected. Check recommendations for improvements.";
        }
    }

    // Improved generateReport function for evaluator.js
    generateReport() {
        if (!this.currentEvaluation) {
            Utils.showToast("No evaluation data available", "error");
            return;
        }

        try {
            // Safely extract data with fallbacks
            const summary = this.currentEvaluation.summary || {};
            const dataLossDetails = this.currentEvaluation.data_loss_details || {};

            // Get accuracy (either as percentage string or direct number)
            const accuracy = this.parsePercentage(summary.accuracy || "0%");

            // Safely get arrays with fallbacks to empty arrays
            const lostElements = dataLossDetails.lost_elements || [];
            const lostAttributes = dataLossDetails.lost_attributes || [];
            const recommendations = this.currentEvaluation.recommendations || [];

            const report = {
                timestamp: new Date().toISOString(),
                evaluation: this.currentEvaluation,
                summary: {
                    accuracy: accuracy,
                    status: accuracy >= 80 ? "PASS" : "NEEDS REVIEW",
                    issues: lostElements.length + lostAttributes.length,
                    recommendations: recommendations.length,
                },
            };

            Utils.downloadFile(
                JSON.stringify(report, null, 2),
                `evaluation-report-${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.json`
            );

            Utils.showToast("Report generated successfully", "success");
        } catch (error) {
            console.error("Error generating report:", error);
            Utils.showToast("Failed to generate report: " + error.message, "error");
        }
    }

    // Improved parsePercentage to handle both string and number inputs
    parsePercentage(percentValue) {
        if (typeof percentValue === 'number') {
            return percentValue;
        }

        if (typeof percentValue !== 'string') {
            return 0;
        }

        // Match percentage string like "85.5%"
        const match = /(\d+(\.\d+)?)%/.exec(percentValue);
        return match ? parseFloat(match[1]) : 0;
    }

    // Helper method to determine color based on metric value
    setMetricColor(element, value, isInverted = false) {
        // Remove any existing classes
        element.classList.remove("metric-excellent", "metric-good", "metric-fair", "metric-poor");

        // Add appropriate class
        let className;
        if (isInverted) {
            // For metrics where lower is better (like data loss)
            if (value <= 5) className = "metric-excellent";
            else if (value <= 15) className = "metric-good";
            else if (value <= 30) className = "metric-fair";
            else className = "metric-poor";
        } else {
            // For metrics where higher is better (like accuracy)
            if (value >= 90) className = "metric-excellent";
            else if (value >= 75) className = "metric-good";
            else if (value >= 60) className = "metric-fair";
            else className = "metric-poor";
        }

        element.classList.add(className);
    }

    // Helper method to parse percentage from string (e.g., "85.5%" -> 85.5)
    parsePercentage(percentStr) {
        const match = /(\d+(\.\d+)?)%/.exec(percentStr);
        return match ? parseFloat(match[1]) : 0;
    }

    // Helper method to parse preserved elements percentage
    getPreservedPercentage(preservedStr) {
        const match = /\((\d+(\.\d+)?)%\)/.exec(preservedStr);
        return match ? parseFloat(match[1]) : 0;
    }

    // Helper method to parse data loss percentage
    getLossPercentage(lossStr) {
        const match = /\((\d+(\.\d+)?)%\)/.exec(lossStr);
        return match ? parseFloat(match[1]) : 0;
    }

    // Helper method to capitalize severity
    capitalizeSeverity(severity) {
        return severity.charAt(0).toUpperCase() + severity.slice(1);
    }

    // Helper method to escape HTML
    escapeHtml(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    getSeverityClass(severity) {
        switch (severity.toLowerCase()) {
            case "high":
                return "severity-high";
            case "medium":
                return "severity-medium";
            case "low":
                return "severity-low";
            case "none":
                return "severity-none";
            default:
                return "";
        }
    }
}

// Initialize evaluator when DOM is loaded
document.addEventListener("DOMContentLoaded", () => {
    window.evaluator = new Evaluator();
});