let isModelLoading = false;
let modelNextCursor = null;
let lastDownloadInfo = null;
let activeDownloads = {};
let progressInterval = null;

function prepareCivitaiModelsFetch() {
    isModelLoading = false;
    modelNextCursor = null;
    const cardholder = document.getElementById("civitai_models_cardholder");
    if(cardholder) cardholder.innerHTML = '';
    triggerServerFetch(null);
}

function getModelFilterParams() {
    const isGradio4 = gradioApp().querySelector('#cm_type_filter > div > div > div > div > input') !== null;
    const selector = isGradio4 ? '> div > div > div > div > input' : '> label > div > div > div > input';
    const checkboxSelector = isGradio4 ? 'input' : 'label > input';

    return {
        type: gradioApp().querySelector(`#cm_type_filter ${selector}`).value,
        sort: gradioApp().querySelector(`#cm_sort_filter ${selector}`).value,
        period: gradioApp().querySelector(`#cm_period_filter ${selector}`).value,
        baseModel: gradioApp().querySelector(`#cm_basemodel_filter ${selector}`).value,
        query: gradioApp().querySelector('#cm_search_input > label > textarea').value,
        nsfw: gradioApp().querySelector(`#cm_nsfw_checkbox ${checkboxSelector}`).checked
    };
}

function civitaiModelsCursorLoad(elem) {
    if (elem.scrollTop + elem.clientHeight >= elem.scrollHeight - 300 && !isModelLoading && modelNextCursor) {
        triggerServerFetch(modelNextCursor);
    }
}

function debounceModel(func, delay) {
    let timeout;
    return function(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), delay);
    };
}
const debouncedModelScroll = debounceModel(civitaiModelsCursorLoad, 250);

function triggerServerFetch(cursor) {
    if (isModelLoading) return;
    isModelLoading = true;
    const loadingElement = document.getElementById("civitaimodels_loading");
    if (loadingElement) loadingElement.style.display = "block";

    setTimeout(() => {
        if (isModelLoading) {
            console.log("Civitai Models fetch timed out, forcing unlock.");
            isModelLoading = false;
            if (loadingElement) loadingElement.style.display = "none";
        }
    }, 15000);

    const params = getModelFilterParams();
    params.cursor = cursor;

    const inputParam = gradioApp().querySelector("#cm_server_params_input textarea");
    if (inputParam) {
        inputParam.value = JSON.stringify(params);
        inputParam.dispatchEvent(new Event("input", { bubbles: true }));
    }
    const fetchBtn = gradioApp().getElementById("cm_server_fetch_btn");
    if (fetchBtn) setTimeout(() => fetchBtn.click(), 50);
}

function renderCivitaiModelsFromJSON(jsonStr) {
    const cardholderElement = document.getElementById("civitai_models_cardholder");
    const loadingElement = document.getElementById("civitaimodels_loading");
    isModelLoading = false;
    if (loadingElement) loadingElement.style.display = "none";

    if (!jsonStr) return;
    const data = JSON.parse(jsonStr);

    if (data.error) {
        cardholderElement.innerHTML += `<div style="color:red; padding:20px; text-align:center;">Error: ${data.error}</div>`;
        return;
    }

    const models = data.items || [];
    if (models.length === 0 && !modelNextCursor) {
        cardholderElement.innerHTML = `<div style="color:white; padding:20px; text-align:center;">No models found.</div>`;
        return;
    }

    let htmlStrings = [];
    const nopreview = cardholderElement.getAttribute("data-nopreview") || "";

    models.forEach(item => {
        const latestVersion = item.modelVersions && item.modelVersions[0];
        if (!latestVersion) return;

        let filename = `${item.name}_${latestVersion.name}`.replace(/[^a-zA-Z0-9_-]/g, '_');
        if (latestVersion.files && latestVersion.files.length > 0) {
            filename = latestVersion.files[0].name;
        }

        let imageUrl = "";
        if (latestVersion.images && latestVersion.images.length > 0) {
            imageUrl = latestVersion.images[0].url;
            imageUrl = imageUrl.replace('/original=true/', '/width=450/');
        }
        
        const downloadData = JSON.stringify({
            url: latestVersion.downloadUrl,
            filename: filename,
            type: item.type,
            name: item.name,
            image_url: imageUrl
        }).replace(/"/g, '&quot;');

        let mediaHtml = `<img class="Civit_styles_thumbnail" src="file=${nopreview}" style="width:100%; height:100%; object-fit:cover;">`;
        
        if (latestVersion.images && latestVersion.images.length > 0) {
            const firstImg = latestVersion.images[0];
            let imgUrl = imageUrl;

            if (firstImg.type === "video") {
                mediaHtml = `<video class="Civit_styles_thumbnail" src="${imgUrl}" autoplay loop muted playsinline webkit-playsinline style="width:100%; height:100%; object-fit:cover;"></video>`;
            } else {
                mediaHtml = `<img class="Civit_styles_thumbnail" src="${imgUrl}" onerror="this.src='file=${nopreview}'" style="width:100%; height:100%; object-fit:cover;" loading="lazy">`;
            }
        }

        const isDownloaded = item.isDownloaded;
        
        let btnColor = isDownloaded ? "#5151512a" : "#5151512a";
        let btnIcon = isDownloaded ? "✅" : "⬇️";
        let btnTitle = isDownloaded ? "Model already exists" : "Download the model to Forge";
        let btnCursor = isDownloaded ? "default" : "pointer";
        let btnAction = isDownloaded ? 
            `alert('Model [${item.name}] It already exists in the library, no need to download it again.')` : 
            `confirmAndDownload(this, '${downloadData}')`;

        let html = `
        <div class="style_card" style="min-height:260px; max-height:260px; min-width:184px; max-width:184px; position: relative;">
            <div style="height:184px; width:100%; overflow:hidden;">
                ${mediaHtml}
            </div>
            <div style="position:absolute; top:5px; right:5px; background:rgba(0,0,0,0.7); color:white; padding:2px 5px; font-size:10px; border-radius:4px;">${item.type}</div>
            
            <div style="padding: 5px; color: white; font-size: 12px; height: 70px; overflow: hidden; background: rgba(0,0,0,0.5); width: 100%;">
                <div style="font-weight: bold; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${item.name}</div>
                <div style="font-size: 10px; color: #ccc;">Ver: ${latestVersion.name}</div>
                <div style="font-size: 10px; margin-top: 2px;">❤️ ${item.stats.thumbsUpCount || item.stats.favoriteCount || 0} ⬇️ ${item.stats.downloadCount}</div>
            </div>
            
            <div class="EditStyleJson" style="background-color: ${btnColor} !important; cursor: ${btnCursor};" 
                 onclick="${btnAction}" title="${btnTitle}">
                <span style="font-size: 16px; color: black; font-weight: bold;">${btnIcon}</span>
            </div>
            
            <div style="position:absolute; bottom:80px; left:5px;">
                <a href="https://civitai.com/models/${item.id}" target="_blank" onclick="event.stopPropagation();" style="text-decoration:none; font-size:16px;">🔗</a>
            </div>
        </div>`;
        htmlStrings.push(html);
    });

    cardholderElement.innerHTML += htmlStrings.join("");

    if (data.metadata && data.metadata.nextCursor) {
        modelNextCursor = data.metadata.nextCursor;
    } else {
        modelNextCursor = null;
    }
}

function confirmAndDownload(btnElement, jsonStr) {
    const data = JSON.parse(jsonStr);
    const modelName = data.name || "The model";
    const fileName = data.filename;
    
    if (btnElement.getAttribute('data-downloading-id')) {
        const taskId = btnElement.getAttribute('data-downloading-id');
        showProgressModal(taskId, modelName);
        return;
    }

    const confirmed = confirm(`Confirm download model：\n\n${modelName}\n(${fileName})\n\nThe download will take place in the background.`);
    
    if (confirmed) {
        if(btnElement) {
            btnElement.style.backgroundColor = "#AAA";
            btnElement.innerHTML = '<span class="rotating-icon" style="font-size: 16px; color: black; font-weight: bold;">⏳</span>';
            window.lastClickDownloadBtn = btnElement; 
        }
        triggerCivitaiDownload(jsonStr);
    }
}

function triggerCivitaiDownload(jsonStr) {
    lastDownloadInfo = jsonStr;
    const infoBox = gradioApp().querySelector("#cm_download_info_box textarea");
    if (infoBox) {
        infoBox.value = jsonStr;
        infoBox.dispatchEvent(new Event("input", { bubbles: true })); 
    }
    const btn = gradioApp().getElementById("cm_download_trigger_btn");
    if (btn) btn.click();
}

function handleConfigSaveLog(logText) {
    if (!logText) return;
    
    try {
        if (logText.startsWith("{") && logText.includes("task_id")) {
            const data = JSON.parse(logText);
            if (data.status === "started") {
                const btn = window.lastClickDownloadBtn;
                if (btn) {
                    const taskId = data.task_id;
                    activeDownloads[taskId] = {
                        btn: btn,
                        name: data.filename,
                        status: 'running'
                    };
                    btn.setAttribute('data-downloading-id', taskId);
                    btn.title = "Click to view download progress /abort download";
                    btn.onclick = () => showProgressModal(taskId, data.filename);
                    
                    startPolling();
                }
            }
            return; 
        }
    } catch(e) {}

    if (logText === "MISSING_KEY_CIVITAI") {
        showConfigModal("CIVITAI_API_KEY", "Civitai API Key", "Downloading this model requires API Key。");
    } else if (logText === "CONFIG_SAVED") {
        alert("Configuration saved!");
        closeConfigModal();
        if (lastDownloadInfo) triggerCivitaiDownload(lastDownloadInfo);
    } else if (logText.startsWith("File already exists")) {
        alert(logText);
        if (window.lastClickDownloadBtn) {
             window.lastClickDownloadBtn.innerHTML = '<span style="font-size: 16px; color: black; font-weight: bold;">✅</span>';
             window.lastClickDownloadBtn.style.backgroundColor = "#5151512a";
        }
    } else {
        alert(logText);
    }
}

function checkPromptGenError(htmlContent) {
    if (htmlContent.includes("MISSING_KEY_GEMINI")) {
        lastDownloadInfo = null;
        showConfigModal("GEMINI_API_KEY", "Gemini API Key", "Using Gemini to expand prompt words requires an API Key.");
    } else if (htmlContent.includes("MISSING_KEY_ZHIPU")) {
        lastDownloadInfo = null;
        showConfigModal("ZHIPUAI_API_KEY", "ZhipuAI API Key", "Using ZhipuAI to expand prompt words requires an API Key.");
    }
}

function showConfigModal(configKey, title, desc) {
    let modal = document.getElementById('stylez-config-modal');
    if (!modal) {
        const modalHTML = `
            <div id="stylez-config-modal" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.7); z-index:10000; align-items:center; justify-content:center;">
                <div style="background:var(--body-background-fill); padding:20px; border-radius:10px; width:400px; box-shadow:0 0 10px rgba(0,0,0,0.5); border:1px solid var(--border-color-primary);">
                    <h3 id="stylez-modal-title" style="margin-top:0; color:var(--body-text-color);">API Key Setting</h3>
                    <p id="stylez-modal-desc" style="font-size:12px; color:var(--body-text-color-subdued); margin-bottom:10px;"></p>
                    <input type="text" id="stylez-modal-input" placeholder="paste here Key..." style="width:100%; padding:8px; margin-bottom:15px; background:var(--input-background-fill); color:var(--body-text-color); border:1px solid var(--input-border-color); border-radius:4px;">
                    <div style="display:flex; justify-content:flex-end; gap:10px;">
                        <button onclick="closeConfigModal()" style="padding:5px 15px; cursor:pointer; background:var(--button-secondary-background-fill); color:var(--button-secondary-text-color); border:none; border-radius:4px;">Cancel</button>
                        <button id="stylez-modal-save-btn" style="padding:5px 15px; cursor:pointer; background:var(--button-primary-background-fill); color:var(--button-primary-text-color); border:none; border-radius:4px;">Save</button>
                    </div>
                </div>
            </div>
        `;
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        modal = document.getElementById('stylez-config-modal');
    }

    document.getElementById('stylez-modal-title').innerText = title;
    document.getElementById('stylez-modal-desc').innerText = desc;
    if (modal.style.display === 'none') {
        document.getElementById('stylez-modal-input').value = "";
    }
    
    const saveBtn = document.getElementById('stylez-modal-save-btn');
    saveBtn.onclick = () => {
        const val = document.getElementById('stylez-modal-input').value.trim();
        if(!val) { alert("Content cannot be empty"); return; }
        
        const keyInput = gradioApp().querySelector("#global_config_key_input textarea");
        const valInput = gradioApp().querySelector("#global_config_value_input textarea");
        
        if(keyInput && valInput) {
            keyInput.value = configKey;
            valInput.value = val;
            keyInput.dispatchEvent(new Event("input", { bubbles: true }));
            valInput.dispatchEvent(new Event("input", { bubbles: true }));
            
            const btn = gradioApp().getElementById("global_config_save_btn");
            if(btn) btn.click();
        }
    };

    modal.style.display = 'flex';
}

function closeConfigModal() {
    const modal = document.getElementById('stylez-config-modal');
    if(modal) modal.style.display = 'none';
}

document.addEventListener("DOMContentLoaded", () => {
    setTimeout(() => {
        const holder = document.getElementById('civitai_models_cardholder');
        if (holder) {
            holder.addEventListener('scroll', (event) => debouncedModelScroll(event.target));
            if (!holder.innerHTML.trim()) prepareCivitaiModelsFetch();
        }
    }, 1500);
});

function startPolling() {
    if (progressInterval) return;
    progressInterval = setInterval(() => {
        const btn = gradioApp().getElementById("dl_check_btn");
        if (btn) btn.click();
        
        if (Object.keys(activeDownloads).length === 0) {
            clearInterval(progressInterval);
            progressInterval = null;
        }
    }, 1500);
}

function onDownloadProgressUpdate(jsonStr) {
    if (!jsonStr) return;
    const allTasks = JSON.parse(jsonStr);
    
    for (const [taskId, taskInfo] of Object.entries(activeDownloads)) {
        const remoteTask = allTasks[taskId];
        if (!remoteTask) continue;
        
        const btn = taskInfo.btn;
        const modal = document.getElementById('civitai-progress-modal');
        const currentModalTask = modal ? modal.getAttribute('data-task-id') : null;

        if (remoteTask.status === "completed") {
            btn.innerHTML = '<span style="font-size: 16px; color: black; font-weight: bold;">✅</span>';
            btn.title = "Download completed";
            btn.removeAttribute('data-downloading-id');
            btn.onclick = () => alert('The model has been downloaded.');
            btn.style.backgroundColor = "#5151512a";
            
            if (currentModalTask === taskId) closeProgressModal();
            delete activeDownloads[taskId];
            
        } else if (remoteTask.status === "error" || remoteTask.status === "aborted") {
            btn.innerHTML = '<span style="font-size: 16px; color: black; font-weight: bold;">⬇️</span>';
            btn.title = "Download failed or aborted";
            btn.removeAttribute('data-downloading-id');
            btn.setAttribute("onclick", `confirmAndDownload(this, '${JSON.stringify({url: "", filename: taskInfo.name, type: "", name: taskInfo.name}).replace(/"/g, '&quot;')}')`);
            btn.style.backgroundColor = "#5151512a";
            
            if (currentModalTask === taskId) {
                alert(`Download stopped: ${remoteTask.msg || remoteTask.status}`);
                closeProgressModal();
            }
            delete activeDownloads[taskId];

        } else if (remoteTask.status === "running") {
            const percent = remoteTask.total > 0 ? Math.round((remoteTask.progress / remoteTask.total) * 100) : 0;
            const sizeMB = (remoteTask.progress / 1024 / 1024).toFixed(1);
            const totalMB = (remoteTask.total / 1024 / 1024).toFixed(1);
            
            if (currentModalTask === taskId) {
                document.getElementById('dl-progress-bar').style.width = percent + "%";
                document.getElementById('dl-progress-text').innerText = `${percent}% (${sizeMB}MB / ${totalMB}MB)`;
            }
        }
    }
}

function showProgressModal(taskId, modelName) {
    let modal = document.getElementById('civitai-progress-modal');
    if (!modal) {
        const modalHTML = `
            <div id="civitai-progress-modal">
                <div class="progress-modal-content">
                    <h3 style="color:var(--body-text-color);">Downloading...</h3>
                    <p id="dl-model-name" style="color:var(--body-text-color-subdued); margin-bottom:10px;"></p>
                    <div class="progress-bar-container">
                        <div id="dl-progress-bar" class="progress-bar-fill"></div>
                    </div>
                    <p id="dl-progress-text" style="color:var(--body-text-color); font-weight:bold;">0%</p>
                    <div style="margin-top:20px; display:flex; justify-content:center; gap:10px;">
                        <button onclick="abortCurrentDownload()" style="padding:5px 15px; background:var(--ctp-red); color:white; border:none; border-radius:4px; cursor:pointer;">Abort download</button>
                        <button onclick="closeProgressModal()" style="padding:5px 15px; background:var(--button-secondary-background-fill); color:var(--body-text-color); border:none; border-radius:4px; cursor:pointer;">close window</button>
                    </div>
                </div>
            </div>
        `;
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        modal = document.getElementById('civitai-progress-modal');
    }
    
    modal.setAttribute('data-task-id', taskId);
    document.getElementById('dl-model-name').innerText = modelName;
    document.getElementById('dl-progress-bar').style.width = "0%";
    document.getElementById('dl-progress-text').innerText = "loading...";
    modal.style.display = 'flex';
}

function closeProgressModal() {
    const modal = document.getElementById('civitai-progress-modal');
    if (modal) {
        modal.style.display = 'none';
        modal.removeAttribute('data-task-id');
    }
}

function abortCurrentDownload() {
    const modal = document.getElementById('civitai-progress-modal');
    const taskId = modal ? modal.getAttribute('data-task-id') : null;
    if (!taskId) return;
    
    if (confirm("Are you sure you want to abort this task?")) {
        const input = gradioApp().querySelector("#dl_abort_id_input textarea");
        if (input) {
            input.value = taskId;
            input.dispatchEvent(new Event("input", { bubbles: true }));
            const btn = gradioApp().getElementById("dl_abort_btn");
            if (btn) btn.click();
        }
    }
}