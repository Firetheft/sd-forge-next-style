let isLoading = false;
let nopreview = "";
let loadedStyleIDs = [];
let initialLoadComplete = false;
let isInitialized = false;
let nextCursor = null;

const tagMapping = {
    "NONE": "",
    "NO HUMANS": "116352",
    "MAN": "5232",
    "WOMAN": "5133",
    "OLD": "2043",
    "CHIBI": "5191",
    "CLOTHING": "5193",
    "CHINESE CLOTHES": "110731",
    "ARMOR": "5169",
    "WINGS": "3622",
    "MONSTER": "5668",
    "GIANT": "132433",
    "ROBOT": "6594",
    "ANIMAL": "111768",
    "CAT": "5132",
    "DOG": "2539",
    "DRAGON": "5499",
    "STILL LIFE": "124666",
    "FOOD": "3915",
    "WEAPON": "111782",
    "VEHICLE FOCUS": "162001",
    "TRAIN": "111988",
    "SHIP": "23049",
    "OUTDOORS": "111763",
    "CITY": "55",
    "BUILDING": "111794",
    "HOUSE": "1169",
    "EAST ASIAN ARCHITECTURE": "5768",
    "CASTLE": "111999",
    "NEON LIGHTS": "130825",
    "SCENERY": "2309",
    "WATER": "666",
    "FIRE": "1853",
    "RAIN": "520",
    "SNOW": "16188",
    "LIGHTNING": "5347",
    "FOG": "1284",
    "HORROR (THEME)": "161846",
    "ENGLISH TEXT": "161915",
    "PHOTOGRAPHY": "5241",
    "REALISTIC": "5248",
    "ANIME": "4",
    "FANTASY": "5207",
    "SCIENCE FICTION": "448",
    "SILHOUETTE": "112184",
    "GREYSCALE": "1675",
};

function resetAndReload() {
    nextCursor = null;
    loadedStyleIDs = [];
    const cardholderElement = document.getElementById("civitai_cardholder");
    cardholderElement.innerHTML = '';
    const params = getFilterParams();
    fetchCivitai(params.nsfw, params.sort, params.period, params.tags, params.username, params.international_version, nextCursor);
}

function getFilterParams() {
    const isGradio4 = gradioApp().querySelector('#civit_nsfwfilter > div > div > div > div > input') !== null;
    const selector = isGradio4 ? '> div > div > div > div > input' : '> label > div > div > div > input';

    const internationalVersionCheckbox = gradioApp().querySelector('#international_version_checkbox input');
    const internationalVersion = internationalVersionCheckbox ? internationalVersionCheckbox.checked : false;

    return {
        nsfw: gradioApp().querySelector(`#civit_nsfwfilter ${selector}`).value,
        sort: gradioApp().querySelector(`#civit_sortfilter ${selector}`).value,
        period: gradioApp().querySelector(`#civit_periodfilter ${selector}`).value,
        tags: gradioApp().querySelector(`#civit_tags_filter ${selector}`).value,
        username: gradioApp().querySelector('#civit_username_input > label > textarea').value,
        international_version: internationalVersion,
    };
}

function refreshfetchCivitai() {
    resetAndReload();
}

function civitaiaCursorLoad(elem) {
    if (elem.scrollTop + elem.clientHeight >= elem.scrollHeight - 50 && !isLoading && nextCursor) {
      console.log("scrolling event, loading next page with cursor: " + nextCursor);
        const params = getFilterParams();
        fetchCivitai(params.nsfw, params.sort, params.period, params.tags, params.username, params.international_version, nextCursor);
    }
}

function debounce(func, delay) {
    let timeout;
    return function(...args) {
        const context = this;
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(context, args), delay);
    };
}

const debouncedCivitaiaCursorLoad = debounce(civitaiaCursorLoad, 250);

async function fetchCivitai(nswflvl, sortcivit, periodcivit, tags, username, international_version, cursor) {
    const base_domain = international_version ? "civitai.com" : "civitai.work";
    const api_url = `https://${base_domain}/api/v1/images`;
    const card_base_url = `https://${base_domain}/images`;

    const cardholderElement = document.getElementById("civitai_cardholder");
    const loadingElement = document.getElementById("civitaiimages_loading");
    const errorMessageElement = gradioApp().querySelector("#civitai_error_message");

    loadingElement.style.display = "block";

    if (isLoading) {
        return;
    }

    isLoading = true;

    const params = new URLSearchParams({
        limit: 50,
        nsfw: nswflvl,
        sort: sortcivit,
        period: periodcivit,
        username: username,
    });

    if (cursor) {
        params.append('cursor', cursor);
    }

    if (tags && tagMapping[tags]) {
        params.append('tags', tagMapping[tags]);
    }

    try {
        const response = await fetch(`${api_url}?${params.toString()}`, {
            method: "GET",
            headers: {
                "Content-Type": "application/json",
            },
        });

        if (!response.ok) {
            throw new Error(`Request failed with status code: ${response.status}`);
        }

        const api_data = await response.json();
        const images = api_data.items || [];
        const showEmptyPrompt = gradioApp().querySelector('#show_empty_prompt input').checked;
        const blockedWords = ["xitheking","JinPing","xjnpng","crowded, blur, worried, long neck, nipples, blurry, red patch, sloppy, sketch, scribble, doodle, crooked teeth"];

        let htmlStrings = [];

        for (const item of images) {
            const meta_data = item.meta;
            const title = encodeHTML("by " + item.username);
            let img = item.thumbnail_url || item.url;

            if (!item.thumbnail_url && item.url) {
                try {
                    if (item.url.includes('/original=true/')) {
                        img = item.url.replace('/original=true/', '/width=450/');
                    } else {
                        const imageUrl = new URL(item.url);
                        const pathSegments = imageUrl.pathname.split('/');
                        let widthSegmentIndex = -1;

                        for (let i = 0; i < pathSegments.length; i++) {
                            if (pathSegments[i].startsWith('width=')) {
                                widthSegmentIndex = i;
                                break;
                            }
                        }

                        if (widthSegmentIndex !== -1) {
                            pathSegments[widthSegmentIndex] = 'width=450';
                            imageUrl.pathname = pathSegments.join('/');
                            img = imageUrl.toString();
                        } else {
                            try {
                                if (!imageUrl.pathname.includes('/width=')) {
                                    let parts = imageUrl.pathname.split('/');

                                    if (parts.length > 1) {
                                        parts.splice(parts.length - 1, 0, 'width=450');
                                        imageUrl.pathname = parts.join('/');
                                        img = imageUrl.toString();
                                    } else {
                                        img = item.url;
                                    }
                                } else {
                                    img = item.url;
                                }
                            } catch(err) {
                                console.warn("Failed to inject width, using original", item.url);
                                img = item.url;
                            }
                        }
                    }
                } catch (e) {
                    console.error("Error modifying image URL:", e);
                    img = item.url;
                }
            }

            const id = item.id;
            const description = encodeHTML(item.username + " " + item.id);
            let prompt = "";
            let prompt_negative = "";
            let steps = "";
            let sampling = "";
            let scheduler = "";
            let cfgScale = "";
            let seed = "";
            let Size = "";
            let Model = "";

            if (meta_data) {
                if ('prompt' in meta_data) {
                    prompt = encodeURIComponent(meta_data.prompt.replace(/'/g, '%27'));
                    if (blockedWords.some(word => meta_data.prompt.toLowerCase().includes(word.toLowerCase()))) {
                        continue;
                    }
                }
                if ('negativePrompt' in meta_data) {
                    prompt_negative = encodeURIComponent(meta_data.negativePrompt.replace(/'/g, '%27'));
                    if (blockedWords.some(word => meta_data.negativePrompt.toLowerCase().includes(word.toLowerCase()))) {
                        continue;
                    }
                }

                if ('steps' in meta_data) {
                    steps = encodeHTML(meta_data.steps);
                }

                if ('sampler' in meta_data) {
                    sampling = meta_data.sampler;
                    if (sampling.includes("Karras")) {
                        sampling = sampling.replace(/Karras/g, "").trim();
                        scheduler = "Karras";
                    }
                    else if (sampling === "euler") {
                        sampling = "Euler";
                    }
                    else if (sampling === "euler_ancestral") {
                        sampling = "Euler a";
                    }
                    else if (sampling === "dpmpp_2m") {
                        sampling = "DPM++ 2M";
                    }
                    else if (sampling === "deis") {
                        sampling = "DEIS";
                    }
                    else if (sampling === "ipndm") {
                        sampling = "IPNDM";
                    }
                    else if (sampling === "[Forge] Flux Realistic (Slow)") {
                        sampling = "[Forge] Flux Realistic";
                    }
                    else if (!meta_data.negativePrompt && sampling === "Undefined" && scheduler === "") {
                        sampling = "Euler";
                        scheduler = "Simple";
                    }
                    else if (sampling === "euler_simple") {
                        sampling = "Euler";
                        scheduler = "Simple";
                    }
                    else if (sampling === "euler simple") {
                        sampling = "Euler";
                        scheduler = "Simple";
                    }
                    else if (sampling === "euler_beta") {
                        sampling = "Euler";
                        scheduler = "Beta";
                    }
                    else if (sampling === "euler_ancestral_karras") {
                        sampling = "Euler a";
                        scheduler = "Karras";
                    }
                    else if (sampling === "dpmpp_2m_karras") {
                        sampling = "DPM++ 2M";
                        scheduler = "Karras";
                    }
                    else if (sampling === "dpmpp_2m_sde_karras") {
                        sampling = "DPM++ 2M SDE";
                        scheduler = "Karras";
                    }
                    else if (sampling === "dpmpp_sde_sgm_uniform") {
                        sampling = "DPM++ SDE";
                        scheduler = "SGM Uniform";
                    }
                    else if (sampling === "deis_beta") {
                        sampling = "DEIS";
                        scheduler = "Beta";
                    }
                    else if (sampling === "deis_ddim_uniform") {
                        sampling = "DEIS";
                        scheduler = "DDIM";
                    }
                    else if (sampling === "dpmpp_2m_sgm_uniform") {
                        sampling = "DPM++ 2M";
                        scheduler = "SGM Uniform";
                    }
                    else if (sampling === "dpmpp_2m_alt_ays+") {
                        sampling = "DPM++ 2M";
                        scheduler = "Align Your Steps";
                    }
                    else if (sampling === "dpmpp_3m_sde_gpu") {
                        sampling = "DPM++ 3M SDE";
                    }
                    sampling = encodeHTML(sampling);
                }

                if ('Schedule type' in meta_data) {
                    scheduler = meta_data["Schedule type"];
                    if (scheduler === "align_your_steps") {
                        scheduler = "Align Your Steps";
                    }
                    scheduler = encodeHTML(scheduler);
                }

                if ((!meta_data.negativePrompt || meta_data.negativePrompt.trim() === "" || meta_data.negativePrompt.toLowerCase() === "unknown")
                    && (!meta_data.Model || !meta_data.Model.includes("XL"))) {
                    cfgScale = encodeHTML("1");
                } else if (meta_data && 'cfgScale' in meta_data) {
                    cfgScale = encodeHTML(meta_data.cfgScale);
                }

                if ('seed' in meta_data) {
                    seed = encodeHTML(meta_data.seed);
                }

                if ('Size' in meta_data) {
                    Size = meta_data.Size;
                    if (Size === null || Size === undefined || Size.trim() === "") {
                        if (item.width && item.height) {
                            Size = `${item.width},${item.height}`;
                        } else {
                            Size = "Unknown";
                        }
                    } else {
                        Size = Size.replace('x', ',');
                    }
                    Size = encodeHTML(Size);
                } else if (item.width && item.height) {
                    Size = encodeHTML(`${item.width},${item.height}`);
                } else {
                    Size = encodeHTML("Unknown");
                }

                if ('Model' in meta_data) {
                    Model = encodeHTML(meta_data.Model);
                }
            }

            const styleID = `${item.id}`;
            if (loadedStyleIDs.indexOf(styleID) === -1 && (showEmptyPrompt || prompt && steps)) {
                const subfolder_name = encodeURIComponent("your_subfolder_name"); 
                const encoded_filename = encodeURIComponent("your_filename");
                
                let mediaHtml = "";
                if (item.type === "video") {
                    mediaHtml = `<video class="Civit_styles_thumbnail" src="${img}" autoplay loop muted playsinline webkit-playsinline style="object-fit: cover;"></video>`;
                } else {
                    mediaHtml = `<img class="Civit_styles_thumbnail" src="${img}" onerror="this.src='file=${nopreview}'">`;
                }

                let style_html = `
                    <div class="style_card" style="min-height:184px;max-height:184px;min-width:184px;max-width:184px;">
                        <div class="style_card_checkbox" onclick="toggleCardSelection(event, '${subfolder_name}','${encoded_filename}')">◉</div>
                        
                        ${mediaHtml}

                        <div class="EditStyleJson">
                            <button onclick="editStyle('${title}','${img}','${description}','${prompt}','${prompt_negative}','${steps}','${cfgScale}','${seed}','${Size}','${sampling}','${scheduler}','${subfolder_name}','${encoded_filename}','CivitAI')">🖉</button>
                        </div>
                        <div onclick="applyStyle('${prompt}','${prompt_negative}','${steps}','${cfgScale}','${seed}','${Size}','${sampling}','${scheduler}','CivitAI')" onmouseenter="event.stopPropagation(); hoverPreviewStyle('${prompt}','${prompt_negative}','CivitAI')" onmouseleave="hoverPreviewStyleOut()" class="styles_overlay"></div>
                        <div class="styles_title">${title}</div>
                        <p class="styles_description">
                            <span class="label">Steps:</span> <span class="value">${steps}</span><br>
                            <span class="label">Sampling:</span> <span class="value">${sampling}</span><br>
                            <span class="label">Scheduler:</span> <span class="value">${scheduler}</span><br>
                            <span class="label">CFG Scale:</span> <span class="value">${cfgScale}</span><br>
                            <span class="label">Seed:</span> <span class="value">${seed}</span><br>
                            <span class="label">Size:</span> <span class="value">${Size}</span><br>
                            <span class="label">Model:</span> <span class="value">${Model}</span>
                        </p>
                        <div style="position:absolute;bottom:5px;left:5px;display:flex;gap:4px;z-index:5;">
                            <div onclick="event.stopPropagation(); openCivitaiLightbox('${item.url}', '${item.type}')" class="view_all_button" style="cursor:pointer;font-size:14px;border-radius:4px;padding:2px 2px;color:white;line-height:1;" title="查看大图 (Lightbox)">🔍</div>
                            <a href="${card_base_url}/${id}" target="_blank" onclick="event.stopPropagation();" class="view_all_button" style="text-decoration:none;font-size:14px;border-radius:4px;padding:2px 2px;color:white;line-height:1;" title="跳转到 Civitai">🔗</a>
                        </div>
                    </div>`;
                htmlStrings.push(style_html);
                loadedStyleIDs.push(styleID);
            }
        }

        cardholderElement.innerHTML += htmlStrings.join("");

        if (api_data.metadata && api_data.metadata.nextCursor) {
            nextCursor = api_data.metadata.nextCursor;
        } else {
            nextCursor = null;
        }

        initialLoadComplete = true;

    } catch (error) {
        console.error(`An error occurred: ${error}`);
        if (errorMessageElement) {
            errorMessageElement.textContent = `Error fetching images: ${error.message}`;
        } else {
            console.warn("Error message element not found.  See console for details.")
        }
    } finally {
        isLoading = false;
        loadingElement.style.display = "none";
    }
}

function encodeHTML(str) {
    return String(str).replace(/[&<>"'`=/]/g, function(s) {
        return "&#" + s.charCodeAt(0) + ";";
    });
}

function setupcivitapi() {
    if (!isInitialized) {
        const cardholderElement = document.getElementById("civitai_cardholder");
        nopreview = encodeURIComponent(cardholderElement.getAttribute("data-nopreview"));

        const errorMessageElement = gradioApp().querySelector("#civitai_error_message");
        if (errorMessageElement) {
            errorMessageElement.textContent = "";
        }

        resetAndReload();
        document.getElementById('civitai_cardholder').addEventListener('scroll', (event) => debouncedCivitaiaCursorLoad(event.target));
        isInitialized = true;
    }
}

function openCivitaiLightbox(imageUrl, type) {
    let lightbox = document.getElementById('civitai-custom-lightbox');
    
    if (!lightbox) {
        lightbox = document.createElement('div');
        lightbox.id = 'civitai-custom-lightbox';
        lightbox.style.cssText = 'display:none;position:fixed;z-index:10000;left:0;top:0;width:100%;height:100%;overflow:auto;background-color:rgba(0,0,0,0.9);align-items:center;justify-content:center;';
        
        const closeBtn = document.createElement('span');
        closeBtn.innerHTML = '&times;';
        closeBtn.style.cssText = 'position:absolute;top:15px;right:35px;color:#f1f1f1;font-size:40px;font-weight:bold;transition:0.3s;cursor:pointer;z-index:10001;user-select:none;';
        closeBtn.onclick = function() { lightbox.style.display = 'none'; };
        
        lightbox.onclick = function(event) { 
            if (event.target === lightbox) {
                lightbox.style.display = 'none'; 
            }
        };

        const sendBtn = document.createElement('button');
        sendBtn.innerHTML = 'Send to Interrogate';
        sendBtn.style.cssText = `position: absolute; bottom: 30px; right: 35px; z-index: 10001; padding: 8px 16px; background-color: var(--ctp-accent); color: var(--ctp-minor); border: none; border-radius: 8px; font-weight: bold; cursor: pointer; font-size: 16px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); transition: transform 0.1s;`;
        sendBtn.onmouseover = function() { this.style.transform = 'scale(1.05)'; };
        sendBtn.onmouseout = function() { this.style.transform = 'scale(1)'; };
        sendBtn.onclick = function(event) {
            event.stopPropagation();
            const media = document.getElementById('civitai-custom-lightbox-media');
            if (media) sendToImg2Prompt(media.src);
        };
        lightbox.appendChild(sendBtn);

        const sendImg2ImgBtn = document.createElement('button');
        sendImg2ImgBtn.innerHTML = 'Send to Img2img';
        sendImg2ImgBtn.style.cssText = `position: absolute; bottom: 30px; right: 235px; z-index: 10001; padding: 8px 16px; background-color: var(--ctp-accent); color: var(--ctp-minor); border: none; border-radius: 8px; font-weight: bold; cursor: pointer; font-size: 16px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); transition: transform 0.1s;`;
        sendImg2ImgBtn.onmouseover = function() { this.style.transform = 'scale(1.05)'; };
        sendImg2ImgBtn.onmouseout = function() { this.style.transform = 'scale(1)'; };
        sendImg2ImgBtn.onclick = function(event) {
            event.stopPropagation();
            const media = document.getElementById('civitai-custom-lightbox-media');
            if (media) sendToMainImg2Img(media.src);
        };
        lightbox.appendChild(sendImg2ImgBtn);
        lightbox.appendChild(closeBtn);
        document.body.appendChild(lightbox);
    }
    
    const oldMedia = document.getElementById('civitai-custom-lightbox-media');
    if (oldMedia) oldMedia.remove();

    const oldImg = document.getElementById('civitai-custom-lightbox-img');
    if (oldImg) oldImg.remove();

    let newMedia;
    if (type === 'video') {
        newMedia = document.createElement('video');
        newMedia.controls = true;
        newMedia.autoplay = true;
        newMedia.loop = true;
    } else {
        newMedia = document.createElement('img');
    }
    
    newMedia.id = 'civitai-custom-lightbox-media';
    newMedia.src = imageUrl;
    newMedia.style.cssText = 'margin:auto;display:block;max-width:95%;max-height:95%;object-fit:contain;';
    
    lightbox.appendChild(newMedia);
    lightbox.style.display = 'flex';
}

function sendToImg2Prompt(imageUrl) {
    const transportBox = gradioApp().querySelector('#img2prompt_image_url_transport textarea');
    if (transportBox) {
        transportBox.value = imageUrl;
        transportBox.dispatchEvent(new Event('input', { bubbles: true }));
    } else {
        console.error("Stylez Error: Transfer text box not found #img2prompt_image_url_transport");
        return;
    }

    const stylezContainer = gradioApp().getElementById('Stylez');
    if (stylezContainer) {
        const tabButtons = stylezContainer.querySelectorAll('.tab-nav button');
        tabButtons.forEach(btn => {
            if (btn.innerText.includes("Interrogate") || btn.innerText.includes("反推")) {
                btn.click();
            }
        });
    }

    const lightbox = document.getElementById('civitai-custom-lightbox');
    if (lightbox) {
        lightbox.style.display = 'none';
    }
}

async function sendToMainImg2Img(imageUrl) {
    try {
        const response = await fetch(imageUrl);
        const blob = await response.blob();
        const file = new File([blob], "civitai_image.png", { type: blob.type });

        const img2imgInput = gradioApp().querySelector("#img2img_image input[type='file']");

        if (img2imgInput) {
            const dt = new DataTransfer();
            dt.items.add(file);
            img2imgInput.files = dt.files;
            
            img2imgInput.dispatchEvent(new Event('change', { bubbles: true }));
        } else {
            console.error("Stylez: The picture input box cannot be found #img2img_image");
            alert("The graph input box cannot be found, please confirm that the interface is loaded.");
            return;
        }

        const tabs = gradioApp().getElementById("tabs");
        if (tabs) {
            let tabBtn = null;
            tabBtn = tabs.querySelector('#tab_img2img-button');
            
            if (!tabBtn) {
                const buttons = tabs.querySelectorAll('.tab-nav button');
                buttons.forEach(btn => {
                    const text = btn.innerText.trim();
                    if (text === "Img2img" || text === "img2img" || text === "图生图") {
                        tabBtn = btn;
                    }
                });
            }

            if (tabBtn) {
                tabBtn.click();
            }
        }

        const lightbox = document.getElementById('civitai-custom-lightbox');
        if (lightbox) {
            lightbox.style.display = 'none';
        }

    } catch (e) {
        console.error("Stylez: Failed to send picture", e);
        alert("The image sending failed, possibly due to network problems or browser cross-domain restrictions.");
    }
}

setupcivitapi();