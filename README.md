# SD-Forge-Next-Style

SD-Forge-Next-Style is an all-in-one style and prompt management extension designed specifically for [Stable Diffusion WebUI Forge](https://github.com/Firetheft/sd-webui-forge-neo). It integrates style library management, CivitAI resource browsing and downloading, LLM prompt expansion, image interrogation, and various auxiliary generation tools, aiming to provide a seamless workflow experience.
![QQ20251227-202517](https://github.com/user-attachments/assets/ba94f278-1c17-4bcb-a972-b04693aca68e)

## ✨ Key Features

### 1. 🎨 Styles Library Management
* **Visual Management**: Display styles in card format with thumbnail previews.
* **One-Click Application**: Click on a card to apply Prompts, Negative Prompts, and generation parameters to the Txt2Img or Img2Img interface.
* **Edit & Create**: Support creating, editing, and deleting styles directly in the UI. You can fetch parameters from the current generation settings or the last generated image.
* **Favorites**: Pin frequently used styles to favorites; supports filtering and searching.
<img width="1887" height="1067" alt="QQ20251227-203008" src="https://github.com/user-attachments/assets/81d63bf6-fd44-4431-b140-f103ea02bcaa" />

### 2. 🤖 Prompt Extend
* **Multi-Model Support**: Built-in support for **Local-Qwen** (runs locally), **Google Gemini API**, and **ZhipuAI API**.
* **Various Presets**: Provides multiple expansion modes including Photography, Art, Tags, NSFW, and English-Chinese translation.
* **Auto-Translation**: Capable of expanding simple natural language into detailed, high-quality prompts.
<img width="1251" height="940" alt="QQ20251227-203431" src="https://github.com/user-attachments/assets/ecfff8cd-8182-40e2-bc56-d81a7bbff191" />

### 3. 👁️ Interrogate (Image to Prompt)
* **Multimodal Models**: Supports using **Qwen-VL** (Local), **Gemini Vision**, and **GLM-4v** models for image analysis.
* **Multiple Analysis Modes**: Generate Tags, Natural Language Descriptions, Art Style Analysis, Detailed NSFW Descriptions, etc.
* **One-Click Send**: Generated prompts can be directly sent to Txt2Img or Img2Img input boxes.
<img width="1267" height="1012" alt="QQ20251227-203903" src="https://github.com/user-attachments/assets/e96bb684-ca6d-43fb-a27f-9946a014e583" />

### 4. 🌐 CivitAI Integration
* **CivitMD (Model Browser)**: Browse CivitAI models (Checkpoints, LoRAs, VAEs, etc.) directly within the extension.
    * Filter by type, base model, and sorting options.
    * **One-Click Download**: Supports background downloading of models and preview images, automatically installing them to the correct directories.
    * **Status Detection**: Automatically detects if a model is already installed locally.
<img width="1259" height="1062" alt="QQ20251227-204428" src="https://github.com/user-attachments/assets/19db310a-3c87-4091-8c4a-7f70db3809fa" />

* **CivitAI (Image Browser)**: Browse excellent images from the CivitAI community.
    * **"Copy Work"**: One-click application of an image's prompts and generation parameters.
    * Filter by tags, sorting, period, and NSFW toggles.
<img width="1883" height="1069" alt="QQ20251227-204616" src="https://github.com/user-attachments/assets/dd02294e-dbc9-45c8-a73d-841c12a0ecd2" />

### 5. 🛠️ Auxiliary Tools
* **Prompts (Library)**: Built-in common prompt buttons, categorized for easy access. Click to add to the input box.
* **Size (Presets)**: Provides aspect ratio presets for SDXL, SD1.5, and common cinematic/widescreen formats.
* **Palette**: Extract or randomly generate 5-color palettes and convert them into prompts to control the image tone.
* **Theme**: Customize the extension's theme colors (Accent & Neutral), perfectly adapting to Forge's Dark/Light modes.
<img width="1244" height="858" alt="QQ20251227-204716" src="https://github.com/user-attachments/assets/e4bb1eab-3501-489f-823e-f1401e9c0640" />

## 📥 Installation

1. Open Stable Diffusion WebUI Forge.
2. Go to the **Extensions** tab.
3. Click on **Install from URL**.
4. Enter the repository URL in **URL for extension's git repository**:
```https://github.com/Firetheft/sd-forge-next-style```
5. Click **Install**.
6. Restart the WebUI.

## ⚙️ Configuration

Some features (like online LLM services and CivitAI downloads) require API Keys. You can configure them using one of the following methods:

**Method 1: Automatic Pop-up (Recommended)**
Simply try to use a feature that requires an API Key. An input box will automatically pop up asking you to enter it.
* **CivitAI API Key**: Triggered when you click the "Download" button in the **CivitMD** tab for the first time.
* **Gemini/ZhipuAI API Key**: Triggered when you use the **Extend** or **Interrogate** features with these models selected for the first time.
<img width="676" height="293" alt="QQ20251227-203242" src="https://github.com/user-attachments/assets/cd106372-fb73-4116-b5ef-b9e0f777ab3b" />

**Method 2: Manual Configuration**
You can also manually edit the configuration file located at `extensions/sd-forge-next-style/scripts/config.json`:
```json
{
    "GEMINI_API_KEY": "Your_Gemini_API_Key",
    "ZHIPUAI_API_KEY": "Your_Zhipu_API_Key",
    "CIVITAI_API_KEY": "Your_CivitAI_API_Key",
    "PROXY": "Your_Proxy_Address(Optional)"
}
```

## ⚠️ Notes

Local Models: When using Local-Qwen for expansion or interrogation, model files will be downloaded automatically. Please ensure you have enough disk space and a proper network environment.

Dependencies: If you encounter a qwen-vl-utils missing error, please manually run pip install qwen-vl-utils in your terminal.

## 🤝 Contribution

Issues and Pull Requests are welcome to improve this project!
