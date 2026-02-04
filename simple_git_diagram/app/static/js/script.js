/**
 * @typedef {Object} MermaidAPI
 * @property {function} initialize
 * @property {function} run
 */

/**
 * @typedef {function} SvgPanZoomAPI
 */

// External libraries loaded via script tags
/** @type {MermaidAPI} */
// @ts-ignore - mermaid is loaded externally
const mermaid = window.mermaid;

/** @type {SvgPanZoomAPI} */
// @ts-ignore - svgPanZoom is loaded externally
const svgPanZoom = window.svgPanZoom;

document.addEventListener('DOMContentLoaded', () => {
    let latestDiagramCode = ""; // Store raw code for export

    mermaid.initialize({
        startOnLoad: false,
        securityLevel: 'loose', // Allow click events/links
        theme: 'base',
        themeVariables: {
            // Dark background
            background: '#1a1f26',

            // Primary/default node colors - Vibrant Blue
            primaryColor: '#3b82f6',
            primaryTextColor: '#ffffff',
            primaryBorderColor: '#60a5fa',

            // Secondary node colors - Purple
            secondaryColor: '#8b5cf6',
            secondaryTextColor: '#ffffff',
            secondaryBorderColor: '#a78bfa',

            // Tertiary node colors - Teal
            tertiaryColor: '#14b8a6',
            tertiaryTextColor: '#ffffff',
            tertiaryBorderColor: '#2dd4bf',

            // Flowchart specific
            nodeBorder: '#60a5fa',
            nodeTextColor: '#ffffff',

            // Main text and lines
            lineColor: '#94a3b8',
            textColor: '#e2e8f0',

            // Cluster/Subgraph colors - slightly transparent
            clusterBkg: 'rgba(99, 102, 241, 0.15)',
            clusterBorder: '#818cf8',

            // Label backgrounds
            labelBackground: '#1e293b',

            // Edge label
            edgeLabelBackground: '#1e293b',

            // Font
            fontFamily: 'Inter, system-ui, sans-serif',
            fontSize: '14px',

            // Note styling
            noteBkgColor: '#fbbf24',
            noteTextColor: '#1e293b',
            noteBorderColor: '#f59e0b'
        }
    });

    const generateBtn = /** @type {HTMLButtonElement} */ (document.getElementById('generateBtn'));
    const regenerateBtn = /** @type {HTMLButtonElement} */ (document.getElementById('regenerateBtn'));
    const repoInput = /** @type {HTMLInputElement} */ (document.getElementById('repoUrl'));
    const patInput = /** @type {HTMLInputElement} */ (document.getElementById('githubPat'));
    const errorMsg = /** @type {HTMLDivElement} */ (document.getElementById('errorMsg'));
    const loading = /** @type {HTMLDivElement} */ (document.getElementById('loading'));
    const diagramContainer = /** @type {HTMLDivElement} */ (document.getElementById('diagramContainer'));
    const mermaidDiv = /** @type {HTMLDivElement} */ (document.querySelector('.mermaid'));
    const exportButtons = /** @type {HTMLDivElement} */ (document.getElementById('exportButtons'));
    const exportSvgBtn = /** @type {HTMLButtonElement} */ (document.getElementById('exportSvgBtn'));
    const exportPngBtn = /** @type {HTMLButtonElement} */ (document.getElementById('exportPngBtn'));
    const exportDrawioBtn = /** @type {HTMLButtonElement} */ (document.getElementById('exportDrawioBtn'));
    const diagramTypeSelect = /** @type {HTMLSelectElement} */ (document.getElementById('diagramType'));

    if (!generateBtn || !regenerateBtn || !repoInput || !patInput || !errorMsg ||
        !loading || !diagramContainer || !mermaidDiv || !exportButtons ||
        !exportSvgBtn || !exportPngBtn || !exportDrawioBtn || !diagramTypeSelect) {
        console.error('Required DOM elements not found');
        return;
    }

    generateBtn.addEventListener('click', () => fetchDiagram());
    regenerateBtn.addEventListener('click', () => fetchDiagram(true));
    exportSvgBtn.addEventListener('click', exportAsSvg);
    exportPngBtn.addEventListener('click', exportAsPng);
    exportDrawioBtn.addEventListener('click', exportToDrawio);

    async function fetchDiagram(forceRefresh = false) {
        const repoUrl = repoInput.value.trim();
        const pat = patInput.value.trim();
        const diagramType = diagramTypeSelect.value;

        if (!repoUrl) {
            showError("Please enter a repository URL.");
            return;
        }

        // Reset UI
        showError("");
        loading.classList.remove('hidden');
        diagramContainer.classList.add('hidden');
        exportButtons.classList.add('hidden');
        generateBtn.disabled = true;
        mermaidDiv.innerHTML = ""; // Clear previous

        try {
            const response = await fetch('/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    repo_url: repoUrl,
                    pat: pat || null, // Ensure valid JSON null if empty
                    force_refresh: forceRefresh,
                    diagram_type: diagramType
                })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || "Failed to generate diagram");
            }

            // Success
            loading.classList.add('hidden');
            diagramContainer.classList.remove('hidden');

            // Render Mermaid
            mermaidDiv.removeAttribute('data-processed');
            latestDiagramCode = data.diagram; // Store for export
            mermaidDiv.innerHTML = data.diagram;

            try {
                await mermaid.run({
                    nodes: [mermaidDiv]
                });

                // Initialize SVG Pan Zoom
                const svgElement = mermaidDiv.querySelector('svg');
                if (svgElement) {
                    // Remove fixed dimensions that Mermaid might add
                    svgElement.removeAttribute('height');
                    svgElement.removeAttribute('width');
                    svgElement.removeAttribute('style'); // Clear inline styles

                    // Force full size
                    svgElement.style.width = '100%';
                    svgElement.style.height = '100%';
                    svgElement.style.display = 'block'; // Remove any default inline spacing

                    svgPanZoom(svgElement, {
                        zoomEnabled: true,
                        controlIconsEnabled: true,
                        fit: true,
                        center: true,
                        minZoom: 0.1, // Allow zooming out more
                        maxZoom: 10,
                        resize: true // Listen for window resize
                    });

                    // Show export buttons
                    exportButtons.classList.remove('hidden');
                }

            } catch (err) {
                console.error("Mermaid Render Error", err);
                showError("Generated diagram has syntax errors. Try regenerating.");
                mermaidDiv.innerHTML = `<pre class="bg-gray-100 p-4 rounded overflow-auto text-xs">${data.diagram}</pre>`; // Fallback to raw code
                exportButtons.classList.add('hidden');
            }

            regenerateBtn.style.display = 'inline-block';

        } catch (err) {
            loading.classList.add('hidden');
            showError(err instanceof Error ? err.message : String(err));
            exportButtons.classList.add('hidden');
        } finally {
            generateBtn.disabled = false;
        }
    }

    /**
     * @param {string} msg - Error message to display
     */
    function showError(msg) {
        errorMsg.textContent = msg;
        if (msg) {
            errorMsg.classList.remove('hidden');
        } else {
            errorMsg.classList.add('hidden');
        }
    }

    // === Export Functions ===

    function getSvgElement() {
        return mermaidDiv.querySelector('svg');
    }

    function exportAsSvg() {
        const svgElement = getSvgElement();
        if (!svgElement) {
            showError("No diagram to export.");
            return;
        }

        // Clone SVG and prepare for export
        const svgClone = /** @type {SVGElement} */ (svgElement.cloneNode(true));

        // Get actual dimensions from viewBox or bounding box
        const bbox = svgElement.getBBox();
        const viewBox = svgElement.getAttribute('viewBox');

        // Set explicit dimensions for standalone SVG
        if (viewBox) {
            const parts = viewBox.split(' ');
            svgClone.setAttribute('width', parts[2] || '800');
            svgClone.setAttribute('height', parts[3] || '600');
        } else {
            svgClone.setAttribute('width', String(bbox.width));
            svgClone.setAttribute('height', String(bbox.height));
        }

        // Add XML declaration and proper namespace
        const svgData = new XMLSerializer().serializeToString(svgClone);
        const svgBlob = new Blob([
            '<?xml version="1.0" encoding="UTF-8"?>\n',
            svgData
        ], { type: 'image/svg+xml;charset=utf-8' });

        downloadBlob(svgBlob, 'diagram.svg');
    }

    function exportAsPng() {
        const svgElement = getSvgElement();
        if (!svgElement) {
            showError("No diagram to export.");
            return;
        }

        // Get SVG dimensions
        const bbox = svgElement.getBBox();
        const viewBox = svgElement.getAttribute('viewBox');
        let width, height;

        if (viewBox) {
            const parts = viewBox.split(' ');
            width = parseFloat(parts[2] || '0');
            height = parseFloat(parts[3] || '0');
        } else {
            width = bbox.width;
            height = bbox.height;
        }

        // Scale factor for high-res export (2x for crisp output)
        const scale = 2;
        const scaledWidth = width * scale;
        const scaledHeight = height * scale;

        // Clone and prepare SVG
        const svgClone = /** @type {SVGElement} */ (svgElement.cloneNode(true));
        svgClone.setAttribute('width', String(width));
        svgClone.setAttribute('height', String(height));

        // Serialize SVG
        const svgData = new XMLSerializer().serializeToString(svgClone);
        const svgBase64 = 'data:image/svg+xml;base64,' + btoa(unescape(encodeURIComponent(svgData)));

        // Create canvas and draw
        const canvas = document.createElement('canvas');
        canvas.width = scaledWidth;
        canvas.height = scaledHeight;
        const ctx = canvas.getContext('2d');

        if (!ctx) {
            showError("Failed to create canvas context.");
            return;
        }

        // White background
        ctx.fillStyle = '#ffffff';
        ctx.fillRect(0, 0, scaledWidth, scaledHeight);

        const img = new Image();
        img.onload = function () {
            ctx.drawImage(img, 0, 0, scaledWidth, scaledHeight);
            canvas.toBlob(function (blob) {
                if (blob) {
                    downloadBlob(blob, 'diagram.png');
                } else {
                    showError("Failed to create PNG blob.");
                }
            }, 'image/png');
        };
        img.onerror = function () {
            showError("Failed to export PNG. Try SVG instead.");
        };
        img.src = svgBase64;
    }

    function exportToDrawio() {
        if (!latestDiagramCode) {
            showError("No diagram to export.");
            return;
        }

        // Export as plain Mermaid text (.mmd)
        // This can be inserted into Draw.io via: Arrange > Insert > Advanced > Mermaid
        const blob = new Blob([latestDiagramCode], { type: 'text/plain;charset=utf-8' });
        downloadBlob(blob, 'diagram.mmd');
    }

    /**
     * @param {Blob} blob - Blob to download
     * @param {string} filename - Filename for the download
     */
    function downloadBlob(blob, filename) {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }
});
