onUiLoaded(setupStylez);
let orgPrompt = '';
let orgNegative = '';
let tabname = '';
let promptNeg = '';
let promptPos = '';
let arwidth = '';
let arheight = '';

function clearStylezCardSelection() {
    const selectedCards = gradioApp().querySelectorAll('.style_card.selected');
    selectedCards.forEach(card => {
        card.classList.remove('selected');
        const checkbox = card.querySelector('.style_card_checkbox');
        if (checkbox) {
            checkbox.classList.remove('checked');
        }
    });
}

function setupStylez() {
    const t2i_StyleBtn = document.createElement("button");
    t2i_StyleBtn.setAttribute("class", "lg secondary gradio-button tool svelte-cmf5ev");
    t2i_StyleBtn.setAttribute("id", "t2i_stylez_btn");
    t2i_StyleBtn.setAttribute("onClick", "showHideStylez()");
    t2i_StyleBtn.innerText = `🎨`;
    const txt2img_tools = gradioApp().getElementById("txt2img_clear_prompt");
    if (txt2img_tools) {
        txt2img_tools.addEventListener('click', clearStylezCardSelection);
    }
    txt2img_tools.parentNode.appendChild(t2i_StyleBtn);
    const i2i_StyleBtn = document.createElement("button");
    i2i_StyleBtn.setAttribute("class", "lg secondary gradio-button tool svelte-cmf5ev");
    i2i_StyleBtn.setAttribute("id", "i2i_stylez_btn");
    i2i_StyleBtn.setAttribute("onClick", "showHideStylez()");
    i2i_StyleBtn.innerText = `🎨`;
    const img2img_tools = gradioApp().getElementById("img2img_clear_prompt");
    if (img2img_tools) {
        img2img_tools.addEventListener('click', clearStylezCardSelection);
    }
    img2img_tools.parentNode.appendChild(i2i_StyleBtn);
    const hideoldbar = gradioApp().querySelector('#hide_default_styles > label > input');
    if (hideoldbar.checked === true) {
        hideOldStyles(true);
    } else {
        hideOldStyles(false);
    }
    
    const t2i_stylez_container = gradioApp().querySelector("#Stylez");
    console.log(t2i_stylez_container)
    const tabs = gradioApp().getElementById("tabs");
    tabs.appendChild(t2i_stylez_container);
    const tabNav = document.querySelector(".tab-nav");
    if (tabNav) {
      const buttonTextToFind = "stylez_menutab";
      const buttons = tabNav.querySelectorAll("button.svelte-kqij2n");
      let styleztabbtn = null;
      buttons.forEach(button => {
        if (button.innerText.trim() === buttonTextToFind) {
            styleztabbtn = button;
        }
      });
      if (styleztabbtn) {
        styleztabbtn.style.display = "none";
      } 
    }
}

function hideOldStyles(bool) {
    if(bool == true){
        const stylesOld_t2i = gradioApp().getElementById("txt2img_styles_row");
        stylesOld_t2i.style.display = 'none';
        const stylesOld_i2i = gradioApp().getElementById("img2img_styles_row");
        stylesOld_i2i.style.display = 'none';
    } else {
        const stylesOld_t2i = gradioApp().getElementById("txt2img_styles_row");
        stylesOld_t2i.style.display = 'block';
        const stylesOld_i2i = gradioApp().getElementById("img2img_styles_row");
        stylesOld_i2i.style.display = 'block';
    }
}

function showHideStylez() {
    const stylez = gradioApp().getElementById("Stylez");
    const computedStyle = window.getComputedStyle(stylez);
    if (computedStyle.getPropertyValue("display") === "none" || computedStyle.getPropertyValue("visibility") === "hidden") {
        stylez.style.display = "block";
    } else {
        stylez.style.display = "none";
    }
}

function getENActiveTab() {
    let activetab = "";
    const tab = gradioApp().getElementById("tab_txt2img");
    const computedStyle = window.getComputedStyle(tab);
    if (computedStyle.getPropertyValue("display") === "none" || computedStyle.getPropertyValue("visibility") === "hidden") {
        activetab = "img2img";
    } else {
        activetab = "txt2img";
    }
    return (activetab);
}

function tabCheck(mutationsList, observer) {
    for (const mutation of mutationsList) {
        if (mutation.type === 'attributes' && mutation.attributeName === 'style') {
            const tabTxt2img = gradioApp().getElementById('tab_txt2img');
            const tabImg2img = gradioApp().getElementById('tab_img2img');
            const stylez = gradioApp().getElementById("Stylez");
            if (tabTxt2img.style.display === 'none') {
                stylez.style.display = "none";
                tabname = getENActiveTab();
                promptPos = gradioApp().querySelector(`#${tabname}_prompt > label > textarea`);
                promptNeg = gradioApp().querySelector(`#${tabname}_neg_prompt > label > textarea`);
            }
            if (tabImg2img.style.display === 'none') {
                stylez.style.display = "none";
                tabname = getENActiveTab();
                promptPos = gradioApp().querySelector(`#${tabname}_prompt > label > textarea`);
                promptNeg = gradioApp().querySelector(`#${tabname}_neg_prompt > label > textarea`);
            }
        }
    }
}

function checkElement() {
    const tabTxt2img = gradioApp().getElementById('tab_txt2img');
    if (tabTxt2img) {
        const observer = new MutationObserver(tabCheck);
        tabname = getENActiveTab();
        promptPos = gradioApp().querySelector(`#${tabname}_prompt > label > textarea`);
        promptNeg = gradioApp().querySelector(`#${tabname}_neg_prompt > label > textarea`);
        const tab_txt2img = gradioApp().getElementById('tab_txt2img');
        const tab_img2img = gradioApp().getElementById('tab_img2img');
        const config = {attributes: true};
        observer.observe(tab_txt2img, config);
        observer.observe(tab_img2img, config);
        const style_savefolder_temp = gradioApp().querySelector("#style_savefolder_temp > label > textarea");
        applyValues(style_savefolder_temp,"Styles")
        gradioApp().getElementById('style_save_btn').addEventListener('click', () => {
            saveRefresh();
        });
        gradioApp().getElementById('style_delete_btn').addEventListener('click', () => {
            deleteRefresh();
        });
        setupcivitapi()
    } else {
        setTimeout(checkElement, 100);
    }
}
checkElement();

function toggleCardSelection(event, folder, filename) {
    const card = event.target.closest('.style_card');
    const civitaiContainer = card.closest('#civitai_cardholder');
    
    if (civitaiContainer) {

        const selectedCards = civitaiContainer.querySelectorAll('.style_card.selected');
        selectedCards.forEach(otherCard => {

            if (otherCard !== card) {
                otherCard.classList.remove('selected');
                const otherCheckbox = otherCard.querySelector('.style_card_checkbox');
                if (otherCheckbox) {
                    otherCheckbox.classList.remove('checked');
                }
            }
        });
    }

    const checkbox = card.querySelector('.style_card_checkbox');
    checkbox.classList.toggle('checked');
    card.classList.toggle('selected');
    event.stopPropagation();
}

function applyStyle(prompt, negative, steps, cfgScale, seed, size, sampling, scheduler, origin) {
    const sendPromptsOnly = gradioApp().querySelector('#civitai_send_prompts_only input')?.checked;

    if (!sendPromptsOnly) {
        updatesampling(sampling, origin);
        updatescheduler(scheduler, origin);
    }
    const applyStylePrompt = gradioApp().querySelector('#styles_apply_prompt > label > input');
    const applyStyleNeg = gradioApp().querySelector('#styles_apply_neg > label > input');

    orgPrompt = promptPos.value;
    orgNegative = promptNeg.value;
    if (origin == "Stylez") {
        prompt = removeFirstAndLastCharacter(prompt)
        negative = removeFirstAndLastCharacter(negative)
        if(prompt.includes("{prompt}")) {
            const promptPossections = prompt.split("{prompt}");
            const promptPossectionA = promptPossections[0].trim();
            const promptPossectionB = promptPossections[1].trim();
            if (orgPrompt.includes(promptPossectionA) & orgPrompt.includes(promptPossectionB)) {
                orgPrompt = orgPrompt.replace(promptPossectionA,"");
                orgPrompt = orgPrompt.replace(promptPossectionB,"");
                orgPrompt = orgPrompt.replace(/^\s+/, "");
                orgPrompt = orgPrompt.replace(/^,+/g, "");
                orgPrompt = orgPrompt.replace(/^\s+/, "");
                if (applyStylePrompt.checked === true)
                {
                    applyValues(promptPos,orgPrompt)
                }
            } else {
                appendStyle(applyStylePrompt,prompt,orgPrompt,promptPos)
            }
        } else {
                if (prompt !== "") {
                    if (orgPrompt.includes(prompt) || orgPrompt.includes(", "+ prompt)) {
                        if(orgPrompt.includes(prompt)) {}
                        orgPrompt = orgPrompt.replace(", "+ prompt,"");
                        orgPrompt = orgPrompt.replace(prompt,"");
                        orgPrompt = orgPrompt.replace(/^\s+/, "");
                        orgPrompt = orgPrompt.replace(/^,+/g, "");
                        orgPrompt = orgPrompt.replace(/^\s+/, "");
                        if (applyStylePrompt.checked === true)
                        {
                            applyValues(promptPos,orgPrompt)
                        }
                    } else {
                        appendStyle(applyStylePrompt,prompt,orgPrompt,promptPos)
                    }
                }
            }
            if (negative !== "") {
                if (orgNegative.includes(negative) || orgNegative.includes(", "+ negative)) {
                    if(orgNegative.includes(negative)) {}
                    orgNegative = orgNegative.replace(", "+ negative,"");
                    orgNegative = orgNegative.replace(negative,"");
                    orgNegative = orgNegative.replace(/^\s+/, "");
                    orgNegative = orgNegative.replace(/^,+/g, "");
                    orgNegative = orgNegative.replace(/^\s+/, "");
                    if (applyStyleNeg.checked === true)
                    {
                        applyValues(promptNeg,orgNegative)
                    }
            
                } else {
                    appendStyle(applyStyleNeg,negative,orgNegative,promptNeg)
                }
            }
    } else {
        prompt = decodeURIComponent(prompt).replaceAll(/%27/g, "'")
        negative = decodeURIComponent(negative).replaceAll(/%27/g, "'")
        if (orgPrompt.includes(prompt) || orgPrompt.includes(", "+ prompt)) {
            if(orgPrompt.includes(prompt)) {}
            orgPrompt = ""
            if (applyStylePrompt.checked === true)
            {
                applyValues(promptPos,orgPrompt)
            }
        } else {
            appendStyle(applyStylePrompt,prompt,"",promptPos)
        }
        if (orgNegative.includes(negative) || orgNegative.includes(", "+ negative)) {
            if(orgNegative.includes(negative)) {}
            orgNegative = ""
            if (applyStyleNeg.checked === true)
            {
                applyValues(promptNeg,orgNegative)
            }
        } else {
            appendStyle(applyStyleNeg,negative,"",promptNeg)
        }
    }

    if ((origin === "Stylez" || origin == "CivitAI") && !sendPromptsOnly) {
        applyValueById(steps, 'steps');
        applyValueById(cfgScale, 'cfg_scale');
        applyValueById(seed, 'seed');

        if (size) {
            const [width, height] = size.split(",");
            applyValueById(width, "width");
            applyValueById(height, "height");
        }

        applyValueById(sampling, 'sampling');
        applyValueById(scheduler, 'scheduler');
    } 

    const card = event.target.closest('.style_card');

    toggleCardSelection(event, card.getAttribute('data-foldername'), card.getAttribute('data-filename'));
}

function updatesampling(sampling, origin) {
    if (origin === "Stylez" || origin == "CivitAI") {
        applyValueById(sampling, 'sampling');
    } 
}

function updatescheduler(scheduler, origin) {
    if (origin === "Stylez" || origin == "CivitAI") {
        applyValueById(scheduler, 'scheduler');
    } 
}

function applyValues(a, b) {
    if (!a) return;
    a.value = b;
    updateInput(a);
}

function applyValueById(value, idSuffix) {
    if (value) {
        const elementId = `${tabname}_${idSuffix}`;
        const element = gradioApp().querySelector(`#${elementId} input`); 
        if (element) {
            applyValues(element, value); 
            element.focus();
            const enterEvent = new KeyboardEvent('keydown', { key: 'Enter' });
            element.dispatchEvent(enterEvent);

            setTimeout(() => {
            }, 100);


        } else {
            console.error(`Element with ID ${elementId} not found.`);
        }
    }
}

function hoverPreviewStyle(prompt,negative,origin) {
    const enablePreviewChk = gradioApp().querySelector('#HoverOverStyle_preview > label > input');
    const enablePreview = enablePreviewChk.checked;
    if (enablePreview === true) { 
        previewbox = gradioApp().getElementById("stylezPreviewBoxid");
        previewbox.style.display = "block";
        if (origin == "Stylez") {
            prompt = removeFirstAndLastCharacter(prompt)
            negative = removeFirstAndLastCharacter(negative)
        } else {
            prompt = decodeURIComponent(prompt).replaceAll(/%27/g, "'")
            negative = decodeURIComponent(negative).replaceAll(/%27/g, "'")
        }
        if (prompt == ""){
            prompt = "NULL"
        }
        if (negative == ""){
            negative = "NULL"
        }

        prompt = prompt.replace(/\{([^}]+)\}/g, '<span style="color: var(--ctp-prompt);">{$1}</span>');
        negative = negative.replace(/\{([^}]+)\}/g, '<span style="color: var(--ctp-prompt);">{$1}</span>');
        pos = gradioApp().getElementById("stylezPreviewPositive");
        neg = gradioApp().getElementById("stylezPreviewNegative");
        pos.innerHTML = `<span style="color: var(--ctp-accent);">Prompt:</span> ${prompt}`;
        neg.innerHTML = `<span style="color: var(--ctp-accent);">Negative:</span> ${negative}`;
    }
}

function hoverPreviewStyleOut() {
    previewbox = gradioApp().getElementById("stylezPreviewBoxid");
    pos = gradioApp().getElementById("stylezPreviewPositive");
    neg = gradioApp().getElementById("stylezPreviewNegative");
    pos.textContent = "Prompt: ";
    neg.textContent = "Negative: ";
    previewbox.style.display = "none";
}

function appendStyle(applyStyle,prompt,oldprompt,promptbox) {
if (applyStyle.checked === true) {
        if (prompt.includes("{prompt}")) {
            oldprompt = promptbox.value;
            prompt = prompt.replace('{prompt}', oldprompt);
            promptbox.value = prompt;
            updateInput(promptbox);
        } else {
            if (oldprompt === '') {
                oldprompt = prompt;
                promptbox.value = prompt;
                updateInput(promptbox);
            } else {
                promptbox.value = oldprompt + ", " + prompt;
            }
            updateInput(promptbox);
        }
    }
}

function removeFirstAndLastCharacter(inputString) {
    if (inputString.length >= 2) {
        return inputString.slice(1, -1);
    } else {
        inputString = "";
        return inputString;
    }
}

function cardSizeChange(value) {
    const styleCards = gradioApp().querySelectorAll('#styles_libary .style_card');
    styleCards.forEach((card) => {
        card.style.minHeight = value + 'px';
        card.style.maxHeight = value + 'px';
        card.style.minWidth = value + 'px';
        card.style.maxWidth = value + 'px';
    });
}

function filterSearch(cat, search) {
    let searchString = search.toLowerCase();
    const styleCards = gradioApp().querySelectorAll('.style_card');
    if (searchString == "") {
        if (cat == "All") {
            styleCards.forEach(card => {
                card.style.display = "flex";
            });
        } else if (cat == "Favourites") {
            styleCards.forEach(card => {
                var btn = card.querySelector(".favouriteStyleBtn");
                let computedelem = getComputedStyle(btn);
                if (computedelem.color === "rgb(255, 255, 255)") {
                    card.style.display = "none";
                } else {
                    card.style.display = "flex";
                }
            });
        } else {
            styleCards.forEach(card => {
                const cardCategory = card.getAttribute('data-category');
                if (cardCategory == cat) {
                    card.style.display = "flex";
                } else {
                    card.style.display = "none";
                }
            });
        }
    } else {
        if (cat == "All") {
            styleCards.forEach(card => {
                const cardTitle = card.getAttribute('data-title');
                if (cardTitle.includes(searchString)) {
                    card.style.display = "flex";
                } else {
                    card.style.display = "none";
                }
            });
        } else if (cat == "Favourites") {
            styleCards.forEach(card => {
                const cardTitle = card.getAttribute('data-title');
                var btn = card.querySelector(".favouriteStyleBtn");
                let computedelem = getComputedStyle(btn);
                if (cardTitle.includes(searchString)) {
                    if (computedelem.color === "rgb(255, 255, 255)") {
                        card.style.display = "none";
                    } else {
                        card.style.display = "flex";
                    }
                } else {
                    card.style.display = "none";
                }
            });
        } else {
            styleCards.forEach(card => {
                const cardTitle = card.getAttribute('data-title');
                const cardCategory = card.getAttribute('data-category');
                if (cardTitle.includes(searchString) && cardCategory == cat) {
                    card.style.display = "flex";
                } else {
                    card.style.display = "none";
                }
            });
        }
    }
}

function editStyle(title, img, description, prompt, promptNeggative, steps, cfgScale, seed, size, sampling, scheduler, folder, filename, origin) {
    if (origin == "Stylez") {
        prompt = removeFirstAndLastCharacter(prompt)
        promptNeggative = removeFirstAndLastCharacter(promptNeggative)
    } else {
        prompt = decodeURIComponent(prompt).replaceAll(/%27/g, "'")
        promptNeggative = decodeURIComponent(promptNeggative.replaceAll(/%27/g, "'"))
    }
    
    const editorTitle = gradioApp().querySelector('#style_title_txt textarea');
    applyValues(editorTitle, title);
    
    const imgUrlHolderElement = gradioApp().querySelector('#style_img_url_txt textarea');
    applyValues(imgUrlHolderElement, img);
    
    const editorDescription = gradioApp().querySelector('#style_description_txt textarea');
    applyValues(editorDescription, description);
    
    const editorPrompt = gradioApp().querySelector('#style_prompt_txt textarea');
    applyValues(editorPrompt, prompt);
    
    const editorPromptNeggative = gradioApp().querySelector('#style_negative_txt textarea');
    applyValues(editorPromptNeggative, promptNeggative);
    
    const editorSteps = gradioApp().querySelector('#style_steps textarea') || gradioApp().querySelector('#style_steps input');
    applyValues(editorSteps, steps);
    
    const editorCfgScale = gradioApp().querySelector('#style_cfg_scale textarea') || gradioApp().querySelector('#style_cfg_scale input');
    applyValues(editorCfgScale, cfgScale);
    
    const editorSeed = gradioApp().querySelector('#style_seed textarea') || gradioApp().querySelector('#style_seed input');
    applyValues(editorSeed, seed);
    
    const editorSize = gradioApp().querySelector('#style_size textarea') || gradioApp().querySelector('#style_size input');
    applyValues(editorSize, size);
    
    const editorsampling = gradioApp().querySelector('#style_sampling textarea') || gradioApp().querySelector('#style_sampling input');
    applyValues(editorsampling, sampling);
    
    const editorScheduler = gradioApp().querySelector('#style_scheduler textarea') || gradioApp().querySelector('#style_scheduler input');
    applyValues(editorScheduler, scheduler);
    
    const editorSaveFolder = gradioApp().querySelector('#style_savefolder_txt input'); 
    const editorTempFolder = gradioApp().querySelector('#style_savefolder_temp textarea');
    applyValues(editorTempFolder, folder);
    applyValues(editorSaveFolder, folder);
    
    const editorFilename = gradioApp().querySelector('#style_filename_txt textarea');
    filename = decodeURIComponent(filename); 
    filename = filename.replace('.json', '');
    applyValues(editorFilename, filename);

    setTimeout(() => {
        const container = gradioApp().getElementById("Stylez");
        if (!container) return;

        const tabNav = container.querySelector('.tab-nav');
        if (!tabNav) {
            console.warn("[Stylez] Tab navigation not found");
            return;
        }

        const allButtons = tabNav.querySelectorAll('button');
        let targetBtn = null;

        const targetLabels = ["Edit", "编辑"];

        for (let btn of allButtons) {
            const t = btn.innerText.trim();
            if (targetLabels.includes(t)) {
                targetBtn = btn;
                break;
            }
        }

        if (targetBtn) {
            targetBtn.click();
            targetBtn.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
            targetBtn.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
        } else {
            console.warn("[Stylez] Jump failed: No tab named 'Edit' or '编辑' found. Please check if the panel is hidden.");
        }
    }, 100);
}

function grabLastGeneratedimage() {
    const imagegallery = gradioApp().querySelector(`#${tabname}_gallery`);
    if (imagegallery) {
        const firstImage = imagegallery.querySelector('img');
        if (firstImage) {
            let imageSrc = firstImage.src;
            imageSrc = imageSrc.replace(/.*file=/, '');
            imageSrc = imageSrc.split('?')[0];
            imageSrc = decodeURIComponent(imageSrc);
            const imgUrlHolderElement = gradioApp().querySelector('#style_img_url_txt > label > textarea');
            applyValues(imgUrlHolderElement, imageSrc);
        }
    }
}

function grabCurrentSettings() {
    const editorPrompt = gradioApp().querySelector('#style_prompt_txt > label > textarea');
    applyValues(editorPrompt, promptPos.value);

    const editorPromptNeggative = gradioApp().querySelector('#style_negative_txt > label > textarea');
    applyValues(editorPromptNeggative, promptNeg.value);

    const editorSteps = gradioApp().querySelector('#style_steps > label > textarea');
    applyValues(editorSteps, get_value_by_id("steps"));

    const editorCfgScale = gradioApp().querySelector('#style_cfg_scale > label > textarea');
    applyValues(editorCfgScale, get_value_by_id("cfg_scale"));

    const editorSeed = gradioApp().querySelector('#style_seed > label > textarea');
    applyValues(editorSeed, get_value_by_id("seed"));

    const editorSize = gradioApp().querySelector('#style_size > label > textarea');
    applyValues(editorSize, get_value_by_id_combined("width", "height"));

    const editorsampling = gradioApp().querySelector('#style_sampling > label > textarea');
    applyValues(editorsampling, get_value_by_id("sampling"));

    const editorScheduler = gradioApp().querySelector('#style_scheduler > label > textarea');
    applyValues(editorScheduler, get_value_by_id("scheduler"));
}

function get_value_by_id(idSuffix) {
    const elementId = `${tabname}_${idSuffix}`;
    const element = gradioApp().querySelector(`#${elementId} input`);
    if (element) {
        return element.value;
    } else {
        console.warn(`Element with ID ${elementId} not found.`);
        return null;
    }
}

function get_value_by_id_combined(idSuffix1, idSuffix2) {
    const value1 = get_value_by_id(idSuffix1);
    const value2 = get_value_by_id(idSuffix2);

    if (value1 !== null && value2 !== null) {
        return `${value1},${value2}`;
    } else {
        return null;
    }
}

function deleteRefresh() {
    const galleryrefresh = gradioApp().querySelector('#style_refresh');
    const stylesclear = gradioApp().querySelector('#style_clear_btn');
    galleryrefresh.click();
    stylesclear.click();
}

function saveRefresh() {
    setTimeout(() => {
        const galleryrefresh = gradioApp().querySelector('#style_refresh');
        galleryrefresh.click();
    }, 1000);
}

function addFavourite(folder, filename, element) {
    let computedelem = getComputedStyle(element);
    const addfavouritebtn = gradioApp().querySelector('#stylezAddFavourite');
    const removefavouritebtn = gradioApp().querySelector('#stylezRemoveFavourite');
    filename = decodeURIComponent(filename);
    const favTempFolder = gradioApp().querySelector('#favouriteTempTxt > label > textarea');
    if (computedelem.color === "rgb(255, 255, 255)") {
        element.style.color = "#EBD617";
        applyValues(favTempFolder, folder + "/" + filename);
        addfavouritebtn.click();
    } else {
        element.style.color = "#ffffff";
        applyValues(favTempFolder, folder + "/" + filename);
        removefavouritebtn.click();
    }
}

function addQuicksave () {
    const ulElement = gradioApp().getElementById('styles_quicksave_list');
    var liElement = document.createElement('li');
    var deleteButton = document.createElement('button');
    var innerButton = document.createElement('button');
    var promptParagraph = document.createElement('button');
    var negParagraph = document.createElement('button');
    let prompt = ""
    let negprompt = ""
    if (promptPos.value !== "" || promptNeg.value !== "") {
       
        if (promptPos.value == "")
        {
            promptParagraph.disabled = true  
            promptParagraph.textContent = "EMPTY"
            prompt = "EMPTY"
        }
        else {
            promptParagraph.disabled = false
            promptParagraph.textContent = promptPos.value;
            prompt = encodeURIComponent(promptPos.value);
        }
        if (promptNeg.value == "")
        {
            negParagraph.disabled = true
            negParagraph.textContent = "EMPTY"
            negprompt = "EMPTY"
        } else {
            negParagraph.disabled = false
            negParagraph.textContent = promptNeg.value;
            negprompt = encodeURIComponent(promptNeg.value)
        }
        liElement.className = 'styles_quicksave';
        deleteButton.className = 'styles_quicksave_del';
        deleteButton.textContent = '❌';
        deleteButton.onclick = function() {
            deletequicksave(this)
        };
        promptParagraph.onclick = function() {
            applyQuickSave("pos",this.textContent)
        };
        promptParagraph.onmouseenter = function() {
            event.stopPropagation(); 
            hoverPreviewStyle(promptParagraph.textContent,negParagraph.textContent,'Quicksave');
        }
        promptParagraph.onmouseleave = function() {
            hoverPreviewStyleOut()
        }
        promptParagraph.className = 'styles_quicksave_prompt styles_quicksave_btn';

        negParagraph.onclick = function() {
            applyQuickSave("neg",this.textContent)
        };
        negParagraph.onmouseenter = function() {
            event.stopPropagation(); 
            hoverPreviewStyle(promptParagraph.textContent,negParagraph.textContent,'Quicksave');
        }
        negParagraph.onmouseleave = function() {
            hoverPreviewStyleOut()
        }
        negParagraph.className = 'styles_quicksave_neg styles_quicksave_btn';
        innerButton.className = 'styles_quicksave_apply';
        innerButton.appendChild(promptParagraph);
        innerButton.appendChild(negParagraph);
        liElement.appendChild(deleteButton);
        liElement.appendChild(innerButton);
        ulElement.appendChild(liElement);
    }
}
function applyQuickSave(box,prompt) {
    tabname = getENActiveTab();
    if (box == "pos"){
        applyValues(promptPos,prompt)
    } else {
        applyValues(promptNeg,prompt)
    }
}

function deletequicksave(elem) {
    const quicksave = elem.parentNode;
    const list = quicksave.parentNode;
    list.removeChild(quicksave);
}

function clearquicklist() {
    const list = gradioApp().getElementById("styles_quicksave_list")
    while (list.firstChild) {
        list.removeChild(list.firstChild);
    }
}

function sendToPromtbox(prompt) {
    tabname = getENActiveTab();
    promptPos = gradioApp().querySelector(`#${tabname}_prompt > label > textarea`);
    applyValues(promptPos,prompt)
}

function applyGeneratedPrompt(htmlString) {
    const activeTab = getActiveTab();
    const promptBox = gradioApp().querySelector(`#${activeTab}_prompt > label > textarea`);

    if (!promptBox) {
        console.error(`Unable to find prompt box for ${activeTab} tab.`);
        return;
    }

    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = htmlString;

    const plainText = tempDiv.textContent || tempDiv.innerText || '';

    promptBox.value = plainText.trim();
    promptBox.dispatchEvent(new Event('input'));
}

function apply_colors_to_prompt(colors) {
    tabname = getENActiveTab();
    promptPos = gradioApp().querySelector(`#${tabname}_prompt > label > textarea`);

    if (promptPos) {
        let currentPrompt = promptPos.value.trim();
        let colorsToAdd = colors.trim();

        const colorRegexWithPrefix = /(Changes the color of the entire painting to a five-color palette:|Remap all visual tones across the composition to a constrained five-color system:).+\.$/i;
        const colorRegexWithoutPrefix = /,\s*[a-zA-Z\s,\.#_0-9-]*$/i;


        if (colorRegexWithPrefix.test(colorsToAdd)) {
            if (colorRegexWithPrefix.test(currentPrompt)) {
                promptPos.value = currentPrompt.replace(colorRegexWithPrefix, colorsToAdd);
            } else {
                promptPos.value = currentPrompt ? `${currentPrompt}, ${colorsToAdd}` : colorsToAdd;
            }
        } else {
            if (colorRegexWithoutPrefix.test(currentPrompt)) {
                promptPos.value = currentPrompt.replace(colorRegexWithoutPrefix, ", " + colorsToAdd);
            } else if (currentPrompt) {
                promptPos.value = currentPrompt + ", " + colorsToAdd;
            } else {
                promptPos.value = colorsToAdd;
            }
        }
        updateInput(promptPos);
    }
}

function apply_random_colors(colors) {
    for (let i = 0; i < colors.length; i++) {
        const colorPickerInput = gradioApp().querySelector(`#palette_color_${i + 1} input`);
        if (colorPickerInput) {
            colorPickerInput.value = colors[i];
            colorPickerInput.dispatchEvent(new Event("change"));
        }
    }
}

function stylesgrabprompt() {
    tabname = getENActiveTab();
    promptPos = gradioApp().querySelector(`#${tabname}_prompt > label > textarea`);
    return promptPos.value
}

function sendToARbox(width, height) {
    var arWidthTxt2Img = gradioApp().querySelector(`#txt2img_width input`);
    var arHeightTxt2Img = gradioApp().querySelector(`#txt2img_height input`);

    var arWidthImg2Img = gradioApp().querySelector(`#img2img_width input`);
    var arHeightImg2Img = gradioApp().querySelector(`#img2img_height input`);

    if (arWidthTxt2Img && arHeightTxt2Img) {
        arWidthTxt2Img.value = width;
        arHeightTxt2Img.value = height;
        arWidthTxt2Img.dispatchEvent(new Event('input'));
        arHeightTxt2Img.dispatchEvent(new Event('input'));
    } else {
        console.error("Unable to find txt2img width or txt2img height element");
    }

    if (arWidthImg2Img && arHeightImg2Img) {
        arWidthImg2Img.value = width;
        arHeightImg2Img.value = height;
        arWidthImg2Img.dispatchEvent(new Event('input'));
        arHeightImg2Img.dispatchEvent(new Event('input'));
    } else {
        console.error("Unable to find txt2img width or txt2img height element");
    }
}

function getActiveTab() {
    const txt2imgTab = gradioApp().querySelector('#tab_txt2img');
    const img2imgTab = gradioApp().querySelector('#tab_img2img');
    return txt2imgTab.style.display === 'none' ? 'img2img' : 'txt2img';
}

let currentSelectedSimplePromptButton = null;

function sendToPromptbox(prompt, clickedButton) {
    const activeTab = getActiveTab();
    const promptBox = gradioApp().querySelector(`#${activeTab}_prompt > label > textarea`);

    if (!promptBox) {
        console.error(`Unable to find prompt box for ${activeTab} tab`);
        return;
    }

    if (clickedButton) {
        clickedButton.classList.toggle('selected');
    }

    let selectedPrompts = [];
    const allPromptButtons = gradioApp().querySelectorAll('.simple-prompt-button');

    allPromptButtons.forEach(button => {
        if (button.classList.contains('selected')) {
            const promptTextElement = button.querySelector('.label-bottom');
            if (promptTextElement) {
                let currentButtonPrompt = promptTextElement.textContent.trim();
                if (!selectedPrompts.includes(currentButtonPrompt)) {
                    selectedPrompts.push(currentButtonPrompt);
                }
            }
        }
    });

    let newPrompt = selectedPrompts.join(', ');

    promptBox.value = newPrompt;
    promptBox.dispatchEvent(new Event('input'));
}

function applyThemePreset(colors) {
    const accentColorPicker = gradioApp().querySelector("#colorPickerRow .theme-color-picker:nth-child(1) input");
    const minorColorPicker = gradioApp().querySelector("#colorPickerRow .theme-color-picker:nth-child(2) input");

    if (accentColorPicker && minorColorPicker) {
        accentColorPicker.value = colors[0];
        minorColorPicker.value = colors[1];

        accentColorPicker.dispatchEvent(new Event("change"));
        minorColorPicker.dispatchEvent(new Event("change"));


    }
}

function updateStylezTheme(accent, minor) {
    if (!accent || !minor) return;
    
    document.documentElement.style.setProperty('--ctp-accent', accent);
    document.documentElement.style.setProperty('--ctp-minor', minor);
    document.body.style.setProperty('--ctp-accent', accent);
    document.body.style.setProperty('--ctp-minor', minor);
    
    const links = document.querySelectorAll('link[rel="stylesheet"]');
    links.forEach(link => {
        if (link.href && link.href.includes('sd-forge-next-style/style.css')) {
            const newUrl = new URL(link.href);
            newUrl.searchParams.set('t', Date.now());
            link.href = newUrl.toString();
        }
    });
}

processElements();
