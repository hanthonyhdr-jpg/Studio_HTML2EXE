let allColors = [];
let pagesData = [];
window.logoDataUrl = null;

// --- Inicialização ---
document.addEventListener("DOMContentLoaded", () => {
    const dropZone = document.getElementById('dropZone');
    dropZone.addEventListener('click', () => {
        window.location.href = 'app://selectfiles';
    });

    // Auto-update em qualquer mudança
    document.querySelectorAll('input, select').forEach(el => {
        el.addEventListener('input', updatePreview);
    });

    document.getElementById('printDate').valueAsDate = new Date();
});

// --- Comunicação com Python ---
let bridgeAttempts = 0;
function onBridgeReady() {
    console.log("Ponte estabelecida com Python.");
    document.getElementById('dropZone').style.borderColor = '#10b981';
    loadPresetsDropdown();
}

function tryConnectBridge() {
    bridgeAttempts++;
    if (bridgeAttempts > 20) {
        console.error('Bridge nao conectado apos 20 tentativas');
        return;
    }
    if (window.pybridge) {
        onBridgeReady();
    } else {
        setTimeout(tryConnectBridge, 200);
    }
}

function receiveFiles(files) {
    if (!files || files.length === 0) return;
    files.forEach(f => parseXML(f.content));
    const fileList = document.getElementById('fileList');
    files.forEach(f => {
        const div = document.createElement('div');
        div.textContent = `✓ ${f.name}`;
        fileList.appendChild(div);
    });
    document.getElementById('clearFilesBtn').style.display = 'block';
    updatePreview();
}

// --- Processamento de XML ---
function parseXML(xmlString) {
    const parser = new DOMParser();
    const xmlDoc = parser.parseFromString(xmlString, "text/xml");
    const elements = xmlDoc.getElementsByTagName("*");
    
    for (let i = 0; i < elements.length; i++) {
        let node = elements[i];
        let attrs = {};
        for (let j = 0; j < node.attributes.length; j++) {
            let a = node.attributes[j];
            attrs[a.name.toLowerCase()] = a.value;
        }

        let name = attrs.name || attrs.nome || attrs.n;
        // Lógica de resource (Corel)
        if (!name && attrs.resid) {
            let res = xmlDoc.querySelector(`resource[id="${attrs.resid}"]`);
            if (res) name = (res.querySelector('BR') || res.querySelector('PT') || res).textContent;
        }

        let r = parseInt(attrs.r), g = parseInt(attrs.g), b = parseInt(attrs.b);
        let c = parseInt(attrs.c), m = parseInt(attrs.m), y = parseInt(attrs.y), k = parseInt(attrs.k);
        let hex = attrs.hex || attrs.hexcode;

        if (!isNaN(r) || !isNaN(c) || hex) {
            // Se só tem CMYK, converte para RGB para o preview
            if (isNaN(r) && !isNaN(c)) {
                r = Math.round(255 * (1 - c/100) * (1 - k/100));
                g = Math.round(255 * (1 - m/100) * (1 - k/100));
                b = Math.round(255 * (1 - y/100) * (1 - k/100));
            }
            if (!hex) hex = '#' + [r, g, b].map(x => x.toString(16).padStart(2, '0')).join('').toUpperCase();
            
            allColors.push({
                name: name || 'Cesta de Cor',
                r: r || 0, g: g || 0, b: b || 0,
                c: c || 0, m: m || 0, y: y || 0, k: k || 0,
                hex: hex,
                cmyk: `C${c||0} M${m||0} Y${y||0} K${k||0}`
            });
        }
    }
}

// --- Layout e Preview ---
function updatePreview() {
    const previewArea = document.getElementById('previewArea');
    const emptyState = document.getElementById('emptyState');
    
    if (allColors.length === 0) {
        emptyState.style.display = 'block';
        previewArea.querySelectorAll('.page-wrapper').forEach(p => p.remove());
        return;
    }
    emptyState.style.display = 'none';

    // Medidas
    const pW = parseFloat(document.getElementById('pageW').value) || 210;
    const pH = parseFloat(document.getElementById('pageH').value) || 297;
    const mT = parseFloat(document.getElementById('mTop').value) || 15;
    const mL = parseFloat(document.getElementById('mLeft').value) || 15;
    const cols = parseInt(document.getElementById('cols').value) || 4;
    const sqW = parseFloat(document.getElementById('sqW').value) || 25;
    const sqH = parseFloat(document.getElementById('sqH').value) || 25;
    const hG = parseFloat(document.getElementById('hGap').value) || 20;
    const vG = parseFloat(document.getElementById('vGap').value) || 25;
    const tG = parseFloat(document.getElementById('textGap').value) || 4;
    const fs = parseFloat(document.getElementById('fontSize').value) || 8;
    const fs_mm = fs * 0.352778;

    // Altura do bloco (Quadrado + Espaço + Texto)
    const showRGB = document.getElementById('showRGB').checked;
    const showHex = document.getElementById('showHex').checked;
    const showCMYK = document.getElementById('showCMYK').checked;
    let lines = 1; if(showRGB) lines++; if(showHex) lines++; if(showCMYK) lines++;
    const blockHeight = sqH + tG + (lines * fs_mm * 1.3);

    // Header Height
    let headerH = 15;
    if (window.logoDataUrl) {
        const lW = parseFloat(document.getElementById('logoSize').value) || 40;
        headerH += (lW * (window.logoHeight / window.logoWidth)) + 5;
    }

    pagesData = [];
    let currentPage = [];
    let curX = mL, curY = mT + headerH, colIdx = 0;

    allColors.forEach(color => {
        if (colIdx >= cols) { colIdx = 0; curX = mL; curY += blockHeight + vG; }
        if (curY + blockHeight > pH - mT && currentPage.length > 0) {
            pagesData.push(currentPage);
            currentPage = []; curX = mL; curY = mT + headerH; colIdx = 0;
        }
        currentPage.push({ color, x: curX, y: curY });
        curX += sqW + hG; colIdx++;
    });
    if (currentPage.length > 0) pagesData.push(currentPage);

    renderPages(pW, pH, sqW, sqH, tG, fs_mm, showRGB, showHex, showCMYK);
}

function renderPages(pW, pH, sqW, sqH, tG, fs_mm, sR, sH, sC) {
    const area = document.getElementById('previewArea');
    area.querySelectorAll('.page-wrapper').forEach(p => p.remove());
    
    pagesData.forEach((page, i) => {
        const wrapper = document.createElement('div');
        wrapper.className = 'page-wrapper';
        wrapper.style.width = `${pW * 3}px`; // Escala para o monitor
        wrapper.style.height = `${pH * 3}px`;
        
        const label = document.createElement('div');
        label.className = 'page-label';
        label.textContent = `PÁGINA ${i + 1} DE ${pagesData.length}`;
        
        const svg = generateSVG(page, pW, pH, sqW, sqH, tG, fs_mm, sR, sH, sC);
        wrapper.innerHTML = label.outerHTML + svg;
        area.appendChild(wrapper);
    });
}

function generateSVG(page, pW, pH, sqW, sqH, tG, fs_mm, sR, sH, sC) {
    const font = document.getElementById('fontName').value;
    const mName = document.getElementById('machineName').value;
    const pDate = document.getElementById('printDate').value;
    let dateStr = pDate ? pDate.split('-').reverse().join('/') : '';
    const title = `Máquina: ${mName} | Data: ${dateStr}`;
    const mT = parseFloat(document.getElementById('mTop').value) || 15;

    let svg = `<svg xmlns="http://www.w3.org/2000/svg" width="100%" height="100%" viewBox="0 0 ${pW} ${pH}">
    <rect width="100%" height="100%" fill="white" />`;

    if (window.logoDataUrl) {
        const lW = parseFloat(document.getElementById('logoSize').value) || 40;
        const lH = lW * (window.logoHeight / window.logoWidth);
        svg += `<image href="${window.logoDataUrl}" x="${(pW-lW)/2}" y="${mT}" width="${lW}" height="${lH}" />`;
        svg += `<text x="${pW/2}" y="${mT+lH+5}" font-family="${font}" font-size="${fs_mm*1.5}" font-weight="bold" text-anchor="middle">${title}</text>`;
    } else {
        svg += `<text x="${pW/2}" y="${mT+5}" font-family="${font}" font-size="${fs_mm*1.5}" font-weight="bold" text-anchor="middle">${title}</text>`;
    }

    page.forEach(item => {
        const c = item.color;
        svg += `<rect x="${item.x}" y="${item.y}" width="${sqW}" height="${sqH}" fill="${c.hex}" />`;
        let ty = item.y + sqH + tG + fs_mm;
        svg += `<text x="${item.x + sqW/2}" y="${ty}" font-family="${font}" font-size="${fs_mm}" text-anchor="middle">${c.name}</text>`;
        if(sC) { ty += fs_mm*1.3; svg += `<text x="${item.x + sqW/2}" y="${ty}" font-family="${font}" font-size="${fs_mm*0.85}" fill="#666" text-anchor="middle">CMYK: ${c.cmyk}</text>`; }
        if(sR) { ty += fs_mm*1.3; svg += `<text x="${item.x + sqW/2}" y="${ty}" font-family="${font}" font-size="${fs_mm*0.85}" fill="#666" text-anchor="middle">RGB: ${c.r},${c.g},${c.b}</text>`; }
        if(sH) { ty += fs_mm*1.3; svg += `<text x="${item.x + sqW/2}" y="${ty}" font-family="${font}" font-size="${fs_mm*0.85}" fill="#666" text-anchor="middle">HEX: ${c.hex}</text>`; }
    });

    return svg + `</svg>`;
}

// --- Exportação ---
async function exportPDF() {
    try {
        if (pagesData.length === 0) return alert("Importe XMLs primeiro.");
        
        // Detecção robusta da biblioteca jsPDF
        const jsPDFLib = (window.jspdf && window.jspdf.jsPDF) ? window.jspdf.jsPDF : (window.jsPDF || null);
        
        if (!jsPDFLib) {
            alert("Erro: Biblioteca PDF não carregada. Verifique se o arquivo jspdf.umd.min.js existe na pasta assets.");
            return;
        }

        const pW = parseFloat(document.getElementById('pageW').value);
        const pH = parseFloat(document.getElementById('pageH').value);
        const doc = new jsPDFLib({ orientation: pW > pH ? 'l' : 'p', unit: 'mm', format: [pW, pH] });

        for (let i = 0; i < pagesData.length; i++) {
            if (i > 0) doc.addPage([pW, pH], pW > pH ? 'l' : 'p');
            const svg = generateSVG(pagesData[i], pW, pH, 25, 25, 4, 8*0.352778, true, true, true);
            const img = new Image();
            await new Promise(res => {
                img.onload = () => {
                    const canvas = document.createElement('canvas');
                    canvas.width = img.width * 2; canvas.height = img.height * 2;
                    const ctx = canvas.getContext('2d');
                    ctx.fillStyle = 'white'; ctx.fillRect(0,0,canvas.width,canvas.height);
                    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
                    doc.addImage(canvas.toDataURL('image/jpeg', 0.95), 'JPEG', 0, 0, pW, pH);
                    res();
                };
                img.src = 'data:image/svg+xml;base64,' + btoa(unescape(encodeURIComponent(svg)));
            });
        }
        const b64 = doc.output('datauristring').split(',')[1];
        window.pybridge.save_file('Catalogo_Hero.pdf', b64, 'PDF Files (*.pdf)');
    } catch(e) { alert("Erro PDF: " + e); }
}

async function exportSVG() {
    try {
        if (pagesData.length === 0) return;
        const pW = parseFloat(document.getElementById('pageW').value);
        const pH = parseFloat(document.getElementById('pageH').value);
        
        if (pagesData.length > 1) {
            const JSZipLib = window.JSZip || (window.jszip ? window.jszip.JSZip : null);
            if (!JSZipLib) {
                alert("Erro: Biblioteca ZIP não encontrada.");
                return;
            }
            const zip = new JSZipLib();
            pagesData.forEach((p, i) => zip.file(`Pagina_${i+1}.svg`, generateSVG(p, pW, pH, 25, 25, 4, 2.8, true, true, true)));
            const b64 = await zip.generateAsync({type: 'base64'});
            window.pybridge.save_file('Catalogo_Hero.zip', b64, 'ZIP Files (*.zip)');
        } else {
            const svg = generateSVG(pagesData[0], pW, pH, 25, 25, 4, 2.8, true, true, true);
            window.pybridge.save_file('Catalogo_Hero.svg', btoa(unescape(encodeURIComponent(svg))), 'SVG Files (*.svg)');
        }
    } catch(e) { alert("Erro SVG: " + e); }
}

// --- Presets ---
function loadPresetsDropdown() {
    if (window.pybridge) {
        window.pybridge.get_presets(data => {
            try {
                const presets = JSON.parse(data);
                const sel = document.getElementById('presetSelect');
                if (sel) {
                    sel.innerHTML = '<option value="">Selecione...</option>';
                    Object.keys(presets).forEach(name => {
                        const opt = document.createElement('option');
                        opt.value = name; opt.textContent = name;
                        sel.appendChild(opt);
                    });
                }
            } catch (e) {
                console.error('Erro ao carregar presets:', e);
            }
        });
    } else {
        console.warn('pybridge ainda nao disponivel, tentando novamente...');
        setTimeout(loadPresetsDropdown, 500);
    }
}

function savePreset() {
    if (!window.pybridge) {
        console.error('pybridge nao disponivel para salvar preset');
        return;
    }
    const name = document.getElementById('presetName').value;
    if (!name) return alert("Dê um nome!");
    const data = {};
    document.querySelectorAll('input:not([type="file"])').forEach(i => { if(i.id) data[i.id] = i.value; });
    window.pybridge.save_preset(name, JSON.stringify(data), ok => { if(ok) loadPresetsDropdown(); });
}
