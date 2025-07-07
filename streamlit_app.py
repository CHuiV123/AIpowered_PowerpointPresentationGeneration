import streamlit as st
import requests
import base64
import docx
import PyPDF2

st.set_page_config(
    page_title="SHRDC MSF GENAI PowerPoint Generator",
    page_icon="📝",
    layout="centered",
    initial_sidebar_state="expanded"
)

# Sidebar options
with st.sidebar:
    st.title("Options")
    use_bullets = st.selectbox("Slide content style", ["Bullet points", "Paragraph"])
    detail_level = st.selectbox("Detail level", ["Brief", "Detailed"])
    temperature = st.slider("Creativity (temperature)", 0.1, 1.0, 0.7, 0.1)

st.title("🤖💡 AI PowerPoint Slide Generator")

provider = st.selectbox("Select Provider", ["openai", "gemini", "ollama"])

api_key = ""
ollama_url = ""
models = []

if provider != "ollama":
    api_key = st.text_input("API Key", type="password")
else:
    ollama_url = st.text_input("Ollama URL", value="http://localhost:11434")

# Load models
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

# --- New option for content source ---
content_source = st.radio("Choose how to provide content", ["Write Topic or Description", "Upload Document"])

uploaded_text = ""
user_instruction = ""
prompt = ""

if content_source == "Write Topic or Description":
    prompt = st.text_area("Presentation Topic or Description", height=150)
else:
    uploaded_file = st.file_uploader("Upload document", type=["txt", "pdf", "docx"])
    if uploaded_file is not None:
        file_type = uploaded_file.type

        # Read TXT
        if uploaded_file.name.endswith(".txt"):
            uploaded_text = uploaded_file.read().decode("utf-8")
        
        # Read PDF
        elif uploaded_file.name.endswith(".pdf"):
            pdf_reader = PyPDF2.PdfReader(uploaded_file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() or ""
            uploaded_text = text
        
        # Read DOCX
        elif uploaded_file.name.endswith(".docx"):
            doc = docx.Document(uploaded_file)
            text = "\n".join([para.text for para in doc.paragraphs])
            uploaded_text = text

    user_instruction = st.text_area("Instruction on how to generate slides from document", height=120)

num_slides = st.slider("Number of slides", min_value=3, max_value=20, value=7)

bg_image_file = st.file_uploader("Upload background image (optional)", type=["jpg", "png"])
opacity = st.slider("Background image opacity (%)", min_value=10, max_value=100, value=15)

if st.button("Generate Presentation"):
    if not model:
        st.error("Please select a model.")
    else:
        bg_image_base64 = ""
        if bg_image_file:
            bg_image_base64 = base64.b64encode(bg_image_file.read()).decode("utf-8")

        use_uploaded_doc = "true" if content_source == "Upload Document" and uploaded_text.strip() else "false"

        data = {
            "provider": provider,
            "model": model,
            "api_key": api_key,
            "prompt": prompt,
            "num_slides": num_slides,
            "bg_image_base64": bg_image_base64,
            "opacity": opacity,
            "ollama_url": ollama_url,
            "content_format": use_bullets,
            "detail_level": detail_level,
            "temperature": temperature,
            "use_uploaded_doc": use_uploaded_doc,
            "uploaded_text": uploaded_text,
            "user_instruction": user_instruction,
        }

        with st.spinner("Generating presentation..."):
            try:
                response = requests.post("http://127.0.0.1:8080/generate_slides", data=data, timeout=300)
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
    st.image("static/shrdc.jpg", width=200, caption="Selangor Human Resource Development Centre")

with col3:
    col4, col5 = st.columns(2)
    with col4:
        st.image("static/msf.jpg", caption="Malaysian Smart Factory")
    with col5:
        st.image("static/genai.jpg", caption="Generative AI Innovation Hub")
