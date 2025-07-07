import streamlit as st
import requests
import base64

st.set_page_config(page_title="SHRDC MSF GENAI PowerPoint Generator", page_icon="📝", layout="centered",initial_sidebar_state="collapsed")
# with st.sidebar:
#     st.subheader("**:blue[Selangor Human Resource Development Centre]**")
#     st.markdown("   ")
#     col1, col2 = st.columns(2)
#     with col1: 
#         st.image("static/shrdc.jpg")
#     with col2: 
#         st.image("static/msf.jpg", caption="Malaysian Smart Factory")     
#     st.image("static/genai.jpg",caption="Generative AI Hub", width=3)
#     st.markdown("---")
#     st.markdown("### About")
#     st.markdown("Create amazing slides powered by AI ✨")
#     st.write("Version: 2.0")
#     st.write("Made with ❤️ by Hui Voon")
#     st.markdown("[Visit my website](https://github.com/CHuiV123?tab=repositories)")
    

st.title("🤖💡 AI PowerPoint Slide Generator")

provider = st.selectbox("Select Provider", ["openai", "gemini", "ollama"])

api_key = ""
ollama_url = ""
models = []

if provider != "ollama":
    api_key = st.text_input("API Key", type="password")
else:
    ollama_url = st.text_input("Ollama URL", value="http://localhost:11434")

# Auto-fetch models immediately when provider or url changes
if provider == "ollama":
    if ollama_url:
        with st.spinner("Loading Ollama models..."):
            try:
                response = requests.post(
                    "http://127.0.0.1:8080/list_models",
                    data={"provider": provider, "api_key": "", "ollama_url": ollama_url},
                    timeout=15,
                )
                if response.status_code == 200:
                    models = response.json().get("models", [])
                else:
                    st.error(f"Error loading models: {response.text}")
            except Exception as e:
                st.error(f"Failed to connect to Ollama server: {str(e)}")
elif api_key:
    with st.spinner("Loading models..."):
        try:
            response = requests.post(
                "http://127.0.0.1:8080/list_models",
                data={"provider": provider, "api_key": api_key},
                timeout=15,
            )
            if response.status_code == 200:
                models = response.json().get("models", [])
            else:
                st.error(f"Error loading models: {response.text}")
        except Exception as e:
            st.error(f"Failed to connect: {str(e)}")

model = st.selectbox("Select Model", models)

prompt = st.text_area("Presentation Topic or Description", height=150)
num_slides = st.slider("Number of slides", min_value=3, max_value=20, value=7)

bg_image_file = st.file_uploader("Upload background image (optional)", type=["jpg", "png"])
opacity = st.slider("Background image opacity (%)", min_value=10, max_value=100, value=100)

if st.button("Generate Presentation"):
    if not model or not prompt:
        st.error("Please provide both model and prompt.")
    else:
        bg_image_base64 = ""
        if bg_image_file:
            bg_image_base64 = base64.b64encode(bg_image_file.read()).decode("utf-8")

        data = {
            "provider": provider,
            "model": model,
            "api_key": api_key,
            "prompt": prompt,
            "num_slides": num_slides,
            "bg_image_base64": bg_image_base64,
            "opacity": opacity,
            "ollama_url": ollama_url,
        }

        with st.spinner("Generating presentation..."):
            try:
                response = requests.post("http://127.0.0.1:8080/generate_slides", data=data, timeout=120)
                if response.status_code == 200:
                    resp_json = response.json()
                    if "message" in resp_json:
                        st.success(resp_json["message"])
                    else:
                        st.error("Error: No message in response.")
                else:
                    st.error(f"Error: {response.text}")
            except Exception as e:
                st.error(f"Failed to generate presentation: {str(e)}")

st.markdown("---")
col1, col2, col3 = st.columns(3)
with col1: 
    st.markdown("### About")
    st.markdown("Create amazing slides powered by AI ✨   Version: 2.0")
    st.write("Made with ❤️ by Hui Voon")
    
with col2:
    st.image("static/shrdc.jpg", width=200, caption= "Selangor Human Resource Development Centre")
    
with col3: 
    col4,col5 = st.columns(2)
    with col4: 
        st.image("static/msf.jpg", caption="Malaysian Smart Factory") 
    with col5: 
        st.image("static/genai.jpg",caption="Generative AI Innovation Hub") 