// converter.js
class Converter {
    constructor() {
        this.currentFile = null;
        this.currentResult = null;
        this.setupEventListeners();
    }

    setupEventListeners() {
        // Form submission
        const form = document.getElementById("conversion-form");
        form.addEventListener("submit", async (e) => {
            e.preventDefault();
            await this.handleConversion();
        });

        // Source format change handler
        document.getElementById("source-format").addEventListener("change", (e) => {
            this.updateTargetFormatOptions(e.target.value);
        });

        // Button handlers
        document
            .getElementById("validate-btn")
            .addEventListener("click", () => this.validateFile());
        document
            .getElementById("metadata-btn")
            .addEventListener("click", () => this.extractMetadata());
        document
            .getElementById("evaluate-btn")
            .addEventListener("click", () => this.evaluate());
        document
            .getElementById("copy-btn")
            .addEventListener("click", () => this.copyResult());
        document
            .getElementById("download-btn")
            .addEventListener("click", () => this.downloadResult());

        // File input handler
        document.getElementById("file-input").addEventListener("change", (e) => {
            this.handleFileSelection(e.target.files[0]);
        });

        // Drop zone handlers
        const dropZone = document.getElementById("drop-zone");
        ["dragenter", "dragover", "dragleave", "drop"].forEach((eventName) => {
            dropZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
            });
        });

        ["dragenter", "dragover"].forEach((eventName) => {
            dropZone.addEventListener(eventName, () => {
                dropZone.classList.add("drag-active");
            });
        });

        ["dragleave", "drop"].forEach((eventName) => {
            dropZone.addEventListener(eventName, () => {
                dropZone.classList.remove("drag-active");
            });
        });

        dropZone.addEventListener("drop", (e) => {
            const file = e.dataTransfer.files[0];
            this.handleFileSelection(file);
        });
    }

    updateTargetFormatOptions(sourceFormat) {
        const targetSelect = document.getElementById("target-format");
        targetSelect.innerHTML = "";

        const formats = ["cmme", "mei", "json"].filter((f) => f !== sourceFormat);
        formats.forEach((format) => {
            const option = document.createElement("option");
            option.value = format;
            option.textContent = format.toUpperCase();
            targetSelect.appendChild(option);
        });
    }

    // Update the handleFileSelection method in converter.js
    handleFileSelection(file) {
        if (!file) return;

        const sourceFormat = document.getElementById("source-format").value;
        const extension = file.name.split(".").pop().toLowerCase();

        // Validate file format with support for .mei and .cmme extensions
        let validExtensions = [];
        if (sourceFormat === "json") {
            validExtensions = ["json"];
        } else if (sourceFormat === "mei") {
            validExtensions = ["xml", "mei"];  // Accept both .xml and .mei
        } else if (sourceFormat === "cmme") {
            validExtensions = ["xml", "cmme"];  // Accept both .xml and .cmme
        }

        if (!validExtensions.includes(extension)) {
            Utils.showToast(
                `Invalid file format. Expected ${validExtensions.map(ext => '.' + ext).join(' or ')} file for ${sourceFormat.toUpperCase()} format`,
                "error"
            );
            return;
        }

        this.currentFile = file;

        // Update file info display
        const fileInfo = document.getElementById("file-info");
        fileInfo.style.display = "block";
        fileInfo.innerHTML = `
        <div class="file-details">
            <i class="fas fa-file"></i>
            <span>${file.name}</span>
            <span class="file-size">(${Utils.formatFileSize(file.size)})</span>
        </div>
    `;

        // Enable buttons
        document.getElementById("validate-btn").disabled = false;
        document.getElementById("metadata-btn").disabled = false;
    }

    async handleConversion() {
        if (!this.currentFile) {
            Utils.showToast("Please select a file first", "error");
            return;
        }

        const sourceFormat = document.getElementById("source-format").value;
        const targetFormat = document.getElementById("target-format").value;
        const conversionType = `${sourceFormat}-to-${targetFormat}`;

        UI.showSpinner();

        try {
            const formData = new FormData();

            // Read file content and clean up XML if needed
            const fileContent = await this.currentFile.text();
            let fileToSend;

            if (sourceFormat === "mei") {
                // Clean up MEI namespace declarations
                const cleanedContent = this.cleanMEINamespace(fileContent);
                fileToSend = new Blob([cleanedContent], { type: "text/xml" });
            } else {
                fileToSend = this.currentFile;
            }

            formData.append("file", fileToSend);

            const response = await fetch(`/transform?type=${conversionType}`, {
                method: "POST",
                body: formData,
            });

            const data = await response.json();

            if (data.status === "success") {
                this.currentResult = data.result;

                // Format the result based on the target format
                let formattedResult = data.result;
                if (targetFormat === "json") {
                    // Make sure we're dealing with a string before parsing
                    if (typeof formattedResult === 'string') {
                        try {
                            // Try to parse and re-stringify for pretty formatting
                            formattedResult = JSON.stringify(JSON.parse(formattedResult), null, 2);
                        } catch (jsonError) {
                            console.error("JSON parsing error:", jsonError);
                            // If it's not valid JSON, leave it as is
                        }
                    } else if (typeof formattedResult === 'object') {
                        // If it's already an object, stringify it
                        formattedResult = JSON.stringify(formattedResult, null, 2);
                    }
                } else if (targetFormat === "mei" || targetFormat === "cmme") {
                    // Pretty print XML if it's a string
                    if (typeof formattedResult === 'string') {
                        try {
                            const parser = new DOMParser();
                            const xmlDoc = parser.parseFromString(formattedResult, "text/xml");
                            const serializer = new XMLSerializer();
                            formattedResult = this.formatXML(
                                serializer.serializeToString(xmlDoc)
                            );
                        } catch (xmlError) {
                            console.error("XML parsing error:", xmlError);
                            // If it's not valid XML, leave it as is
                        }
                    }
                }

                UI.updateResult(formattedResult);
                Utils.showToast("Conversion successful!", "success");

                // Enable evaluation
                document.getElementById("evaluate-btn").disabled = false;
                document.getElementById("copy-btn").disabled = false;
                document.getElementById("download-btn").disabled = false;
            } else {
                throw new Error(data.message);
            }
        } catch (error) {
            UI.updateResult(error.message, "error");
            Utils.showToast(error.message, "error");
        } finally {
            UI.hideSpinner();
        }
    }

    // Add helper methods for XML handling
    cleanMEINamespace(xmlContent) {
        // Remove any existing XML declaration
        if (xmlContent.startsWith("<?xml")) {
            xmlContent = xmlContent.substring(xmlContent.indexOf("?>") + 2).trim();
        }

        // Remove any existing namespace declarations
        xmlContent = xmlContent.replace(/\sxmlns="[^"]*"/g, "");

        // Add single namespace declaration
        if (xmlContent.includes("<mei>")) {
            xmlContent = xmlContent.replace(
                "<mei>",
                '<mei xmlns="http://www.music-encoding.org/ns/mei">'
            );
        }

        return xmlContent;
    }

    formatXML(xml) {
        let formatted = "";
        let indent = "";
        const tab = "    "; // 4 spaces for indentation

        xml.split(/>\s*</).forEach((node) => {
            if (node.match(/^\/\w/)) {
                // Closing tag
                indent = indent.substring(tab.length);
            }

            formatted += indent + "<" + node + ">\r\n";

            if (node.match(/^<?\w[^>]*[^\/]$/)) {
                // Opening tag
                indent += tab;
            }
        });

        return formatted.substring(1, formatted.length - 3);
    }

    async validateFile() {
        if (!this.currentFile) {
            Utils.showToast("Please select a file first", "error");
            return;
        }

        const format = document.getElementById("source-format").value;
        UI.showSpinner();

        try {
            const formData = new FormData();
            formData.append("file", this.currentFile);

            const response = await fetch(`/validate?type=${format}`, {
                method: "POST",
                body: formData,
            });

            const data = await response.json();

            if (data.status === "success") {
                if (data.validation.valid) {
                    Utils.showToast("File is valid!", "success");
                } else {
                    Utils.showToast(
                        "Validation failed. Check the details below.",
                        "error"
                    );
                }

                // Format the validation results for display
                const formattedResults = {
                    status: data.validation.valid ? "Valid" : "Invalid",
                    errors: data.validation.errors.map((error) => {
                        // Handle namespace-related errors differently
                        if (error.includes("Attribute xmlns redefined")) {
                            return "Note: Namespace declaration will be handled automatically during conversion";
                        }
                        return error;
                    }),
                    warnings: data.validation.warnings,
                };

                UI.updateResult(JSON.stringify(formattedResults, null, 2));
            } else {
                throw new Error(data.message);
            }
        } catch (error) {
            Utils.showToast(error.message, "error");
            UI.updateResult(
                JSON.stringify(
                    {
                        status: "error",
                        message: error.message,
                    },
                    null,
                    2
                )
            );
        } finally {
            UI.hideSpinner();
        }
    }

    // Add this helper method to the Converter class
    formatValidationError(error) {
        // Clean up namespace-related error messages
        if (error.includes("Attribute xmlns redefined")) {
            return "Note: Namespace declaration will be handled automatically during conversion";
        }
        return error;
    }

    async extractMetadata() {
        if (!this.currentFile) {
            Utils.showToast("Please select a file first", "error");
            return;
        }

        const format = document.getElementById("source-format").value;
        UI.showSpinner();

        try {
            const formData = new FormData();
            formData.append("file", this.currentFile);

            const response = await fetch(`/metadata?type=${format}`, {
                method: "POST",
                body: formData,
            });

            const data = await response.json();

            if (data.status === "success") {
                UI.updateResult(JSON.stringify(data.metadata, null, 2));
                Utils.showToast("Metadata extracted successfully!", "success");
            } else {
                throw new Error(data.message);
            }
        } catch (error) {
            Utils.showToast(error.message, "error");
        } finally {
            UI.hideSpinner();
        }
    }

    async evaluate() {
        if (!this.currentFile || !this.currentResult) {
          Utils.showToast(
            "Both source file and conversion result are required",
            "error"
          );
          return;
        }
      
        const sourceFormat = document.getElementById("source-format").value;
        const targetFormat = document.getElementById("target-format").value;
      
        try {
          UI.showSpinner();
          
          const formData = new FormData();
          formData.append("source_file", this.currentFile);
      
          // Create a blob with the current result
          let resultContent = this.currentResult;
          
          // Make sure resultContent is a string
          if (typeof resultContent === 'object') {
            resultContent = JSON.stringify(resultContent);
          }
          
          const resultType = targetFormat === 'json' ? 'application/json' : 'text/xml';
          const resultBlob = new Blob([resultContent], { type: resultType });
          
          // Create a file from the blob
          const resultFileName = `result.${targetFormat === 'json' ? 'json' : 'xml'}`;
          const resultFile = new File([resultBlob], resultFileName, { type: resultType });
          
          formData.append("result_file", resultFile);
      
          console.log(`Evaluating conversion from ${sourceFormat} to ${targetFormat}`);
          
          const response = await fetch(
            `/evaluate/conversion?source_format=${sourceFormat}&target_format=${targetFormat}`,
            {
              method: "POST",
              body: formData,
            }
          );
      
          const data = await response.json();
          console.log("Evaluation response:", data);
      
          if (data.status === "success") {
            // We pass the raw response to the evaluator, which will normalize it
            window.evaluator.evaluateConversion(
              this.currentFile, 
              resultFile, 
              sourceFormat, 
              targetFormat
            );
          } else {
            throw new Error(data.message || "Unknown error during evaluation");
          }
        } catch (error) {
          Utils.showToast(error.message, "error");
          console.error('Evaluation error:', error);
        } finally {
          UI.hideSpinner();
        }
      }

    copyResult() {
        if (!this.currentResult) return;
        Utils.copyToClipboard(this.currentResult);
    }

    downloadResult() {
        if (!this.currentResult) return;
        const extension = this.currentResult.startsWith("{") ? "json" : "xml";
        Utils.downloadFile(this.currentResult, `converted.${extension}`);
    }

    getCurrentResult() {
        return this.currentResult;
    }
}

// Initialize converter when DOM is loaded
document.addEventListener("DOMContentLoaded", () => {
    window.converter = new Converter();
});