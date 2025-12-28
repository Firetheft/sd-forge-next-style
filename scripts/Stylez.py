import os
import html
import datetime
import urllib.parse
import gradio as gr
from PIL import Image, ImageOps
import shutil
import json
import csv
import re
import random
import requests
import hashlib
import pandas as pd
import torch
import gc
import base64
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, AutoProcessor, Qwen3VLForConditionalGeneration
from modules import scripts, shared, script_callbacks
from modules import (
    generation_parameters_copypaste as parameters_copypaste,
)
try:
    from modules.call_queue import wrap_gradio_gpu_call
except ImportError:
    from webui import wrap_gradio_gpu_call
from pathlib import Path
from huggingface_hub import snapshot_download
from modules.scripts import basedir
from modules import paths_internal, errors, devices
import google.generativeai as genai
from zhipuai import ZhipuAI
import webcolors
try:
    import colornamer
except ImportError:
    colornamer = None
from palettable.cartocolors.diverging import ArmyRose_7, Earth_7, Fall_7, Geyser_7, TealRose_7, Temps_7, Tropic_7
from palettable.cartocolors.qualitative import Antique_10, Bold_10, Pastel_10, Prism_10, Safe_10, Vivid_10
from palettable.cartocolors.sequential import BluGrn_7, BluYl_7, BrwnYl_7, Burg_7, BurgYl_7, DarkMint_7, Emrld_7, Magenta_7, Mint_7, OrYel_7, Peach_7, PinkYl_7, Purp_7, PurpOr_7, RedOr_7, Sunset_7, SunsetDark_7, Teal_7, TealGrn_7, agGrnYl_7, agSunset_7
from palettable.cmocean.diverging import Balance_20, Curl_20, Delta_20
from palettable.cmocean.sequential import Algae_20, Amp_20, Deep_20, Dense_20, Gray_20, Haline_20, Ice_20, Matter_20, Oxy_20, Phase_20, Solar_20, Speed_20, Tempo_20, Thermal_20, Turbid_20
from palettable.colorbrewer.diverging import BrBG_11, PiYG_11, PRGn_11, PuOr_11, RdBu_11, RdGy_11, RdYlBu_11, RdYlGn_11, Spectral_11
from palettable.colorbrewer.qualitative import Set3_12, Pastel1_9, Accent_8, Paired_12, Set1_9, Set2_8, Dark2_8, Pastel2_8
from palettable.colorbrewer.sequential import Blues_9, BuGn_9, BuPu_9, GnBu_9, Greens_9, Greys_9, Oranges_9, OrRd_9, PuBu_9, PuBuGn_9, PuRd_9, Purples_9, RdPu_9, Reds_9, YlGn_9, YlGnBu_9, YlOrBr_9, YlOrRd_9

try:
    from qwen_vl_utils import process_vision_info
except ImportError:
    print("Stylez Error: qwen-vl-utils not installed. Please run 'pip install qwen-vl-utils'")
    process_vision_info = None

import sys
import threading
from modules import paths
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import uuid

ext_dir = Path(basedir())
extension_path = scripts.basedir()
refresh_symbol = '\U0001f504'  # 🔄
close_symbol = '\U0000274C'  # ❌
save_symbol = '\U0001F4BE' #💾
delete_style = '\U0001F5D1' #🗑️
clear_symbol = '\U0001F9F9' #🧹

card_size_value = 0
card_size_min = 0
card_size_max = 0
favourites = []
config_json = os.path.join(extension_path,"scripts" ,"config.json")
mappings_csv = os.path.join(extension_path,"scripts" ,"mappings.csv")
css_file_path = os.path.join(extension_path,"style.css")
color_file_path = os.path.join(extension_path,"colors.txt")
prompt_translation_model_dir = Path(paths_internal.models_path) / "prompt_translation"  # 本地目录

# ---------------------------------------------------------------------------
# Qwen VL Model Management
# ---------------------------------------------------------------------------
_qwen_model_cache = {"model": None, "processor": None}
QWEN_MODEL_DIR = os.path.join(paths_internal.models_path, "Qwen")

# 全局下载任务管理
download_tasks = {}

def load_qwen_model(model_name="huihui-ai/Huihui-Qwen3-VL-2B-Instruct-abliterated"):
    global _qwen_model_cache

    if _qwen_model_cache["model"] is not None:
        return _qwen_model_cache["model"], _qwen_model_cache["processor"]

    repo_id = model_name
    local_dir = os.path.join(QWEN_MODEL_DIR, repo_id.split("/")[-1])
    
    if not os.path.exists(local_dir):
        print(f"Stylez: Downloading {repo_id} to {local_dir}...")
        snapshot_download(repo_id=repo_id, local_dir=local_dir, local_dir_use_symlinks=False)

    print(f"Stylez: Loading Qwen3 VL model from {local_dir}...")
    
    try:
        processor = AutoProcessor.from_pretrained(
            local_dir, 
            min_pixels=256*28*28, 
            max_pixels=1280*28*28, 
            trust_remote_code=True
        )
        
        dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
        
        model = Qwen3VLForConditionalGeneration.from_pretrained(
            local_dir,
            torch_dtype=dtype,
            device_map="cuda", 
            trust_remote_code=True
        )
    except Exception as e:
        print(f"Stylez Error loading Qwen3 model: {e}")
        return None, None

    _qwen_model_cache["model"] = model
    _qwen_model_cache["processor"] = processor
    
    return model, processor

def run_qwen_inference(text, image=None, max_new_tokens=1024, temperature=0.7, top_p=0.8, top_k=20, seed=-1):
    if process_vision_info is None:
        return "Error: qwen-vl-utils library is missing."

    model, processor = load_qwen_model()
    if model is None:
        return "Error: Failed to load Qwen3 model."

    messages = []
    user_content = []
    
    if image is not None:
        user_content.append({"type": "image", "image": image})
        system_prompt = "You are a helpful assistant describing images."
    else:
        system_prompt = "You are a helpful assistant."

    if text:
        user_content.append({"type": "text", "text": text})

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content}
    ]

    text_input = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    image_inputs, video_inputs = process_vision_info(messages)
    
    inputs = processor(
        text=[text_input],
        images=image_inputs,
        videos=video_inputs,
        padding=True,
        return_tensors="pt",
    )
    inputs = inputs.to(model.device)

    if seed == -1 or seed is None:
        seed = torch.randint(0, 2**32, (1,)).item()
    torch.manual_seed(seed)

    gen_kwargs = {
        "max_new_tokens": max_new_tokens,
        "do_sample": temperature > 0,
    }
    if temperature > 0:
        gen_kwargs.update({"temperature": temperature, "top_p": top_p, "top_k": top_k})

    with torch.no_grad():
        generated_ids = model.generate(**inputs, **gen_kwargs)
    
    generated_ids_trimmed = [
        out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
    ]
    output_text = processor.batch_decode(
        generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
    )
    
    return output_text[0]

def unload_qwen_model():
    global _qwen_model_cache
    
    print("Stylez: Unloading Qwen3 VL model...")
    
    if _qwen_model_cache["model"] is not None:
        _qwen_model_cache["model"].to("cpu")
        del _qwen_model_cache["model"]
        _qwen_model_cache["model"] = None
    
    if _qwen_model_cache["processor"] is not None:
        del _qwen_model_cache["processor"]
        _qwen_model_cache["processor"] = None
    
    gc.collect()
    torch.cuda.empty_cache()
    print("Stylez: Qwen3 VL model unloaded and VRAM cleared.")

# ---------------------------------------------------------------------------
# Image Captioning Logic
# ---------------------------------------------------------------------------

BASE_INSTRUCTION = "You are a creative prompt engineer and visual analyst. Your mission is to analyze the provided image and generate exactly 1 distinct instruction or description based on the user's request."
SUFFIX_INSTRUCTION = "\n\n**Output Format:** Your response must be a SINGLE, concise paragraph or list as requested. Do NOT add conversational filler, numbering, or explanations."

VISUAL_SYSTEM_PROMPTS = {
    "Image Description - Tags": f"""
{BASE_INSTRUCTION}
**Task:** Extract key visual elements, subjects, styles, lighting, and composition from the image.
**Output:** A concise, comma-separated sequence of high-quality Danbooru-style tags.
**Order:** Subject > Action/Pose > Apparel > Environment > Lighting > Style.
{SUFFIX_INSTRUCTION}
""",
    "Image Description - Natural Language": f"""
{BASE_INSTRUCTION}
**Task:** Provide a direct, continuous, and highly descriptive natural language prompt for the image.
**Focus:** Capture all key visual details, subject appearance, atmosphere, camera angle, and artistic style.
**Style:** Write like a professional photographer or art director describing a scene for generation.
{SUFFIX_INSTRUCTION}
""",
    "Image Description - Photorealistic": f"""
{BASE_INSTRUCTION}
**Task:** Describe the content of the image strictly as a high-quality, photorealistic photograph.
**Constraint:** IGNORE the original art style (e.g., anime, illustration, painting). Translate all stylized elements into their real-world equivalents. For example, describe 'anime eyes' as 'realistic human eyes', and 'cel shading' as 'natural lighting with soft shadows'.
**Focus:** Emphasize realistic textures (skin pores, fabric weaves), cinematic lighting, camera lens details (depth of field, focal length, bokeh), and believable anatomical proportions.
**Style:** Write like a professional photographer specifying a shot for a realistic movie or photoshoot. Do NOT use terms like 'anime', 'illustration', '2D', or 'drawing'.
{SUFFIX_INSTRUCTION}
""",
    "Image Description - Art Analysis": f"""
{BASE_INSTRUCTION}
**Task:** Analyze the image as an art critic and provide a professional, detailed description of the artwork.
**Focus:**
1. **Medium & Technique:** Identify the medium (e.g., oil on canvas, watercolor, digital painting, charcoal, marble sculpture) and specific techniques (e.g., thick impasto brushstrokes, wet-on-wet, cel shading, dithering).
2. **Style & Movement:** Pinpoint the art style or movement (e.g., Impressionism, Art Nouveau, Cyberpunk, Ukiyo-e, Surrealism).
3. **Visual Elements:** Describe the color palette (e.g., monochromatic, pastel, vibrant complementary colors), lighting (e.g., chiaroscuro, flat lighting), and composition.
4. **Subject & Mood:** Describe the subject matter and the emotional atmosphere (e.g., melancholic, chaotic, serene).
**Constraint:** Use professional art terminology. Output ONLY the description.
{SUFFIX_INSTRUCTION}
""",
    "Image Description - NSFW": f"""
{BASE_INSTRUCTION}
**Task:** Analyze the image and provide a highly detailed, explicit, and uncensored description of the NSFW content.
**Constraint:** Do NOT use euphemisms. Be anatomically precise and direct.
**Focus:** Describe body parts (genitalia, breasts, etc.), sexual acts/positions, fluids, facial expressions (ahegao, blush), and skin textures (sweat, oil).
**Structure:** Start with the main subjects and their interaction, followed by specific anatomical details, clothing state (or lack thereof), and background context.
{SUFFIX_INSTRUCTION}
""",
    "Image Edit - Teleport": f"{BASE_INSTRUCTION}\n**Task:** Teleport the subject to a completely random and unexpected location/scenario. Keep the subject unchanged, but completely transform the background and context.\n{SUFFIX_INSTRUCTION}",
    "Image Edit - Move Camera": f"{BASE_INSTRUCTION}\n**Task:** Describe a new camera angle for the scene (e.g., top-down, wide-angle, close-up) to reveal new aspects, while keeping the scene content consistent.\n{SUFFIX_INSTRUCTION}",
    "Image Edit - Relight": f"{BASE_INSTRUCTION}\n**Task:** Propose a new, dramatic lighting setup (e.g., cyberpunk neon, golden hour, studio softbox). Change the atmosphere through light and shadow.\n{SUFFIX_INSTRUCTION}",
    "Image Edit - Composition Rebuild": f"{BASE_INSTRUCTION}\n**Task:** Recompose the image layout. Suggest a new framing or object placement to improve visual flow and aesthetics.\n{SUFFIX_INSTRUCTION}",
    "Image Edit - Product Photo": f"{BASE_INSTRUCTION}\n**Task:** Transform this into a high-end commercial product photograph. Focus on studio lighting, clean background, and product details.\n{SUFFIX_INSTRUCTION}",
    "Image Edit - Product Appearance Redesign": f"{BASE_INSTRUCTION}\n**Task:** Redesign the product's outer appearance (packaging, material, color) to look more modern, luxurious, or eco-friendly.\n{SUFFIX_INSTRUCTION}",
    "Image Edit - Zoom": f"{BASE_INSTRUCTION}\n**Task:** Apply a zoom effect (in or out) to focus on a specific detail or reveal more context.\n{SUFFIX_INSTRUCTION}",
    "Image Edit - Colorize": f"{BASE_INSTRUCTION}\n**Task:** Apply a specific color grading or colorize the image if it's black and white. Suggest a cohesive color palette.\n{SUFFIX_INSTRUCTION}",
    "Image Edit - Logo": f"{BASE_INSTRUCTION}\n**Task:** Transform the main subject into a stylized, vector-like Logo design. Simplify shapes and focus on symbolic representation.\n{SUFFIX_INSTRUCTION}",
    "Image Edit - Tail Frame Generation": f"{BASE_INSTRUCTION}\n**Task:** Analyze the motion and context to generate the 'next frame' or ending frame for a video sequence based on this image.\n{SUFFIX_INSTRUCTION}",
    "Image Edit - Movie Poster": f"{BASE_INSTRUCTION}\n**Task:** Turn this image into a cinematic movie poster. Add a sense of drama, genre-specific styling (Horror, Sci-Fi, Romance), and composition.\n{SUFFIX_INSTRUCTION}",
    "Image Edit - Cartoonize": f"{BASE_INSTRUCTION}\n**Task:** Transform the image style into a cartoon, anime, or comic book style (e.g., 90s anime, Pixar 3D, line art).\n{SUFFIX_INSTRUCTION}",
    "Image Edit - Remove Text": f"{BASE_INSTRUCTION}\n**Task:** Instruction: Remove all visible text, watermarks, or subtitles from the image, filling the gaps naturally.\n{SUFFIX_INSTRUCTION}",
    "Image Edit - Hairdresser": f"{BASE_INSTRUCTION}\n**Task:** Change the subject's hairstyle. Suggest a new cut, color, or style that suits the face.\n{SUFFIX_INSTRUCTION}",
    "Image Edit - Wardrobe Makeover": f"{BASE_INSTRUCTION}\n**Task:** Change the subject's clothing to a different style (e.g., Cyberpunk, Hanfu, Formal suit), keeping the pose unchanged.\n{SUFFIX_INSTRUCTION}",
    "Image Edit - Gravure Pose": f"{BASE_INSTRUCTION}\n**Task:** Adjust the subject's pose to be more photogenic, elegant, or model-like (Gravure style), focusing on body language.\n{SUFFIX_INSTRUCTION}",
    "Image Edit - Bodybuilder": f"{BASE_INSTRUCTION}\n**Task:** Exaggerate the subject's musculature, turning them into a bodybuilder physique.\n{SUFFIX_INSTRUCTION}",
    "Image Edit - Remove Furniture": f"{BASE_INSTRUCTION}\n**Task:** Remove all furniture and indoor clutter, leaving the room architecture empty and clean.\n{SUFFIX_INSTRUCTION}",
    "Image Edit - Interior Design": f"{BASE_INSTRUCTION}\n**Task:** Redesign the interior style (e.g., from modern to rustic, or industrial to minimalist).\n{SUFFIX_INSTRUCTION}",
    "Image Edit - Architectural Facelift": f"{BASE_INSTRUCTION}\n**Task:** Redesign the building's exterior facade. Change materials, windows, or architectural style.\n{SUFFIX_INSTRUCTION}",
    "Image Edit - Clean Up": f"{BASE_INSTRUCTION}\n**Task:** Remove clutter, debris, and distraction objects from the scene to make it look tidy.\n{SUFFIX_INSTRUCTION}",
    "Image Edit - Art Style": f"{BASE_INSTRUCTION}\n**Task:** Repaint the image in the style of a famous art movement (e.g., Impressionism, Van Gogh, Ukiyo-e).\n{SUFFIX_INSTRUCTION}",
    "Image Edit - Material Shift": f"{BASE_INSTRUCTION}\n**Task:** Change the material of objects (e.g., wood to glass, flesh to metal, fabric to liquid).\n{SUFFIX_INSTRUCTION}",
    "Image Edit - Emotion Shift": f"{BASE_INSTRUCTION}\n**Task:** Change the subject's facial expression and emotional vibe (e.g., from neutral to happy, or angry to surprised).\n{SUFFIX_INSTRUCTION}",
    "Image Edit - Age Shift": f"{BASE_INSTRUCTION}\n**Task:** Change the subject's age (make them younger or older) while keeping identity features.\n{SUFFIX_INSTRUCTION}",
    "Image Edit - Seasonal Shift": f"{BASE_INSTRUCTION}\n**Task:** Change the season of the scene (e.g., Summer to Winter, Spring to Autumn).\n{SUFFIX_INSTRUCTION}",
    "Image Edit - Composite Fusion": f"{BASE_INSTRUCTION}\n**Task:** Fix lighting and shadow inconsistencies to make the foreground subject blend perfectly with the background.\n{SUFFIX_INSTRUCTION}",
}

img2prompt_models = [
    "Local-Qwen",
    "GeminiAPI",
    "ZhipuAPI",
]

img2prompt_types = list(VISUAL_SYSTEM_PROMPTS.keys())

def generate_caption_fn(
    image: Image,
    model_name: str,
    max_new_token: float,
    prompt_type: str,
    unload_after_gen: bool = False,
    seed: int = -1,
):
    if seed == -1:
        seed = random.randint(0, 2**32 - 1)

    result = ""
    
    instruction_text = VISUAL_SYSTEM_PROMPTS.get(prompt_type, "Describe this image in detail.")
    
    if model_name == "Local-Qwen":
        result = run_qwen_inference(
            text=instruction_text,
            image=image,
            max_new_tokens=int(max_new_token),
            seed=seed
        )
        result = re.sub(r'^\s*\d+[\.\)]?\s*', '', result, flags=re.MULTILINE).strip()

        if unload_after_gen:
            unload_qwen_model()

    elif model_name == "GeminiAPI":
        configure_gemini()
        model = genai.GenerativeModel("gemini-2.5-flash")
        
        temp_image_path = "temp_image.jpg"
        image.save(temp_image_path)
        sample_file = genai.upload_file(path=temp_image_path, display_name="uploaded image")
        
        response = model.generate_content([sample_file, instruction_text])
        result = response.text.strip()
        
        result = re.sub(r'^\s*\d+[\.\)]?\s*', '', result, flags=re.MULTILINE).strip()
        os.remove(temp_image_path)

    elif model_name == "ZhipuAPI":
        client = ZhipuAI(api_key=ZHIPUAI_API_KEY)
        temp_image_path = "temp_image.jpg"
        image.save(temp_image_path)
        with open(temp_image_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')

        response = client.chat.completions.create(
            model="GLM-4.6V-Flash",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": instruction_text},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }
            ],
        )
        result = response.choices[0].message.content.strip()
        result = re.sub(r'^\s*\d+[\.\)]?\s*', '', result, flags=re.MULTILINE).strip()
        os.remove(temp_image_path)

    return result, f"<p>{result}</p>", f"<p>Live Seed: {seed}</p>"

# ---------------------------------------------------------------------------
# Main Stylez Logic
# ---------------------------------------------------------------------------

df = pd.read_csv(mappings_csv)

mediums_mapping = dict(zip(df[df['type'] == 'mediums']['key'], df[df['type'] == 'mediums']['value']))
style_mapping = dict(zip(df[df['type'] == 'style']['key'], df[df['type'] == 'style']['value']))

tagschoices=[
"NONE",
"NO HUMANS",
"MAN",
"WOMAN",
"OLD",
"CHIBI",
"CLOTHING",
"CHINESE CLOTHES",
"ARMOR",
"WINGS",
"MONSTER",
"GIANT",
"ROBOT",
"ANIMAL",
"CAT",
"DOG",
"DRAGON",
"STILL LIFE",
"FOOD",
"WEAPON",
"VEHICLE FOCUS",
"TRAIN",
"SHIP",
"OUTDOORS",
"CITY",
"BUILDING",
"HOUSE",
"EAST ASIAN ARCHITECTURE",
"CASTLE",
"NEON LIGHTS",
"SCENERY",
"WATER",
"FIRE",
"RAIN",
"SNOW",
"LIGHTNING",
"FOG",
"HORROR (THEME)",
"ENGLISH TEXT",
"PHOTOGRAPHY",
"REALISTIC",
"ANIME",
"FANTASY",
"SCIENCE FICTION",
"SILHOUETTE",
"GREYSCALE"
]

theme_presets = {
    "Mint": {
        "colors": ["#00FFC9", "#3d3e4f"],
        "css_class": "minty-teal-button"
    },
    "Lime": {
        "colors": ["#b7ff00", "#3e3f3b"],
        "css_class": "lime-green-button"
    },
    "Blue": {
        "colors": ["#00b7ff", "#2f394e"],
        "css_class": "electric-blue-button"
    },
    "Orange": {
        "colors": ["#ff9900", "#252525"],
        "css_class": "amber-orange-button"
    },
    "Pink": {
        "colors": ["#F798B3", "#666771"],
        "css_class": "cotton-candy-button"
    },
    "Lilac": {
        "colors": ["#BB86FC", "#1F1F1F"],
        "css_class": "neon-lilac-button"
    },
    "Red": {
        "colors": ["#ff4040", "#272727"],
        "css_class": "coral-red-button"
    },
    "Gray": {
        "colors": ["#d3d3d3", "#282828"],
        "css_class": "light-gray-button"
    },
    "Gold": {
        "colors": ["#F7E7CE", "#3B3633"],
        "css_class": "champagne-gold-button"
    },
    "Lavender": {
        "colors": ["#87A9FF", "#29344A"],
        "css_class": "lavender-blue-button"
    },
}

def save_card_def(value):
    global card_size_value
    save_settings("card_size",value)
    card_size_value = value
    
def get_extension_config():
    if not os.path.exists(config_json):
        return {}
    try:
        with open(config_json, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def save_extension_config_func(key, value):
    if not key: return "Error: Key name is empty", gr.update()
    try:
        data = get_extension_config()
        data[key] = value
        with open(config_json, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        global GEMINI_API_KEY, ZHIPUAI_API_KEY, PROXY
        if key == "GEMINI_API_KEY": GEMINI_API_KEY = value
        if key == "ZHIPUAI_API_KEY": ZHIPUAI_API_KEY = value
        if key == "PROXY": PROXY = value
        
        return f"CONFIG_SAVED_{random.randint(0, 100000)}", "<p style='color:green;'>API Key saved successfully. Please try generating again.</p>"
    except Exception as e:
        return f"Error saving config: {e}", gr.update()

def get_model_target_dir(m_type):
    opts = shared.cmd_opts
    
    try:
        from modules import paths
        base_models_path = paths.models_path
    except:
        base_models_path = "models"

    if m_type == "Checkpoint":
        p = getattr(opts, 'ckpt_dir', None)
        if p: return p
        return os.path.join(base_models_path, "Stable-diffusion")
        
    elif m_type == "Hypernetwork":
        p = getattr(opts, 'hypernetwork_dir', None)
        if p: return p
        return os.path.join(base_models_path, "hypernetworks")
        
    elif m_type == "LORA" or m_type == "LoCon" or m_type == "DoRA":
        p = getattr(opts, 'lora_dir', None)
        if p: return p
        return os.path.join(base_models_path, "Lora")
        
    elif m_type == "VAE":
        p = getattr(opts, 'vae_dir', None)
        if p: return p
        return os.path.join(base_models_path, "VAE")
        
    elif m_type == "Controlnet":
        p = getattr(opts, 'controlnet_dir', None)
        if p: return p
        return os.path.join(base_models_path, "ControlNet")
        
    elif m_type == "Upscaler":
        p = getattr(opts, 'esrgan_models_dir', None)
        if p: return p
        return os.path.join(base_models_path, "ESRGAN")
        
    return os.path.join(base_models_path, "Stable-diffusion")

def check_model_exists(m_type, filename):
    safe_name = replace_illegal_filename_characters(filename)
    possible_filenames = [safe_name]
    if "." not in safe_name:
        possible_filenames.append(safe_name + ".safetensors")
        possible_filenames.append(safe_name + ".ckpt")
        possible_filenames.append(safe_name + ".pt")

    search_roots = []

    default_dir = get_model_target_dir(m_type)
    if default_dir and os.path.exists(default_dir):
        search_roots.append(default_dir)

    opts = shared.cmd_opts
    
    if m_type == "Checkpoint":
        if hasattr(opts, 'ckpt_dirs') and opts.ckpt_dirs:
            search_roots.extend(opts.ckpt_dirs)
        if hasattr(opts, 'ckpt_dir') and opts.ckpt_dir:
            search_roots.append(opts.ckpt_dir)
            
    elif m_type in ["LORA", "LoCon", "DoRA"]:
        if hasattr(opts, 'lora_dirs') and opts.lora_dirs:
            search_roots.extend(opts.lora_dirs)
        if hasattr(opts, 'lora_dir') and opts.lora_dir:
            search_roots.append(opts.lora_dir)

    elif m_type == "VAE":
        if hasattr(opts, 'vae_dirs') and opts.vae_dirs:
            search_roots.extend(opts.vae_dirs)
        if hasattr(opts, 'vae_dir') and opts.vae_dir:
            search_roots.append(opts.vae_dir)

    if hasattr(opts, 'forge_ref_comfy_home') and opts.forge_ref_comfy_home:
        comfy_root = opts.forge_ref_comfy_home
        if m_type == "Checkpoint":
            search_roots.append(os.path.join(comfy_root, "models", "checkpoints"))
            search_roots.append(os.path.join(comfy_root, "models", "unet"))
            search_roots.append(os.path.join(comfy_root, "models", "diffusion_models"))
        elif m_type in ["LORA", "LoCon", "DoRA"]:
            search_roots.append(os.path.join(comfy_root, "models", "loras"))
        elif m_type == "VAE":
            search_roots.append(os.path.join(comfy_root, "models", "vae"))
        elif m_type == "Upscaler":
            search_roots.append(os.path.join(comfy_root, "models", "upscale_models"))
        elif m_type == "Controlnet":
             search_roots.append(os.path.join(comfy_root, "models", "controlnet"))

    unique_roots = list(set([os.path.abspath(p) for p in search_roots if p and os.path.exists(p)]))

    for root_dir in unique_roots:
        for current_root, dirs, files in os.walk(root_dir):
            for name in possible_filenames:
                if name in files:
                    return True
                    
    return False

def get_civitai_models_func(json_data):
    try:
        data = json.loads(json_data)
    except:
        return json.dumps({"items": [], "metadata": {}, "error": "Invalid JSON"})

    config = get_extension_config()
    proxy_url = config.get("PROXY", "")
    proxies = {"http": proxy_url, "https": proxy_url} if proxy_url else {}
    
    api_key = config.get("CIVITAI_API_KEY", "")
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    base_domain = "civitai.com"
    api_url = f"https://{base_domain}/api/v1/models"
    
    params = {
        "limit": 20,
        "sort": data.get("sort", "Most Downloaded"),
        "period": data.get("period", "AllTime"),
        "nsfw": "true" if data.get("nsfw") else "false"
    }
    
    if data.get("type") and data.get("type") != "All":
        params["types"] = data.get("type")
    if data.get("query"):
        params["query"] = data.get("query")
    if data.get("baseModel") and data.get("baseModel") != "All":
        params["baseModels"] = data.get("baseModel")
    if data.get("cursor"):
        params["cursor"] = data.get("cursor")

    try:
        response = requests.get(api_url, params=params, headers=headers, proxies=proxies, verify=False, timeout=30)
        if response.status_code != 200:
            return json.dumps({"items": [], "metadata": {}, "error": f"API Error: {response.status_code}"})
        
        result = response.json()
        
        if "items" in result:
            for item in result["items"]:
                try:
                    latest_ver = item.get("modelVersions", [{}])[0]
                    files = latest_ver.get("files", [])
                    if files:
                        filename = files[0].get("name")
                    else:
                        filename = f"{item['name']}_{latest_ver['name']}"

                    item["isDownloaded"] = check_model_exists(item.get("type"), filename)
                except Exception as e:
                    item["isDownloaded"] = False
        
        return json.dumps(result)

    except Exception as e:
        return json.dumps({"items": [], "metadata": {}, "error": str(e)})

def download_civitai_model_func(json_data):
    try:
        data = json.loads(json_data)
        url = data.get("url")
        filename = data.get("filename")
        m_type = data.get("type")
        image_url = data.get("image_url")
        
        config = get_extension_config()
        api_key = config.get("CIVITAI_API_KEY", "")
        
        if not api_key:
            return "MISSING_KEY_CIVITAI"

        proxy_url = config.get("PROXY", "")
        proxies = {"http": proxy_url, "https": proxy_url} if proxy_url else {}
        headers = {"Authorization": f"Bearer {api_key}", "User-Agent": "Mozilla/5.0"}

        dest_dir = get_model_target_dir(m_type)
        if not os.path.exists(dest_dir): os.makedirs(dest_dir, exist_ok=True)
        
        safe_name = replace_illegal_filename_characters(filename)
        if "." not in safe_name: safe_name += ".safetensors"
        final_path = os.path.join(dest_dir, safe_name)
        
        if os.path.exists(final_path):
             return f"File already exists: {safe_name}"

        task_id = str(uuid.uuid4())
        download_tasks[task_id] = {
            "status": "running",
            "progress": 0,
            "total": 0,
            "filename": safe_name,
            "abort": False
        }

        def _dl():
            try:
                with requests.get(url, stream=True, headers=headers, proxies=proxies, verify=False, allow_redirects=True, timeout=60) as r:
                    if r.status_code == 401: 
                        download_tasks[task_id]["status"] = "error"
                        download_tasks[task_id]["msg"] = "401 Unauthorized"
                        return
                    r.raise_for_status()
                    
                    total_size = int(r.headers.get('content-length', 0))
                    download_tasks[task_id]["total"] = total_size
                    
                    with open(final_path, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            if download_tasks[task_id]["abort"]:
                                f.close()
                                os.remove(final_path)
                                download_tasks[task_id]["status"] = "aborted"
                                return
                            if chunk:
                                f.write(chunk)
                                download_tasks[task_id]["progress"] += len(chunk)
                if image_url:
                    try:
                        base_name, _ = os.path.splitext(final_path)
                        
                        print(f"[Stylez] Downloading preview content: {image_url}")
                        
                        with requests.get(image_url, stream=True, headers=headers, proxies=proxies, verify=False, timeout=30) as r_img:
                            if r_img.status_code == 200:
                                import mimetypes
                                root, ext = os.path.splitext(image_url)
                                if '?' in ext:
                                    ext = ext.split('?')[0]
                                
                                if not ext or len(ext) > 5: 
                                    content_type = r_img.headers.get('content-type')
                                    ext = mimetypes.guess_extension(content_type)
                                
                                if not ext:
                                    ext = ".jpg"
                                
                                if ext == '.jpe': ext = '.jpg'

                                image_path = base_name + ext

                                with open(image_path, 'wb') as f_img:
                                    r_img.raw.decode_content = True
                                    shutil.copyfileobj(r_img.raw, f_img)
                                print(f"[Stylez] Preview saved to: {image_path}")
                            else:
                                print(f"[Stylez] Failed to download preview, status code: {r_img.status_code}")
                                
                    except Exception as img_e:
                        print(f"[Stylez] Failed to download preview image: {img_e}")

                download_tasks[task_id]["status"] = "completed"
                print(f"[Stylez] Downloaded: {final_path}")
            except Exception as e:
                download_tasks[task_id]["status"] = "error"
                download_tasks[task_id]["msg"] = str(e)
                print(f"[Stylez] Download Failed: {e}")

        threading.Thread(target=_dl).start()
        return json.dumps({"status": "started", "task_id": task_id, "filename": safe_name})
    except Exception as e:
        return f"Error: {e}"

def check_download_progress_func():
    return json.dumps(download_tasks)

def abort_download_func(task_id):
    if task_id in download_tasks:
        download_tasks[task_id]["abort"] = True
        return "Aborting..."
    return "Task not found"

if not os.path.exists(config_json):
    default_config = {
        "GEMINI_API_KEY": "",
        "ZHIPUAI_API_KEY": "",
        "PROXY": "",
        "card_size": 146,
        "card_size_min": 50,
        "card_size_max": 200,
        "autoconvert": True,
        "favourites": []
    }
    
    with open(config_json, 'w') as config_file:
        json.dump(default_config, config_file, indent=4)

with open(config_json, "r") as json_file:
    data = json.load(json_file)
    GEMINI_API_KEY = data.get("GEMINI_API_KEY", "")
    ZHIPUAI_API_KEY = data.get("ZHIPUAI_API_KEY", "")
    PROXY = data.get("PROXY", "")
    card_size_value = data.get("card_size", 146)
    card_size_min = data.get("card_size_min", 50)
    card_size_max = data.get("card_size_max", 200)
    autoconvert = data.get("autoconvert", True)
    favourites = data.get("favourites", [])

def configure_gemini():
    data = get_extension_config()
    api_key = data.get("GEMINI_API_KEY", "")
    proxy_url = data.get("PROXY", "")

    client_options = {}
    if proxy_url:
        client_options['api_endpoint'] = proxy_url
    
    if api_key:
        genai.configure(api_key=api_key, transport='rest', client_options=client_options)

def reload_favourites():
    with open(config_json, "r") as json_file:
        data = json.load(json_file)
        global favourites
        favourites = data["favourites"]

def save_settings(setting,value):
    with open(config_json, "r") as json_file:
        data = json.load(json_file)
    data[setting] = value
    with open(config_json, "w") as json_file:
        json.dump(data, json_file, indent=4)

def img_to_thumbnail(img):
    return gr.update(value=img)

character_translation_table = str.maketrans('"*/:<>?\\|\t\n\v\f\r', '＂＊／：＜＞？＼￨     ')
leading_space_or_dot_pattern = re.compile(r'^[\s.]')


def replace_illegal_filename_characters(input_filename: str):
    r"""
    Replace illegal characters with full-width variant
    if leading space or dot then add underscore prefix
    if input is blank then return underscore
    """
    if input_filename:
        output_filename = input_filename.translate(character_translation_table)
        return '_' + output_filename if re.match(leading_space_or_dot_pattern, output_filename) else output_filename
    return '_' 


def create_json_objects_from_csv(csv_file):
    json_objects = []
    with open(csv_file, 'r', newline='', encoding='utf-8-sig') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            name = row.get('name', None)
            prompt = row.get('prompt', None)
            negative_prompt = row.get('negative_prompt', None)
            if name is None or prompt is None or negative_prompt is None:
                print("Warning: Skipping row with missing values.")
                continue
            safe_name = replace_illegal_filename_characters(name)
            json_data = {
                "name": safe_name,
                "description": "converted from csv",
                "preview": f"{safe_name}.jpg",
                "prompt": prompt,
                "negative": negative_prompt,
            }
            json_objects.append(json_data)
    return json_objects

def save_json_objects(json_objects):
    if not json_objects:
        print("Warning: No JSON objects to save.")
        return

    styles_dir = os.path.join(extension_path, "styles")
    csv_conversion_dir = os.path.join(styles_dir, "CSVConversion")
    os.makedirs(csv_conversion_dir, exist_ok=True)

    nopreview_image_path = os.path.join(extension_path, "nopreview.jpg")
    for json_obj in json_objects:
        try:
            json_file_path = os.path.join(csv_conversion_dir, f"{json_obj['name']}.json")
            with open(json_file_path, 'w') as jsonfile:
                json.dump(json_obj, jsonfile, indent=4)
            image_path = os.path.join(csv_conversion_dir, f"{json_obj['name']}.jpg")
            shutil.copy(nopreview_image_path, image_path)
        except Exception as e:
            print(f'{e}\nStylez Failed to convert {json_obj.get("name", str(json_obj))}')

        
if autoconvert:
    styles_files = shared.cmd_opts.styles_file if isinstance(shared.cmd_opts.styles_file, list) else [shared.cmd_opts.styles_file]
    for styles_file_path in styles_files:
        if os.path.exists(styles_file_path):
            json_objects = create_json_objects_from_csv(styles_file_path)
            save_json_objects(json_objects)
        else:
            print(f"File does not exist: {styles_file_path}")

    save_settings("autoconvert", False)


def generate_html_code():
    reload_favourites()
    style = None
    style_html = ""
    categories_list = ["All","Favourites"]
    save_categories_list =[]
    styles_dir = os.path.join(extension_path, "styles")
    current_time = datetime.datetime.now()
    formatted_time = current_time.strftime('%H:%M:%S.%f')
    formatted_time = formatted_time.replace(":", "")
    formatted_time = formatted_time.replace(".", "")
    try:
        for root, dirs, _ in os.walk(styles_dir):
            for directory in dirs:
                subfolder_name = os.path.basename(os.path.join(root, directory))
                if subfolder_name.lower() not in categories_list:
                    categories_list.append(subfolder_name)
                if subfolder_name.lower() not in save_categories_list:
                    save_categories_list.append(subfolder_name)    
        for root, _, files in os.walk(styles_dir):
            for filename in files:
                if filename.endswith(".json"):
                    json_file_path = os.path.join(root, filename)
                    subfolder_name = os.path.basename(root)
                    with open(json_file_path, "r", encoding="utf-8") as f:
                        try:
                            style = json.load(f)
                            title = style.get("name", "")
                            preview_image = style.get("preview", "")
                            description = style.get("description", "")
                            img = os.path.join(os.path.dirname(json_file_path), preview_image)
                            img = os.path.abspath(img)
                            prompt = style.get("prompt", "")
                            prompt = html.escape(json.dumps(prompt))
                            prompt_negative = style.get("negative", "")
                            prompt_negative = html.escape(json.dumps(prompt_negative))
                            steps = style.get("steps", "")
                            cfg_scale = style.get("cfg_scale", "")
                            seed = style.get("seed", "")
                            size = style.get("size", "")
                            sampling = style.get("sampling", "") 
                            scheduler = style.get("scheduler", "") 
                            imghack = img.replace("\\", "/")
                            json_file_path = json_file_path.replace("\\", "/")
                            encoded_filename = urllib.parse.quote(filename, safe="")
                            titlelower = str(title).lower()
                            color = ""
                            stylefavname =subfolder_name + "/" + filename
                            if (stylefavname in favourites):
                                color = "#EBD617"
                            else:
                                color = "#ffffff"
                            style_html += f"""
                            <div class="style_card" data-category='{subfolder_name}' data-title='{titlelower}' style="min-height:{card_size_value}px;max-height:{card_size_value}px;min-width:{card_size_value}px;max-width:{card_size_value}px;">
                                <div class="style_card_checkbox" onclick="toggleCardSelection(event, '{subfolder_name}','{encoded_filename}')">◉</div>  <img class="styles_thumbnail" src="{"file=" + img}" alt="{title} Preview" loading="lazy">
                                <div class="EditStyleJson">
                                    <button onclick="editStyle(`{title}`,`{imghack}`,`{description}`,`{prompt}`,`{prompt_negative}`,`{steps}`,`{cfg_scale}`,`{seed}`,`{size}`,`{sampling}`,`{scheduler}`,`{subfolder_name}`,`{encoded_filename}`,`Stylez`)">🖉</button>
                                </div>
                                <div class="favouriteStyleJson">
                                    <button class="favouriteStyleBtn" style="color:{color};" onclick="addFavourite('{subfolder_name}','{encoded_filename}', this)">★</button>
                                </div>
                                    <div onclick="applyStyle(`{prompt}`,`{prompt_negative}`,`{steps}`,`{cfg_scale}`,`{seed}`,`{size}`,`{sampling}`,`{scheduler}`,`Stylez`)" onmouseenter="event.stopPropagation(); hoverPreviewStyle(`{prompt}`,`{prompt_negative}`,`Stylez`)" onmouseleave="hoverPreviewStyleOut()" class="styles_overlay"></div>
                                    <div class="styles_title">{title}</div>
                                    <p class="styles_description"><span class="label">{description}</span></p>
                                </img>
                            </div>
                            """
                        except json.JSONDecodeError:
                            print(f"Error parsing JSON in file: {filename}")
                        except KeyError as e:
                            print(f"KeyError: {e} in file: {filename}")
    except FileNotFoundError:
        print("Directory '/models/styles' not found.")
    return style_html, categories_list, save_categories_list

def refresh_styles(cat):
    if cat is None or len(cat) == 0 or cat  == "[]" :
        cat = None
    newhtml = generate_html_code()
    newhtml_sendback = newhtml[0]
    newcat_sendback = newhtml[1]
    newfilecat_sendback = newhtml[2]
    return newhtml_sendback,gr.update(choices=newcat_sendback),gr.update(value="All"),gr.update(choices=newfilecat_sendback)

def save_style(title, img, description, prompt, prompt_negative, steps, cfg_scale, seed, size, sampling, scheduler, filename, save_folder):
    print(f"""Saved: '{save_folder}/{filename}'""")
    if save_folder and filename:
        if img is None or img == "":
            img = Image.open(os.path.join(extension_path, "nopreview.jpg")) 
        img = ImageOps.fit(img, (200, 200), Image.LANCZOS, centering=(0.5, 0.5))
        save_folder_path = os.path.join(extension_path, "styles", save_folder)
        if not os.path.exists(save_folder_path):
            os.makedirs(save_folder_path)
        json_data = {
            "name": title,
            "description": description,
            "preview": filename + ".jpg",
            "prompt": prompt,
            "negative": prompt_negative,
            "steps": steps,
            "cfg_scale": cfg_scale,
            "seed": seed,
            "size": size,
            "sampling": sampling,  
            "scheduler": scheduler 
        }
        json_file_path = os.path.join(save_folder_path, filename + ".json")
        with open(json_file_path, "w") as json_file:
            json.dump(json_data, json_file, indent=4)
        img_path = os.path.join(save_folder_path, filename + ".jpg")
        img.save(img_path)
        msg = f"""File Saved to '{save_folder}'"""
        info(msg)
    else:
        msg = """Please provide a valid save folder and Filename"""
        warning(msg)
    return filename_check(save_folder,filename)

def info(message):
    gr.Info(message)

def warning(message):
    gr.Warning(message)
    
def tempfolderbox(dropdown):
    return gr.update(value=dropdown)

def filename_check(folder,filename):
    if filename is None or len(filename) == 0 :
        warning = """<p id="style_filename_check">Enter filename!</p>"""
    else:
        save_folder_path = os.path.join(extension_path, "styles", folder)
        json_file_path = os.path.join(save_folder_path, filename + ".json")
        if os.path.exists(json_file_path):
            warning = f"""<p id="style_filename_check">File already exists in '{folder}'</p>"""
        else:
            warning = """<p id="style_filename_check">Filename valid!</p>"""
    return gr.update(value=warning)

def clear_style():
    previewimage = os.path.join(extension_path, "nopreview.jpg")
    return gr.update(value=None),gr.update(value=previewimage),gr.update(value=None),gr.update(value=None),gr.update(value=None),gr.update(value=None),gr.update(value=None)

def deletestyle(folder, filename):
    base_path = os.path.join(extension_path, "styles", folder)
    json_file_path = os.path.join(base_path, filename + ".json")
    jpg_file_path = os.path.join(base_path, filename + ".jpg")

    if os.path.exists(json_file_path):
        os.remove(json_file_path)
        warning(f"""Stlye "{filename}" deleted!! """)
        if os.path.exists(jpg_file_path):
            os.remove(jpg_file_path)
        else:
            warning(f"Error: {jpg_file_path} not found.")
    else:
        warning(f"Error: {json_file_path} not found.")

def addToFavourite(style):
 global favourites
 if (style not in favourites):
     favourites.append(style)
     save_settings("favourites",favourites)
     info("style added to favourites")

def removeFavourite(style):
 global favourites
 if (style in favourites):
     favourites.remove(style)
     save_settings("favourites",favourites)
     info("style removed from favourites")

# ---------------------------------------------------------------------------
# Text Expansion Logic
# ---------------------------------------------------------------------------

def generate_text_prompt(
    model_selection, 
    prompt_preset, 
    prompt_input_txt, 
    mediums_dropdown_value, 
    style_dropdown_value, 
    max_length_slider, 
    seed_slider, 
    unload_after_gen=False
):

    ignore_medium_style = prompt_preset in [
        "Translate EN->CN", "Translate CN->EN", "Natural Language -> Tags", "Tags -> Natural Language"
    ]

    parts = []
    if not ignore_medium_style and mediums_dropdown_value not in ["None", "Random"]:
        parts.append(mediums_mapping.get(mediums_dropdown_value, ""))
    elif not ignore_medium_style and mediums_dropdown_value == "Random":
        parts.append(random.choice(list(mediums_mapping.values())))
        
    parts.append(prompt_input_txt)
    
    if not ignore_medium_style and style_dropdown_value not in ["None", "Random"]:
        parts.append(style_mapping.get(style_dropdown_value, ""))
    elif not ignore_medium_style and style_dropdown_value == "Random":
        parts.append(random.choice(list(style_mapping.values())))

    combined_text = " ".join([p for p in parts if p]).strip()

    if seed_slider == -1:
        seed_slider = random.randint(0, 2**32 - 1)
    actual_seed_value = seed_slider

    PROMPT_PHOTO = f"""
You are an expert AI photographer and prompt engineer for Flux/Midjourney. Your task is to expand the user's input into a highly detailed, photorealistic image prompt.

**Input:** "{combined_text}"

**Instructions:**
1. **Goal:** Create a vivid, high-resolution description of a real photograph. Use sensory details.
2. **Structure:** Follow this logical order: [Main Subject & Action] > [Detailed Environment] > [Lighting & Atmosphere] > [Camera Angle & Composition] > [Technical Details].
3. **Technical Focus:** Specify camera gear (e.g., Sony A7RIV, Leica M6), film stock (e.g., Kodak Portra 400, Fujifilm Pro 400H), lens specs (e.g., 85mm f/1.2, macro lens), and lighting (e.g., cinematic lighting, volumetric rays, studio softbox).
4. **Constraint:** Do NOT use artistic terms like 'painting', 'illustration', '3d render', or 'drawing'. Do NOT output conversational text. Output ONLY the prompt string.
5. **Translation:** If input is non-English, translate to English first.
"""

    PROMPT_ART = f"""
You are a digital art curator and concept artist. Your task is to expand the user's input into a creative, artistic image prompt for Flux/Midjourney.

**Input:** "{combined_text}"

**Instructions:**
1. **Goal:** Create a rich, aesthetic description of an artwork. Focus on visual impact and emotion.
2. **Medium & Style:** Define the specific medium (e.g., oil painting, watercolor, digital collage, vector art, impasto) and artistic influences (e.g., Surrealism, Ukiyo-e, Cyberpunk).
3. **Details:** Describe brushwork textures, color palette (e.g., pastel tones, neon contrasts), and emotional atmosphere.
4. **Requirement:** Keep the main subject identifiable but rendered with strong artistic flair. Do NOT output conversational text. Output ONLY the prompt string.
5. **Translation:** If input is non-English, translate to English first.
"""

    PROMPT_TAGS = f"""
You are a Stable Diffusion prompting expert. Convert the user's input into a precise list of high-quality tags (Danbooru style).

**Input:** "{combined_text}"

**Instructions:**
1. **Format:** Output ONLY a comma-separated list: `tag1, tag2, tag3...`
2. **Mandatory Start:** Always start with high-quality meta tags: `masterpiece, best quality, very aesthetic, absrudres`.
3. **Structure:** [Subject/Character tags] > [Action/Pose tags] > [Clothing/Accessories] > [Background/Environment] > [Lighting/Camera tags] > [Art Style tags].
4. **Specifics:** Use specific booru tags (e.g., instead of "blue skirt", use "pleated skirt, blue skirt").
5. **Translation:** If input is non-English, translate to English tags directly.
"""
    
    PROMPT_VIDEO_WAN = f"""
You are an expert video prompt engineer for Wan2.1/Wan2.2 (WanVideo). Your task is to expand the user's input into a highly detailed video generation prompt.

**Input:** "{combined_text}"

**Instructions:**
1. **Goal:** Create a cinematic, dynamic video description.
2. **Structure:** Follow this order: [Main Subject & Action] > [Camera Movement & Angle] > [Environment & Atmosphere] > [Lighting & Style] > [Video Quality Tags].
3. **Motion Focus:** Explicitly describe movements (e.g., "The girl turns her head slowly," "leaves blowing in the wind", "waves crashing"). Use camera terms like "slow pan," "dolly zoom," "static shot," "tracking shot."
4. **Quality Tags:** Include necessary video quality tags (e.g., "4k," "high quality," "smooth motion," "hyper-realistic", "FHD").
5. **Constraint:** Output ONLY the prompt string. Do NOT output conversational text.
6. **Translation:** If input is non-English, translate to English first.
"""

    PROMPT_IMAGE_QWEN_CN = f"""
你是一位精通Qwen模型提示词的AI绘画专家。你的任务是将用户的输入扩写为一段高质量、细节丰富的中文自然语言绘画提示词。

**输入内容:** "{combined_text}"

**指令:**
1. **目标:** 生成一段画面感极强、描述细腻的中文Prompt，适用于Qwen-VL、Kolors等支持中文的生图模型。
2. **结构:** 遵循逻辑顺序：[主体与动作] > [详细环境背景] > [光影与氛围] > [构图与视角] > [艺术风格与媒介]。
3. **细节增强:** 丰富画面的纹理（如“丝绸般的质感”、“斑驳的墙面”）、光线（如“丁达尔效应”、“柔和的晨光”）和色彩描述。
4. **风格化:** 明确指定艺术风格（如“赛博朋克”、“水墨画”、“超写实摄影”、“吉卜力风格”）。
5. **约束:** 直接输出最终的扩写结果，不要包含“好的”、“以下是提示词”等对话内容。**必须保持中文输出**。
"""

    PROMPT_NSFW = f"""
You are an expert erotica writer and prompt engineer for adult content. Your task is to expand the user's input into a highly detailed, explicit, and sensory-rich NSFW image prompt.

**Input:** "{combined_text}"

**Instructions:**
1. **Goal:** Create an explicit, arousing, and visually detailed description suitable for adult content generation.
2. **Focus:** Emphasize anatomy (body shapes, curves, skin texture), physical interactions, facial expressions (pleasure, blush, desire), and sensory details (sweat, fluids, lighting).
3. **Structure:** [Subjects & Actions] > [Explicit Details & Angles] > [Outfit/Undress State] > [Environment & Atmosphere] > [Quality Tags].
4. **Constraint:** Be direct and descriptive. Do NOT use euphemisms. Output ONLY the prompt string. Do NOT output conversational text.
5. **Translation:** If input is non-English, translate to English first.
"""

    PROMPT_TRANSLATE_CN = f"Translate the following text into professional, descriptive Chinese. Output ONLY the translated text, no explanation: {combined_text}"
    PROMPT_TRANSLATE_EN = f"Translate the following text into professional, descriptive English. Output ONLY the translated text, no explanation: {combined_text}"
    PROMPT_NL_TO_TAGS = f"Convert this text into a concise, comma-separated list of Danbooru-style tags. Focus on visual elements. Output ONLY the tags: {combined_text}"
    PROMPT_TAGS_TO_NL = f"Convert these tags into a coherent, descriptive natural language paragraph. Focus on sentence flow and imagery. Output ONLY the paragraph: {combined_text}"

    prompt_map = {
        "Expansion (Photography)": PROMPT_PHOTO,
        "Expansion (Art)": PROMPT_ART,
        "Expansion (Tags)": PROMPT_TAGS,
        "Expansion (Video-Wan)": PROMPT_VIDEO_WAN,
        "Expansion (Qwen-Chinese)": PROMPT_IMAGE_QWEN_CN,
        "Expansion (NSFW)": PROMPT_NSFW,
        "Translate EN->CN": PROMPT_TRANSLATE_CN,
        "Translate CN->EN": PROMPT_TRANSLATE_EN,
        "Natural Language -> Tags": PROMPT_NL_TO_TAGS,
        "Tags -> Natural Language": PROMPT_TAGS_TO_NL
    }
    
    final_prompt = prompt_map.get(prompt_preset, combined_text)
    generated_prompt = ""

    current_config = get_extension_config()

    if model_selection == "Local-Qwen":
        generated_prompt = run_qwen_inference(
            text=final_prompt, 
            image=None, 
            max_new_tokens=max_length_slider, 
            seed=seed_slider
        )
        if unload_after_gen:
            unload_qwen_model()

    elif model_selection == "ZhipuAPI":
        zhipu_key = current_config.get("ZHIPUAI_API_KEY", "")
        if not zhipu_key:
            return "MISSING_KEY_ZHIPU", ""
            
        client = ZhipuAI(api_key=zhipu_key)
        response = client.chat.completions.create(
            model="GLM-4.6V-Flash",
            messages=[{"role": "system", "content": "You are a helpful creative assistant."}, {"role": "user", "content": final_prompt}],
        )
        generated_prompt = response.choices[0].message.content

    elif model_selection == "GeminiAPI":
        gemini_key = current_config.get("GEMINI_API_KEY", "")
        if not gemini_key:
            return "MISSING_KEY_GEMINI", ""

        configure_gemini()
        model = genai.GenerativeModel("gemini-2.5-flash")
        generation_config = genai.types.GenerationConfig(max_output_tokens=max_length_slider)
        try:
            response = model.generate_content(final_prompt, generation_config=generation_config)
            generated_prompt = response.text
        except Exception as e:
            return f"Gemini Error: {e}", ""

    return generated_prompt, f"<p>Live Seed: {actual_seed_value}</p>"

def create_ar_button(label, width, height, button_class="ar-button"):
    return gr.Button(label, elem_classes=button_class).click(fn=None, _js=f'sendToARbox({width}, {height})')

def simple_prompt_button(label, prompt, button_class="simple-prompt-button"):
    html_button = f"""
        <button class="{button_class}" onclick="sendToPromptbox('{prompt}', this)">
            <span class="label-top">{label}</span><br>
            <span class="label-bottom">{prompt}</span>
        </button>
    """
    return gr.HTML(html_button)

def load_prompts_csv(filepath=os.path.join(extension_path, "prompts.csv")):
    prompt_categories = {}
    try:
        with open(filepath, "r", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                category = row["category"]
                subcategory = row["subcategory"]
                label = row["label"]
                prompt = row["prompt"]

                if category not in prompt_categories:
                    prompt_categories[category] = {}
                if subcategory not in prompt_categories[category]:
                    prompt_categories[category][subcategory] = []

                prompt_categories[category][subcategory].append(f"{label}|{prompt}") 

        return prompt_categories

    except FileNotFoundError:
        print(f"Error: Prompts file not found at {filepath}")
        return {}

prompt_categories = load_prompts_csv()

def update_prompt_types(model_name):
    choices = [
        "Image Description - Tags",
        "Image Description - Natural Language",
        "Image Description - Photorealistic",
        "Image Description - Art Analysis",
        "Image Description - NSFW",
        "Image Edit - Teleport",
        "Image Edit - Move Camera",
        "Image Edit - Relight",
        "Image Edit - Composition Rebuild",
        "Image Edit - Product Photo",
        "Image Edit - Product Appearance Redesign",
        "Image Edit - Zoom",
        "Image Edit - Colorize",
        "Image Edit - Logo",
        "Image Edit - Tail Frame Generation",
        "Image Edit - Movie Poster",
        "Image Edit - Cartoonize",
        "Image Edit - Remove Text",
        "Image Edit - Hairdresser",
        "Image Edit - Wardrobe Makeover",
        "Image Edit - Gravure Pose",
        "Image Edit - Bodybuilder",
        "Image Edit - Remove Furniture",
        "Image Edit - Interior Design",
        "Image Edit - Architectural Facelift",
        "Image Edit - Clean Up",
        "Image Edit - Art Style",
        "Image Edit - Material Shift",
        "Image Edit - Emotion Shift",
        "Image Edit - Age Shift",
        "Image Edit - Seasonal Shift",
        "Image Edit - Composite Fusion",
    ]
    return gr.update(choices=choices, value="Image Description - Natural Language")

def modify_css(accent_color, minor_color):
    with open(css_file_path, 'r', encoding='utf-8') as file:
        css_content = file.read()

    accent_color_line = '--ctp-accent: '
    minor_color_line = '--ctp-minor: '

    if accent_color_line in css_content:
        start_index = css_content.index(accent_color_line) + len(accent_color_line)
        end_index = css_content.index(';', start_index)
        css_content = css_content[:start_index] + f'{accent_color}' + css_content[end_index:]

    if minor_color_line in css_content:
        start_index = css_content.index(minor_color_line) + len(minor_color_line)
        end_index = css_content.index(';', start_index)
        css_content = css_content[:start_index] + f'{minor_color}' + css_content[end_index:]

    with open(css_file_path, 'w', encoding='utf-8') as file:
        file.write(css_content)

    with open(color_file_path, 'w', encoding='utf-8') as color_file:
        color_file.write(f"{accent_color}\n{minor_color}")

    return accent_color, minor_color

def load_colors():
    if os.path.exists(color_file_path):
        with open(color_file_path, 'r', encoding='utf-8') as color_file:
            colors = color_file.read().strip().split('\n')
            if len(colors) == 2:
                return colors[0], colors[1]
    return "#b7ff00", "#517100" 

def generate_color_values(color1, color2, color3, color4, color5, color_conversion, prefix_mode):
    rgb_colors = [hex_to_dec(c) for c in [color1, color2, color3, color4, color5]]

    plain_english_colors = [get_webcolor_name(color) for color in rgb_colors]
    hex_colors = [f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}" for color in rgb_colors]
    rgb_colors_str = [str(c) for c in rgb_colors]

    colornamer_names = [colornamer.get_color_from_rgb(color) for color in rgb_colors] if colornamer else [{"xkcd_color": "N/A", "design_color": "N/A", "common_color": "N/A", "color_type": "N/A", "color_family": "N/A"}] * len(rgb_colors)
    xkcd_colors = [color["xkcd_color"] for color in colornamer_names]
    design_colors = [color["design_color"] for color in colornamer_names]
    common_colors = [color["common_color"] for color in colornamer_names]
    color_types = [color["color_type"] for color in colornamer_names]
    color_families = [color["color_family"] for color in colornamer_names]

    output_map = {
        "plain_english_colors": ", ".join(plain_english_colors),
        "rgb_colors": ", ".join(rgb_colors_str),
        "hex_colors": ", ".join(hex_colors),
        "xkcd_colors": ", ".join(xkcd_colors),
        "design_colors": ", ".join(design_colors),
        "common_colors": ", ".join(common_colors),
        "color_types": ", ".join(color_types),
        "color_families": ", ".join(color_families),
    }
    output_string = output_map[color_conversion]
    
    if prefix_mode == "Force":
        prefix_base = "Changes the color of the entire painting to a five-color palette: "
    elif prefix_mode == "Balance":
        prefix_base = "Remap all visual tones across the composition to a constrained five-color system: "

    if prefix_mode != "None":
        color_list = output_string.split(", ")
        if len(color_list) > 1:
            last_color = color_list.pop()
            color_string_with_and = ", ".join(color_list) + f" and {last_color}"
            final_output_string = f"{prefix_base}{color_string_with_and}."
        else:
            final_output_string = f"{prefix_base}{output_string}."
        return final_output_string.lower()
    else:
        return output_string

def hex_to_dec(inhex):
    try:
        rval = inhex[1:3]
        gval = inhex[3:5]
        bval = inhex[5:]
        rgbval = (int(rval, 16), int(gval, 16), int(bval, 16))
        return rgbval
    except (IndexError, ValueError):
        return (0, 0, 0)

def get_webcolor_name(rgb):
    webcolor_dict = {}
    for color_dict in [
        webcolors.CSS2_HEX_TO_NAMES,
        webcolors.CSS21_HEX_TO_NAMES,
        webcolors.CSS3_HEX_TO_NAMES,
        webcolors.HTML4_HEX_TO_NAMES,
    ]:
        webcolor_dict.update(color_dict)


    closest_match = None
    min_distance = float("inf")

    for hex, name in webcolor_dict.items():
        distance = sum(abs(a - b) for a, b in zip(rgb, webcolors.hex_to_rgb(hex)))
        if distance < min_distance:
            min_distance = distance
            closest_match = name

    return closest_match or "Unknown"

def generate_random_colors():
    available_palettes = [
        ArmyRose_7, Earth_7, Fall_7, Geyser_7, TealRose_7, Temps_7, Tropic_7, 
        Antique_10, Bold_10, Pastel_10, Prism_10, Safe_10, Vivid_10, 
        BluGrn_7, BluYl_7, BrwnYl_7, Burg_7, BurgYl_7, DarkMint_7, Emrld_7, Magenta_7, Mint_7, OrYel_7, Peach_7, PinkYl_7, Purp_7, PurpOr_7, RedOr_7, Sunset_7, SunsetDark_7, Teal_7, TealGrn_7, agGrnYl_7, agSunset_7,
        Balance_20, Curl_20, Delta_20, 
        Algae_20, Amp_20, Deep_20, Dense_20, Gray_20, Haline_20, Ice_20, Matter_20, Oxy_20, Phase_20, Solar_20, Speed_20, Tempo_20, Thermal_20, Turbid_20, 
        BrBG_11, PiYG_11, PRGn_11, PuOr_11, RdBu_11, RdGy_11, RdYlBu_11, RdYlGn_11, Spectral_11, 
        Set3_12, Pastel1_9, Accent_8, Paired_12, Set1_9, Set2_8, Dark2_8, Pastel2_8, 
        Blues_9, BuGn_9, BuPu_9, GnBu_9, Greens_9, Greys_9, Oranges_9, OrRd_9, PuBu_9, PuBuGn_9, PuRd_9, Purples_9, RdPu_9, Reds_9, YlGn_9, YlGnBu_9, YlOrBr_9, YlOrRd_9,
    ]

    selected_palette = random.choice(available_palettes)
    palette_colors = selected_palette.colors
    colors = random.sample(palette_colors, min(5, len(palette_colors)))
    hex_colors = ['#%02x%02x%02x' % (color[0], color[1], color[2]) for color in colors]

    return hex_colors

def add_tab():
    generate_styles_and_tags = generate_html_code()
    nopreview = os.path.join(extension_path, "nopreview.jpg")
    accent_color, minor_color = load_colors()
    cm_base_models = [
        "All", "SD 1.4", "SD 1.5", "SD 1.5 LCM", "SD 1.5 Hyper", "SD 2.0", "SD 2.1", 
        "SD 3", "SD 3.5", "SD 3.5 Large", "SD 3.5 Large Turbo", "SD 3.5 Medium", 
        "SDXL 1.0", "SDXL Lightning", "SDXL Hyper", "Pony", "Pony V7", 
        "Flux.1 S", "Flux.1 D", "Flux.1 Krea", "Flux.1 Kontext", "Flux.2 D", 
        "AuraFlow", "CogVideoX", "HiDream", "Hunyuan 1", "Hunyuan Video", 
        "Illustrious", "Kolors", "LTXV", "Lumina", "Mochi", "NoobAI", 
        "PixArt a", "PixArt E", "Qwen", "ZImageTurbo", "SVD", 
        "Wan Video 1.3B t2v", "Wan Video 14B t2v", "Wan Video 14B i2v 480p", "Wan Video 14B i2v 720p", 
        "Wan Video 2.2 TI2V-5B", "Wan Video 2.2 I2V-A14B", "Wan Video 2.2 T2V-A14B", 
        "Other"
    ]
    with gr.Blocks(analytics_enabled=False,) as ui:
        with gr.Tabs(elem_id = "Stylez"): 
            gr.HTML("""<div id="stylezPreviewBoxid" class="stylezPreviewBox"><p id="stylezPreviewPositive">test</p><p id="stylezPreviewNegative">test</p></div>""")
            with gr.TabItem(label="Styles", elem_id="styles_libary"):
                with gr.Row():
                    quicklist_column = gr.Column(elem_id="style_quicklist_column", visible=False)                     
                    with quicklist_column: 
                        with gr.Row():
                            gr.Text("Quicksave",show_label=False)
                            with gr.Row():
                                stylezquicksave_add = gr.Button("Add" ,elem_classes="stylezquicksave_add")
                                stylezquicksave_clear = gr.Button("Clear" ,elem_classes="stylezquicksave_add")
                        with gr.Row(elem_id="style_cards_row"):                        
                                gr.HTML("""<ul id="styles_quicksave_list"></ul>""")
                    with gr.Column():
                        with gr.Row(elem_id="style_search_search"):
                            Style_Search = gr.Textbox('', label="Search:", elem_id="style_search", placeholder="Search...", elem_classes="textbox", lines=1,scale=3)
                            category_dropdown = gr.Dropdown(label="Category:", choices=generate_styles_and_tags[1], value="All", elem_id="style_Catagory", elem_classes="dropdown styles_dropdown",scale=1)
                            refresh_button = gr.Button(refresh_symbol, elem_id="style_refresh", elem_classes="tool")
                        with gr.Row():
                            with gr.Column(elem_id="style_cards_column"):
                                Styles_html=gr.HTML(generate_styles_and_tags[0])
                with gr.Row(elem_id="stylesPreviewRow"):
                    gr.Checkbox(value=True,label="Prompt", elem_id="styles_apply_prompt", elem_classes="styles_checkbox checkbox")
                    gr.Checkbox(value=True,label="Negative", elem_id="styles_apply_neg", elem_classes="styles_checkbox checkbox")
                    gr.Checkbox(value=True,label="Hover", elem_id="HoverOverStyle_preview", elem_classes="styles_checkbox checkbox")
                    oldstylesCB = gr.Checkbox(value=True,label="HideOld", elem_id="hide_default_styles", elem_classes="styles_checkbox checkbox", interactive=True)
                    setattr(oldstylesCB,"do_not_save_to_config",True)
                    hide_quicklist_checkbox = gr.Checkbox(value=True, label="HideQuick", elem_id="hide_quicklist_checkbox", elem_classes="styles_checkbox checkbox") 
                    card_size_slider = gr.Slider(value=card_size_value,minimum=card_size_min,maximum=card_size_max,label="Size:", elem_id="card_thumb_size")
                    setattr(card_size_slider,"do_not_save_to_config",True)
                with gr.Row(elem_id="stylesfavourite"):
                    favourite_temp = gr.Text(elem_id="favouriteTempTxt",interactive=False,label="Positive:",lines=2,visible=False)
                    add_favourite_btn = gr.Button(elem_id="stylezAddFavourite",visible=False)
                    remove_favourite_btn = gr.Button(elem_id="stylezRemoveFavourite",visible=False)

            civitai_prompt_tab = gr.TabItem(label="CivitAI", elem_id="civitai_prompt", visible=True) 
            with civitai_prompt_tab: 
                with gr.Row():
                    nsfwlvl = gr.Dropdown(label="NSFW:", choices=["None", "Soft"], value="None", elem_id="civit_nsfwfilter", elem_classes="dropdown styles_dropdown", scale=1)
                    sortcivit = gr.Dropdown(label="Sort:", choices=["Most Reactions", "Most Comments", "Newest"], value="Most Reactions", elem_id="civit_sortfilter", elem_classes="dropdown styles_dropdown", scale=1)
                    periodcivit = gr.Dropdown(label="Period:", choices=["AllTime", "Year", "Month", "Week", "Day"], value="Day", elem_id="civit_periodfilter", elem_classes="dropdown styles_dropdown", scale=1)
                    tags = gr.Dropdown(
                        label="Tags:", 
                        choices=tagschoices, 
                        value="NONE", 
                        elem_id="civit_tags_filter", 
                        elem_classes="dropdown styles_dropdown", 
                        scale=1
                    )
                    civitAI_refresh = gr.Button(refresh_symbol, elem_id="style_refresh", elem_classes="tool", scale=1)
                    pagenumber = gr.Dropdown(
                        label="Page:", 
                        choices=[str(i) for i in range(1, 11)], 
                        value="1", 
                        elem_id="civit_page_dropdown", 
                        elem_classes="dropdown styles_dropdown", 
                        scale=1,
                        visible=False
                    )
                    username_input = gr.Textbox(label="Username:", placeholder="Enter username", elem_id="civit_username_input", elem_classes="textbox", scale=3)
                    show_empty_prompt = gr.Checkbox(label="ShowMissing", value=False, elem_id="show_empty_prompt", scale=1)
                    international_version_checkbox = gr.Checkbox(label="GlobalAPI", value=True, elem_id="international_version_checkbox", scale=1)
                    civitai_send_prompts_only = gr.Checkbox(label="PromptOnly", value=False, elem_id="civitai_send_prompts_only", scale=1)
                with gr.Row():
                    with gr.Column(elem_id="civit_cards_column"):
                        gr.HTML(f"""<div><div id="civitaiimages_loading"><p>Loading...</p></div><div onscroll="civitaiaCursorLoad(this)" id="civitai_cardholder" data-nopreview='{nopreview}'></div></div>""")

            civitai_models_tab = gr.TabItem(label="CivitMD", elem_id="civitai_models_tab", visible=True)
            with civitai_models_tab:
                with gr.Row():
                    cm_types = gr.Dropdown(label="Type:", choices=["All", "Checkpoint", "LORA", "LoCon", "DoRA", "VAE", "Controlnet", "Upscaler", "TextualInversion"], value="Checkpoint", elem_id="cm_type_filter", elem_classes="dropdown styles_dropdown", scale=1)
                    cm_basemodel = gr.Dropdown(label="BaseModels:", choices=cm_base_models, value="All", elem_id="cm_basemodel_filter", elem_classes="dropdown styles_dropdown", scale=1)
                    cm_sort = gr.Dropdown(label="Sort: ", choices=["Highest Rated", "Most Downloaded", "Newest"], value="Most Downloaded", elem_id="cm_sort_filter", elem_classes="dropdown styles_dropdown", scale=1)
                    cm_period = gr.Dropdown(label="Period: ", choices=["AllTime", "Year", "Month", "Week", "Day"], value="AllTime", elem_id="cm_period_filter", elem_classes="dropdown styles_dropdown", scale=1)

                with gr.Row():
                    cm_search = gr.Textbox(label="Search:", placeholder="Search models...", elem_id="cm_search_input", elem_classes="textbox", scale=2)
                    cm_nsfw = gr.Checkbox(label="NSFW", value=False, elem_id="cm_nsfw_checkbox", scale=0)
                    cm_refresh = gr.Button(refresh_symbol, elem_id="cm_refresh_btn", elem_classes="tool", scale=0)
                
                with gr.Row():
                    with gr.Column(elem_id="civit_models_card_column"):
                        gr.HTML(f"""
                        <div style="position:relative; height: 100%;">
                            <div id="civitaimodels_loading" style="display:none; position:absolute; z-index:9; background:#000000bd; width:100%; height:100%; text-align:center; padding-top:20%;">
                                <p style="color:var(--button-primary-background-fill); font-size:50px;">Loading...</p>
                            </div>
                            <div onscroll="civitaiModelsCursorLoad(this)" id="civitai_models_cardholder" data-nopreview='{nopreview}' style="height: 48.7vh; overflow: auto; padding-top: 3px;"></div>
                        </div>
                        """)

            simple_prompt_tab = gr.TabItem(label="Prompts", elem_id="simple_prompt", visible=True) 
            with simple_prompt_tab: 
                with gr.Tabs(elem_id="simple_prompt_category"):
                    for category_name, subcategories in prompt_categories.items():
                        with gr.TabItem(label=category_name):
                            with gr.Tabs(elem_id="simple_prompt_subcategory"):
                                for subcategory_name, prompts in subcategories.items():
                                    with gr.TabItem(label=subcategory_name):
                                        with gr.Column(elem_id="simple_prompt_button_columns"):
                                            num_cols = 5 
                                            for i in range(0, len(prompts), num_cols):
                                                with gr.Row():
                                                    row_prompts = prompts[i:i + num_cols]
                                                    for prompt_pair in row_prompts:
                                                        label, prompt = prompt_pair.split("|")
                                                        simple_prompt_button(label, prompt)
                                                    for _ in range(num_cols - len(row_prompts)):
                                                        gr.HTML("<div style='width: 108px;'></div>")

            prompt_enhancement_tab = gr.TabItem(label="Extend", elem_id="prompt enhancement", visible=True)
            with prompt_enhancement_tab:
                with gr.Row():
                    with gr.Column():
                        prompt_input_txt = gr.Textbox(
                            label="Input:", 
                            lines=7, 
                            placeholder="Enter prompt here. First run downloads models automatically (check console). Ensure API Key in config.json if using API.", 
                            elem_classes="prompt_box"
                        )
                        with gr.Row():
                            prompt_gen_btn = gr.Button("GetPrompt", elem_id="prompt_gen_btn")
                        
                        with gr.Row():
                            prompt_model_selector = gr.Dropdown(
                                label="Model:",
                                choices=["Local-Qwen", "ZhipuAPI", "GeminiAPI"],
                                value="Local-Qwen",
                                elem_id="prompt_model_selector"
                            )
                            prompt_preset_selector = gr.Dropdown(
                                label="Preset:",
                                choices=[
                                    "Expansion (Photography)",
                                    "Expansion (Art)",
                                    "Expansion (Tags)",
                                    "Expansion (Video-Wan)",
                                    "Expansion (Qwen-Chinese)",
                                    "Expansion (NSFW)",
                                    "Translate EN->CN",
                                    "Translate CN->EN",
                                    "Natural Language -> Tags",
                                    "Tags -> Natural Language"
                                ],
                                value="Expansion (Photography)",
                                elem_id="prompt_preset_selector"
                            )
                        
                        with gr.Row():
                            mediums_dropdown_value = gr.Dropdown(
                                label="Mediums:",
                                choices=["None", "Random"] + list(mediums_mapping.keys()),  
                                value="None",  
                                elem_id="dropdown_mediums_selector"
                            )
                            
                            style_dropdown_value = gr.Dropdown(
                                label="Style:",
                                choices=["None", "Random"] + list(style_mapping.keys()), 
                                value="None", 
                                elem_id="dropdown_style_selector"
                            )

                        with gr.Row():
                            max_length_slider = gr.Slider(
                                label="MaxLen:", 
                                minimum=25, 
                                maximum=8192, 
                                value=8192, 
                                step=1
                            )

                            seed_slider = gr.Slider(
                                label="Seed:", 
                                minimum=-1, 
                                maximum=2**32-1, 
                                value=-1, 
                                step=1
                            )

                        with gr.Row():
                            prompt_unload_checkbox = gr.Checkbox(
                                label="Unload the model and clear the VRAM",
                                value=True,
                                elem_id="prompt_unload_checkbox"
                            )
                    with gr.Column():
                        gr.HTML("""Output：""")
                        prompt_output_html = gr.HTML(
                            value="<br>", 
                            elem_id="prompt_output_html", 
                            elem_classes="prompt_box_html" 
                        )
                        actual_seed_html = gr.HTML(
                            value="", 
                            elem_id="actual_seed_html" 
                        )
                        with gr.Row():
                            gen_btn = gr.Button(value="Generate", variant="primary", elem_id="prompt_gen_btn")
                            apply_btn = gr.Button("Apply", elem_id="prompt_apply_btn")

            img2prompt_tab = gr.TabItem(label="Interrogate", elem_id="image to prompt", visible=True) 
            with img2prompt_tab: 
                with gr.Row():
                    with gr.Column():
                        img2prompt_image = gr.Image(
                            sources=["upload"],
                            interactive=True,
                            type="pil",
                            elem_classes="stylez_promptgenbox", 
                            height=320,
                        )
                        img2prompt_model_name = gr.Dropdown(
                            label="Model:",
                            choices=img2prompt_models,
                            value="Local-Qwen",
                        )
                        img2prompt_type = gr.Dropdown(
                            label="Prompt Types:",
                            choices=img2prompt_types,
                            value="Image Description - Natural Language",
                        )
                        img2prompt_image_url_transport = gr.Textbox(visible=False, elem_id="img2prompt_image_url_transport")
                        with gr.Row():
                            img2prompt_max_new_token = gr.Slider(
                                label="MaxLen:", value=8192, minimum=1, maximum=8192, step=1
                            )
                            img2prompt_seed = gr.Slider(
                                label="Seed:", value=-1, minimum=-1, maximum=2**32-1, step=1
                            )
                        img2prompt_unload_checkbox = gr.Checkbox(
                            label="Unload the model and clear the VRAM",
                            value=True,
                            elem_id="img2prompt_unload_checkbox"
                        )
                    with gr.Column():
                        gr.HTML("""Output：""")
                        img2prompt_tags = gr.State(value="")
                        img2prompt_html_tags = gr.HTML(
                            value="<br><br><br><br>",
                            label="Tags",
                            elem_id="tags",
                            elem_classes="stylez_promptgenbox", 
                        )
                        img2prompt_seed_html = gr.HTML(
                            value="", 
                            elem_id="img2prompt_seed_html"
                        )
                        with gr.Row():
                            img2prompt_generate_btn = gr.Button(
                                value="Generate", variant="primary", elem_id="style_promptgen_btn"
                            )
                            img2prompt_apply_btn = gr.Button("Apply", elem_id="florence_apply_btn")

            with gr.TabItem(label="Edit", elem_id="stylez_edit_tab"):
                with gr.Row():
                    with gr.Column():
                        with gr.Row():
                            style_title_txt = gr.Textbox(label="Title:", lines=1,placeholder="Title here",elem_id="style_title_txt")
                            style_description_txt = gr.Textbox(label="Description:", lines=1,placeholder="Description here", elem_id="style_description_txt")
                        style_prompt_txt = gr.Textbox(label="Prompt:", lines=2,placeholder="Prompt here", elem_id="style_prompt_txt")
                        style_negative_txt = gr.Textbox(label="Negative:", lines=2,placeholder="Negative here", elem_id="style_negative_txt")
                        with gr.Row(elem_id="steps_cfg_scale"):
                            style_steps = gr.Textbox(label="Steps:", value="20", elem_id="style_steps")  
                            style_cfg_scale = gr.Textbox(label="CFG:", value="1", elem_id="style_cfg_scale") 
                        with gr.Row(elem_id="seed_size"):
                            style_seed = gr.Textbox(label="Seed:", value="-1", elem_id="style_seed")  
                            style_size = gr.Textbox(label="Size:", value="1024,1024", elem_id="style_size") 
                        with gr.Row(elem_id="sampling_scheduler"):
                            style_sampling = gr.Textbox(label="Sampler:", value="Euler", elem_id="style_sampling")
                            style_scheduler = gr.Textbox(label="Scheduler:", value="Simple", elem_id="style_scheduler")
                    with gr.Column():
                        with gr.Row():
                            style_save_btn = gr.Button(save_symbol, elem_classes="tool", elem_id="style_save_btn")
                            style_clear_btn = gr.Button(clear_symbol, elem_classes="tool" ,elem_id="style_clear_btn")
                            style_delete_btn = gr.Button(delete_style, elem_classes="tool", elem_id="style_delete_btn")
                        thumbnailbox = gr.Image(value=None,label="Thumbnail (1:1):",elem_id="style_thumbnailbox",elem_classes="image",interactive=True,type='pil')
                        style_img_url_txt = gr.Text(label=None,lines=1,placeholder="Invisible textbox", elem_id="style_img_url_txt",visible=False)
                with gr.Row():
                    style_grab_current_btn = gr.Button("Fetch", elem_id="style_grab_current_btn")
                    style_lastgen_btn =gr.Button("GrabLast", elem_id="style_lastgen_btn")
                with gr.Row():
                    with gr.Column():
                            style_filename_txt = gr.Textbox(label="Filename:", lines=1,placeholder="Filename", elem_id="style_filename_txt")
                            style_filname_check = gr.HTML("""<p id="style_filename_check">Enter filename!</p>""",elem_id="style_filename_check_container")
                    with gr.Column():
                        with gr.Row():
                            style_savefolder_txt = gr.Dropdown(label="Folder:", value="Styles", choices=generate_styles_and_tags[2], elem_id="style_savefolder_txt", elem_classes="dropdown",allow_custom_value=True)
                            style_savefolder_temp = gr.Textbox(label="Save Folder:", lines=1, elem_id="style_savefolder_temp",visible=False)
                            style_savefolder_refrsh_btn = gr.Button(refresh_symbol, elem_classes="tool")

            color_palette_tab = gr.TabItem(label="Palette", elem_id="color_palette", visible=True) 
            with color_palette_tab: 
                with gr.Row():
                    with gr.Column():
                        color1 = gr.ColorPicker(label="Color1", value="#fafafa", elem_id="palette_color_1", elem_classes="palette-color-picker")
                        color2 = gr.ColorPicker(label="Color2", value="#c8c8c8", elem_id="palette_color_2", elem_classes="palette-color-picker")
                        color3 = gr.ColorPicker(label="Color3", value="#969696", elem_id="palette_color_3", elem_classes="palette-color-picker")
                        color4 = gr.ColorPicker(label="Color4", value="#646464", elem_id="palette_color_4", elem_classes="palette-color-picker")
                        color5 = gr.ColorPicker(label="Color5", value="#323232", elem_id="palette_color_5", elem_classes="palette-color-picker")
                    with gr.Column():
                        with gr.Row():
                            color_conversion = gr.Dropdown(
                                label="Convert:",
                                choices=["plain_english_colors", "rgb_colors", "hex_colors", "xkcd_colors", "design_colors", "common_colors", "color_types", "color_families"],
                                value="xkcd_colors"
                            )
                            prefix_mode_dropdown = gr.Dropdown(
                                label="Prefix:",
                                choices=[
                                    "None",
                                    "Force",
                                    "Balance"
                                ],
                                value="Balance", 
                                elem_id="prefix_mode_dropdown"
                            )
                        random_colors_btn = gr.Button("Random", elem_id="random_colors_btn") 
                        color_values_output = gr.Textbox(label="Values:", lines=2)
                        with gr.Row():
                            generate_color_values_btn = gr.Button("Generate")
                            apply_color_values_btn = gr.Button("Apply")

            size_settings_tab = gr.TabItem(label="Size", elem_id="Size settings", visible=True) 
            with size_settings_tab: 
                with gr.Row():
                    with gr.Column():
                        gr.HTML("""<p style="color: var(--ctp-accent); font-size: 14px; height: 14px; margin: -5px 0px;">Width x Height (SDXL):</p>""")
                        with gr.Row():
                            create_ar_button("1024×1024 | 1:1", 1024, 1024, button_class="ar2-button")
                        with gr.Row():
                            create_ar_button("576×1728 | 1:3", 576, 1728)
                            create_ar_button("1728×576 | 3:1", 1728, 576)
                            create_ar_button("576×1664 | 9:26", 576, 1664)
                            create_ar_button("1664×576 | 26:9", 1664, 576)
                        with gr.Row():
                            create_ar_button("640×1600 | 2:5", 640, 1600)
                            create_ar_button("1600×640 | 5:2", 1600, 640)
                            create_ar_button("640×1536 | 5:12", 640, 1536)
                            create_ar_button("1536×640 | 12:5", 1536, 640)
                        with gr.Row():
                            create_ar_button("704×1472 | 11:23", 704, 1472)
                            create_ar_button("1472×704 | 23:11", 1472, 704)
                            create_ar_button("704×1408 | 1:2", 704, 1408)
                            create_ar_button("1408×704 | 2:1", 1408, 704)
                        with gr.Row():
                            create_ar_button("704×1344 | 11:21", 704, 1344)
                            create_ar_button("1344×704 | 21:11", 1344, 704)
                            create_ar_button("768×1344 | 4:7", 768, 1344)
                            create_ar_button("1344×768 | 7:4", 1344, 768, button_class="ar2-button")
                        with gr.Row():
                            create_ar_button("768×1280 | 3:5", 768, 1280)
                            create_ar_button("1280×768 | 5:3", 1280, 768)
                            create_ar_button("832×1216 | 13:19", 832, 1216, button_class="ar2-button")
                            create_ar_button("1216×832 | 19:13", 1216, 832)
                        with gr.Row():
                            create_ar_button("832×1152 | 13:18", 832, 1152)
                            create_ar_button("1152×832 | 18:13", 1152, 832)
                            create_ar_button("896×1152 | 7:9", 896, 1152)
                            create_ar_button("1152×896 | 9:7", 1152, 896)
                        with gr.Row():
                            create_ar_button("896×1088 | 14:17", 896, 1088)
                            create_ar_button("1088×896 | 17:14", 1088, 896)
                            create_ar_button("960×1088 | 15:17", 960, 1088)
                            create_ar_button("1088×960 | 17:15", 1088, 960)
                        with gr.Row():
                            create_ar_button("960×1024 | 15:16", 960, 1024)
                            create_ar_button("1024×960 | 16:15", 1024, 960)
                        gr.HTML("""<p style="color: var(--ctp-accent); font-size: 14px; height: 14px; margin: -5px 0px;">Width x Height (SD1.5):</p>""")
                        with gr.Row():
                            create_ar_button("512×512 | 1:1", 512, 512, button_class="ar2-button")
                            create_ar_button("768×768 | 1:1", 768, 768)
                            create_ar_button("576×1024 | 9:16", 576, 1024)
                            create_ar_button("1024×576 | 16:9", 1024, 576)
                        with gr.Row():
                            create_ar_button("512×768 | 2:3", 512, 768)
                            create_ar_button("768×512 | 3:2", 768, 512)
                            create_ar_button("576×768 | 3:4", 576, 768)
                            create_ar_button("768×576 | 4:3", 768, 576)
                        gr.HTML("""<p style="color: var(--ctp-accent); font-size: 14px; height: 14px; margin: -5px 0px;">Width x Height (Custom) approx:</p>""")
                        with gr.Row():
                            create_ar_button("880×1176 | 3:4", 880, 1176)
                            create_ar_button("1176×880 | 4:3", 1176, 880)
                            create_ar_button("768×1360 | 9:16", 768, 1360)
                            create_ar_button("1360×768 | 16:9", 1360, 768)
                        with gr.Row():
                            create_ar_button("1576×656 | 2.39:1", 1576, 656)
                            create_ar_button("1392×752 | 1.85:1", 1392, 752)
                            create_ar_button("1176×888 | 1.33:1", 1176, 888)
                            create_ar_button("1568×664 | 2.35:1", 1568, 664)
                        with gr.Row():
                            create_ar_button("1312×792 | 1.66:1", 1312, 792)
                            create_ar_button("1224×856 | 1.43:1", 1224, 856)
                            create_ar_button("912×1144 | 4:5", 912, 1144)
                            create_ar_button("1296×800 | 1.618:1", 1296, 800)
                        gr.HTML("""<p style="color: var(--ctp-accent); font-size: 14px; height: 14px; margin: -5px 0px;">Width x Height (Custom) forced:</p>""")
                        with gr.Row():
                            create_ar_button("720×1280 | 9:16", 720, 1280)
                            create_ar_button("1280×720 | 16:9", 1280, 720)
                            create_ar_button("800×1280 | 10:16", 800, 1280)
                            create_ar_button("1280×800 | 16:10", 1280, 800)

            with gr.TabItem(label="Theme", elem_id="UI settings"):
                gr.Markdown("""
                <p style="color: var(--ctp-accent); font-size: 18px; margin-bottom: 8px; height: 12px;">Dark Theme Settings:</p>
                """)
                with gr.Row(elem_id="colorPickerRow"):
                    accent_color_picker = gr.ColorPicker(label="Accent Color:", value=accent_color, elem_classes="theme-color-picker")
                    minor_color_picker = gr.ColorPicker(label="Neutral Color:", value=minor_color, elem_classes="theme-color-picker")
                    color_apply_button = gr.Button("Apply")
                num_cols = 5 
                with gr.Row(elem_id="theme_preset_row"):
                    for i, (theme_name, theme_data) in enumerate(theme_presets.items()):
                        with gr.Column(min_width=120):
                            gr.Button(theme_name, elem_classes=[theme_data["css_class"]]).click(
                                fn=lambda theme=theme_name: theme_presets[theme]["colors"],
                                outputs=[accent_color_picker, minor_color_picker],
                                _js=f"applyThemePreset"
                            )
                gr.Markdown("""
                <p style="color: var(--ctp-accent); font-size: 18px; margin-bottom: 8px; height: 12px;">Panel Toggle:</p>
                """)
                with gr.Row(elem_id="function_panel"):
                    show_civitai_prompt_checkbox = gr.Checkbox(value=True, label="CivitAI", elem_id="show_civitai_prompt_checkbox", elem_classes="styles_checkbox checkbox")
                    show_civitai_models_checkbox = gr.Checkbox(value=True, label="CivitMD", elem_id="show_civitai_models_checkbox", elem_classes="styles_checkbox checkbox")
                    show_simple_prompt_checkbox = gr.Checkbox(value=True, label="Prompts", elem_id="show_simple_prompt_checkbox", elem_classes="styles_checkbox checkbox")
                    show_extend_checkbox = gr.Checkbox(value=True, label="Extend", elem_id="show_extend_checkbox", elem_classes="styles_checkbox checkbox")
                    show_interrogate_checkbox = gr.Checkbox(value=True, label="Interrogate", elem_id="show_interrogate_checkbox", elem_classes="styles_checkbox checkbox")
                    show_color_palette_checkbox = gr.Checkbox(value=True, label="Palette", elem_id="show_color_palette_checkbox", elem_classes="styles_checkbox checkbox")
                    show_size_settings_checkbox = gr.Checkbox(value=True, label="Size", elem_id="show_size_settings_checkbox", elem_classes="styles_checkbox checkbox")
                gr.Markdown("""
                <p style="color: var(--ctp-accent); font-size: 18px; margin-bottom: 8px; height: 12px;">Notes:</p>
                <p style="margin-bottom: 8px;"><span style="color: var(--ctp-accent);">1. </span>Pay attention to the prompt format modification of other prompt plugins to the text box, such as the <span style="color: var(--ctp-accent);">All in one</span> plugin, please open the setting menu and click the second icon to adjust the prompt format (check the second item to remove the last comma of the Prompt, and uncheck all other items).</p>
                <p style="margin-bottom: 8px;"><span style="color: var(--ctp-accent);">2. </span>Style editing tips: Any prompt containing the keyword <span style="color: var(--ctp-accent);">{prompt}</span> will automatically grab your current prompt and insert it into the position of <span style="color: var(--ctp-accent);">{prompt}</span>. A simple example, you have a style prompt written like this <span style="color: Gray;">A dynamic, black-and-white graphic novel scene with intense action, a paiting of {prompt}</span>, now you enter <span style="color: Gray;">Several stray cats</span> in the positive prompt, when you apply this style template, the positive prompt will become <span style="color: Gray;">A dynamic, black-and-white graphic novel scene with intense action, a paiting of Several stray cats</span>. In short, if you want to edit the style template yourself, you can look at the format of the existing template first.</p>
                """)
        prompt_gen_btn.click(fn=None, _js="stylesgrabprompt", outputs=[prompt_input_txt])
        apply_btn.click(fn=None, _js='sendToPromtbox', inputs=[prompt_output_html])
        img2prompt_apply_btn.click(
            fn=None,
            _js='applyGeneratedPrompt',
            inputs=[img2prompt_html_tags], 
            outputs=[],
        )
        img2prompt_image_url_transport.change(
            fn=img_to_thumbnail,
            inputs=[img2prompt_image_url_transport],
            outputs=[img2prompt_image]
        )
        gen_btn.click(
            fn=wrap_gradio_gpu_call(generate_text_prompt),
            inputs=[prompt_model_selector, prompt_preset_selector, prompt_input_txt, mediums_dropdown_value, style_dropdown_value, max_length_slider, seed_slider, prompt_unload_checkbox],
            outputs=[prompt_output_html, actual_seed_html]
        )
        oldstylesCB.change(fn=None,inputs=[oldstylesCB],_js="hideOldStyles")
        refresh_button.click(fn=refresh_styles,inputs=[category_dropdown], outputs=[Styles_html,category_dropdown,category_dropdown,style_savefolder_txt])
        card_size_slider.release(fn=save_card_def,inputs=[card_size_slider])
        card_size_slider.change(fn=None,inputs=[card_size_slider],_js="cardSizeChange")
        category_dropdown.change(fn=None,_js="filterSearch",inputs=[category_dropdown,Style_Search])
        Style_Search.change(fn=None,_js="filterSearch",inputs=[category_dropdown,Style_Search])
        style_img_url_txt.change(fn=img_to_thumbnail, inputs=[style_img_url_txt],outputs=[thumbnailbox])
        style_grab_current_btn.click(fn=None,_js='grabCurrentSettings')
        style_lastgen_btn.click(fn=None,_js='grabLastGeneratedimage')
        style_savefolder_refrsh_btn.click(fn=refresh_styles,inputs=[category_dropdown], outputs=[Styles_html,category_dropdown,category_dropdown,style_savefolder_txt])
        style_save_btn.click(
            fn=save_style,
            inputs=[style_title_txt, thumbnailbox, style_description_txt, style_prompt_txt, style_negative_txt, style_steps, style_cfg_scale, style_seed, style_size, style_sampling, style_scheduler, style_filename_txt, style_savefolder_temp],
            outputs=[style_filname_check]
        )
        style_filename_txt.change(fn=filename_check, inputs=[style_savefolder_temp,style_filename_txt], outputs=[style_filname_check])
        style_savefolder_txt.change(fn=tempfolderbox, inputs=[style_savefolder_txt], outputs=[style_savefolder_temp])
        style_savefolder_temp.change(fn=filename_check, inputs=[style_savefolder_temp,style_filename_txt], outputs=[style_filname_check])
        style_clear_btn.click(fn=clear_style, outputs=[style_title_txt,style_img_url_txt,thumbnailbox,style_description_txt,style_prompt_txt,style_negative_txt,style_filename_txt])
        style_delete_btn.click(fn=deletestyle, inputs=[style_savefolder_temp,style_filename_txt])
        add_favourite_btn.click(fn=addToFavourite, inputs=[favourite_temp])
        remove_favourite_btn.click(fn=removeFavourite, inputs=[favourite_temp])
        stylezquicksave_add.click(fn=None,_js="addQuicksave")
        stylezquicksave_clear.click(fn=None,_js="clearquicklist")
        
        img2prompt_generate_btn.click(
            fn=wrap_gradio_gpu_call(generate_caption_fn),
            inputs=[img2prompt_image, img2prompt_model_name, img2prompt_max_new_token, img2prompt_type, img2prompt_unload_checkbox, img2prompt_seed],
            outputs=[img2prompt_tags, img2prompt_html_tags, img2prompt_seed_html],
        )
        img2prompt_model_name.change(
            fn=update_prompt_types,
            inputs=img2prompt_model_name,
            outputs=img2prompt_type,
        )
        
        civitAI_refresh.click(fn=None, _js="refreshfetchCivitai", inputs=[nsfwlvl, sortcivit, periodcivit, tags, username_input, pagenumber, show_empty_prompt, international_version_checkbox])
        periodcivit.change(fn=None, _js="refreshfetchCivitai", inputs=[nsfwlvl, sortcivit, periodcivit, tags, username_input, pagenumber, show_empty_prompt, international_version_checkbox])
        sortcivit.change(fn=None, _js="refreshfetchCivitai", inputs=[nsfwlvl, sortcivit, periodcivit, tags, username_input, pagenumber, show_empty_prompt, international_version_checkbox])
        nsfwlvl.change(fn=None, _js="refreshfetchCivitai", inputs=[nsfwlvl, sortcivit, periodcivit, tags, username_input, pagenumber, show_empty_prompt, international_version_checkbox])
        tags.change(fn=None, _js="refreshfetchCivitai", inputs=[nsfwlvl, sortcivit, periodcivit, tags, username_input, pagenumber, show_empty_prompt, international_version_checkbox])
        pagenumber.change(fn=None, _js="refreshfetchCivitai", inputs=[nsfwlvl, sortcivit, periodcivit, tags, username_input, pagenumber, show_empty_prompt, international_version_checkbox])
        username_input.submit(fn=None, _js="refreshfetchCivitai", inputs=[nsfwlvl, sortcivit, periodcivit, tags, username_input, pagenumber, show_empty_prompt, international_version_checkbox])
        show_empty_prompt.change(fn=None, _js="refreshfetchCivitai", inputs=[nsfwlvl, sortcivit, periodcivit, tags, username_input, pagenumber, show_empty_prompt, international_version_checkbox])
        international_version_checkbox.change(fn=None, _js="refreshfetchCivitai", inputs=[nsfwlvl, sortcivit, periodcivit, tags, username_input, pagenumber, show_empty_prompt, international_version_checkbox])
        color_apply_button.click(
            fn=modify_css,
            inputs=[accent_color_picker, minor_color_picker],
            outputs=[accent_color_picker, minor_color_picker]
        )
        color_apply_button.click(
            fn=None,
            inputs=[accent_color_picker, minor_color_picker],
            outputs=[],
            _js="updateStylezTheme"
        )
        generate_color_values_btn.click(
            fn=generate_color_values,
            inputs=[color1, color2, color3, color4, color5, color_conversion, prefix_mode_dropdown],
            outputs=color_values_output
        )
        apply_color_values_btn.click(
            fn=None,
            inputs=color_values_output,
            _js="apply_colors_to_prompt"
        )
        random_colors_btn.click(
            fn=generate_random_colors,
            outputs=[color1, color2, color3, color4, color5],
            _js="apply_random_colors"
        )
        hide_quicklist_checkbox.change(
            fn=lambda value: gr.update(visible=not value),
            inputs=hide_quicklist_checkbox,
            outputs=quicklist_column
        )
        show_civitai_prompt_checkbox.change(
            fn=lambda value: gr.update(visible=value),
            inputs=show_civitai_prompt_checkbox,
            outputs=civitai_prompt_tab,
        )
        show_civitai_models_checkbox.change(
            fn=lambda value: gr.update(visible=value),
            inputs=show_civitai_models_checkbox,
            outputs=civitai_models_tab,
        )
        show_simple_prompt_checkbox.change(
            fn=lambda value: gr.update(visible=value),
            inputs=show_simple_prompt_checkbox,
            outputs=simple_prompt_tab,
        )
        show_extend_checkbox.change(
            fn=lambda value: gr.update(visible=value),
            inputs=show_extend_checkbox,
            outputs=prompt_enhancement_tab,
        )

        show_interrogate_checkbox.change(
            fn=lambda value: gr.update(visible=value),
            inputs=show_interrogate_checkbox,
            outputs=img2prompt_tab,
        )
        show_color_palette_checkbox.change(
            fn=lambda value: gr.update(visible=value),
            inputs=show_color_palette_checkbox,
            outputs=color_palette_tab,
        )
        show_size_settings_checkbox.change(
            fn=lambda value: gr.update(visible=value),
            inputs=show_size_settings_checkbox,
            outputs=size_settings_tab,
        )

        cm_server_input = gr.Textbox(visible=False, elem_id="cm_server_params_input")
        cm_server_output = gr.Textbox(visible=False, elem_id="cm_server_data_output")
        cm_server_btn = gr.Button(visible=False, elem_id="cm_server_fetch_btn")

        cm_download_info = gr.Textbox(visible=False, elem_id="cm_download_info_box")
        cm_download_log = gr.Textbox(visible=False, elem_id="cm_download_log_box")
        cm_download_btn = gr.Button(visible=False, elem_id="cm_download_trigger_btn")

        cm_server_btn.click(fn=get_civitai_models_func, inputs=[cm_server_input], outputs=[cm_server_output])
        cm_server_output.change(fn=None, _js="renderCivitaiModelsFromJSON", inputs=[cm_server_output])
        cm_download_btn.click(fn=download_civitai_model_func, inputs=[cm_download_info], outputs=[cm_download_log])
        cm_download_log.change(fn=None, _js="handleConfigSaveLog", inputs=[cm_download_log])

        dl_progress_output = gr.Textbox(visible=False, elem_id="dl_progress_output")
        dl_check_btn = gr.Button(visible=False, elem_id="dl_check_btn")
        dl_check_btn.click(fn=check_download_progress_func, inputs=[], outputs=[dl_progress_output])
        dl_progress_output.change(fn=None, _js="onDownloadProgressUpdate", inputs=[dl_progress_output])

        dl_abort_id_input = gr.Textbox(visible=False, elem_id="dl_abort_id_input")
        dl_abort_btn = gr.Button(visible=False, elem_id="dl_abort_btn")
        dl_abort_btn.click(fn=abort_download_func, inputs=[dl_abort_id_input], outputs=[])

        refresh_js = "prepareCivitaiModelsFetch"
        triggers = [cm_refresh, cm_types, cm_basemodel, cm_sort, cm_period, cm_search, cm_nsfw]
        dummy_inputs = [cm_types]
        for comp in triggers:
            method = comp.submit if comp == cm_search else comp.click if comp == cm_refresh else comp.change
            method(fn=None, _js=refresh_js, inputs=dummy_inputs)
        
        prompt_output_html.change(fn=None, _js="checkPromptGenError", inputs=[prompt_output_html])

        global_config_key = gr.Textbox(visible=False, elem_id="global_config_key_input")
        global_config_value = gr.Textbox(visible=False, elem_id="global_config_value_input")
        global_config_save_btn = gr.Button(visible=False, elem_id="global_config_save_btn")
        
        global_config_save_btn.click(
            fn=save_extension_config_func,
            inputs=[global_config_key, global_config_value],
            outputs=[cm_download_log, prompt_output_html]
        )
    return [(ui, "stylez_menutab", "stylez_menutab")]

script_callbacks.on_ui_tabs(add_tab)