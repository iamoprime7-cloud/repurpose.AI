import os
import time
import json
import streamlit as st
import yt_dlp
import pandas as pd
import re
from google import genai
from huggingface_hub import InferenceClient

def extract_json(text):
    """
    Finds the first valid JSON object in a string and returns it.
    """
    try:
        # Regex to find everything between the first { and the last }
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return match.group(0)
        return text # Return original if no brackets found
    except:
        return text

# --- 1. SETUP & KEYS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GOOGLE_API_KEY = "AIzaSyASTY6GxK3ub16GQZynprie8fkdctOuTho"
HF_API_KEY = "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"

# AI Clients
# Timeout set to 0.0 to allow long audio processing without interruption
client = genai.Client(
    api_key=GOOGLE_API_KEY, 
    http_options={'timeout': 0.0} 
)
hf_client = InferenceClient(api_key=HF_API_KEY)

# --- 2. UI CONFIGURATION ---
st.set_page_config(page_title="Repurpose Pro Studio", page_icon="🚀", layout="wide")

with st.sidebar:
    st.title("Studio Settings")
    st.info("Configure your brand voice and target platforms below.")
    
    brand_voice = st.selectbox(
        "Brand Voice:", 
        ["Professional & Authority", "Witty & Relatable", "Aggressive & Bold", "Educational & Deep"]
    )
    
    target_platforms = st.multiselect(
        "Target Platforms:",
        ["LinkedIn", "Twitter (X)", "Instagram", "Threads"],
        default=["LinkedIn", "Twitter (X)"]
    )
    
    st.divider()
    st.header("Style Reference")
    style_sample = st.text_area(
        "Paste a sample of your writing style:",
        placeholder="Copy/paste a previous post here so the AI learns your voice.",
        help="The AI will analyze the sentence structure and tone of this text."
    )
    
    st.divider()
    st.caption("Repurpose Pro v2.5 | Gemini 2.5 Native")

# --- 3. CORE ENGINES ---
def download_audio(url):
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
        'outtmpl': os.path.join(BASE_DIR, 'temp_audio.%(ext)s'),
        'ffmpeg_location': BASE_DIR,
        'prefer_ffmpeg': True,
        'nocheckcertificate': True,
        'quiet': True
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    return os.path.join(BASE_DIR, "temp_audio.mp3")

def generate_image(prompt_text):
    try:
        # Using the SDXL model via the HF Router
        image = hf_client.text_to_image(
            prompt=f"{prompt_text}, professional digital art, high resolution",
            model="stabilityai/stable-diffusion-xl-base-1.0"
        )
        path = os.path.join(BASE_DIR, "temp_visual.png")
        image.save(path)
        return path
    except Exception as e:
        st.error(f"Image Error: {e}")
        return None

# --- 4. MAIN INTERFACE ---
st.title("🚀 Repurpose Pro: Batch Content Studio")
st.write(f"Generating **{brand_voice}** content for: {', '.join(target_platforms)}")

# Batch Input
urls_input = st.text_area("Paste YouTube Links (one per line):", height=150, placeholder="https://youtube.com/watch?v=...")
urls = [u.strip() for u in urls_input.split('\n') if u.strip()]

if st.button("Generate Full Studio Package"):
    if not urls:
        st.warning("Please enter at least one URL.")
    else:
        batch_data = []
        results_area = st.container()
        
        for idx, url in enumerate(urls):
            with st.spinner(f"video {idx+1} of {len(urls)}..."):
                status = st.status(f"Processing video {idx+1}...")
                
                try:
                    
                    audio_path = download_audio(url)
                    
                    
                    with open(audio_path, "rb") as f:
                        file_upload = client.files.upload(
                            file=f, 
                            config={'mime_type': 'audio/mpeg'}
                        )
                    
                    while file_upload.state.name == "PROCESSING":
                        time.sleep(3)
                        file_upload = client.files.get(name=file_upload.name)
                    
                    # 3. Content Prompting
                    current_style = style_sample if style_sample else "Generic professional social media style"
                    
                    # Variable 'prompt' is now explicitly defined here
                    prompt = f"""
                    Act as a Senior Content Strategist and Expert Copywriter. 
                    Your task is to transform the attached audio into a high-value content engine for a {brand_voice} brand.

                    CRITICAL STYLE INSTRUCTION:
                    Mimic the formatting, sentence length, and 'vibe' of this sample:
                    --- STYLE SAMPLE ---
                    {style_sample if style_sample else "Professional, insightful, and engaging social media storytelling."}
                    --------------------

                    Generate a JSON object with the following keys:
                    1. "LinkedIn": Create a 'Deep Dive' post (approx 400-600 words). Include a 'pattern-interrupt' hook, a detailed breakdown of the 3 most important lessons from the audio, and a thought-provoking 'Question of the Day' call-to-action.
                    2. "Twitter (X)": Create a 5-tweet high-value thread. Tweet 1: Hook + Promise. Tweets 2-4: The 'Meat' of the audio. Tweet 5: Summary + CTA.
                    3. "Instagram": A punchy, value-driven caption with 10 relevant hashtags.
                    4. "visual_prompt": A hyper-realistic, 8k resolution artistic description for an image generator that captures the emotional core of the audio.

                    TECHNICAL RULES:
                    - Use Markdown (bolding, bullet points, headers) within the text values.
                    - Elaborate on the 'WHY' behind the concepts mentioned in the audio.
                    - Ensure the summary is comprehensive but the individual posts are expanded.
                    - Return ONLY the raw JSON object.
                    """
                    
                    # Using Gemini 2.5 Flash as requested
                    response = client.models.generate_content(
                        model="gemini-2.5-flash", 
                        contents=[file_upload, prompt]
                    )
                    
                    # Clean and Parse JSON
                    clean_json = response.text.replace("```json", "").replace("```", "").strip()
                    try:
                        # 1. Strip Markdown
                        raw_text = response.text.replace("```json", "").replace("```", "").strip()
                        
                        # 2. Extract only the JSON part (removes extra text)
                        json_str = extract_json(raw_text)
                        
                        # 3. Load it
                        data = json.loads(json_str)
                        
                    except json.JSONDecodeError as e:
                        # Fallback: If JSON fails, create a dummy object so the app doesn't crash
                        st.error(f"AI JSON Error: {e}")
                        data = {
                            "LinkedIn": response.text, # Show raw text so you don't lose it
                            "Twitter (X)": "Error parsing JSON.",
                            "visual_prompt": "Abstract digital art"
                        }

                    batch_data.append({
                        "Video URL": url,
                        "LinkedIn Post": data.get("LinkedIn", "N/A"),
                        "Twitter Thread": data.get("Twitter (X)", "N/A"),
                        "Instagram": data.get("Instagram", "N/A"),
                        "Visual Prompt": data.get("visual_prompt", "N/A")
                    })
                    
                    # 4. Image Generation
                    image_path = generate_image(data.get("visual_prompt", ""))

                    # 5. Display Results
                    with results_area:
                        st.divider()
                        st.subheader(f"🎬 Video {idx+1} Content Package")
                        
                        tab_names = target_platforms + ["🎨 Branded Visual"]
                        tabs = st.tabs(tab_names)
                        
                        for i, platform in enumerate(target_platforms):
                            with tabs[i]:
                                text_content = data.get(platform, "Content missing.")
                                st.write(text_content)
                                st.button(f"Copy {platform}", key=f"btn_{idx}_{i}")
                        
                        with tabs[-1]:
                            if image_path:
                                st.image(image_path, use_container_width=True)
                            else:
                                st.warning("Visual asset generation failed.")
                    
                    status.update(label=f"✅ Video {idx+1} Completed!", state="complete")
                    
                    # Cleanup
                    if os.path.exists(audio_path): os.remove(audio_path)
                    
                except Exception as e:
                    st.error(f"Error on video {idx+1}: {e}")

        # --- 5. BATCH EXPORT ---
        if batch_data:
            df = pd.DataFrame(batch_data)
            csv = df.to_csv(index=False).encode('utf-8')
            
            st.success("🎉 All videos processed successfully!")
            st.download_button(
                label="📥 Download Batch as CSV",
                data=csv,
                file_name="repurpose_pro_export.csv",
                mime="text/csv",
                type="primary"
            )
        