from fastapi import FastAPI, Form
from fastapi.responses import JSONResponse
import win32com.client
import os
import re
import datetime
from pathlib import Path
from PIL import Image
import base64
from io import BytesIO
import subprocess
import requests
import time
import json

from openai import OpenAI
from google.generativeai import configure as configure_gemini, list_models, GenerativeModel

app = FastAPI()

@app.post("/list_models")
async def list_models_endpoint(
    provider: str = Form(...),
    api_key: str = Form(""),
    ollama_url: str = Form("")
):
    try:
        if provider == "openai":
            client = OpenAI(api_key=api_key)
            models = client.models.list()
            model_ids = [m.id for m in models.data]
            return JSONResponse(content={"models": model_ids})

        elif provider == "gemini":
            configure_gemini(api_key=api_key)
            models = list_models()
            model_ids = [m.name for m in models]
            return JSONResponse(content={"models": model_ids})

        elif provider == "ollama":
            ollama_url = ollama_url or "http://localhost:11434"
            if ollama_url.rstrip("/") == "http://localhost:11434":
                try:
                    result = subprocess.run(["ollama", "list"], capture_output=True, text=True, check=True)
                    lines = result.stdout.strip().split("\n")[1:]
                    model_names = [line.split()[0] for line in lines if line]
                    return JSONResponse(content={"models": model_names})
                except Exception as e:
                    return JSONResponse(content={"error": f"Failed to list local Ollama models: {str(e)}"})
            else:
                try:
                    list_url = ollama_url.rstrip("/") + "/api/tags"
                    res = requests.get(list_url, timeout=10)
                    res.raise_for_status()
                    models_info = res.json()
                    model_names = [item["name"] for item in models_info.get("models", [])]
                    return JSONResponse(content={"models": model_names})
                except Exception as e:
                    return JSONResponse(content={"error": f"Failed to list remote Ollama models: {str(e)}"})

        else:
            return JSONResponse(content={"error": "Invalid provider."})

    except Exception as e:
        return JSONResponse(content={"error": str(e)})


@app.post("/generate_slides")
async def generate_slides(
    provider: str = Form(...),
    model: str = Form(...),
    api_key: str = Form(""),
    prompt: str = Form(...),
    num_slides: int = Form(7),
    bg_image_base64: str = Form(""),
    opacity: int = Form(100),
    ollama_url: str = Form(""),
    content_format: str = Form("Bullet Points"),
    detail_level: str = Form("Brief"),
    temperature: float = Form(0.7)  # ✅ NEW PARAMETER
):
    try:
        system_message = (
            f"You are a presentation expert. Please create a presentation content as follows:\n"
            "- Slide 1 should be a title-only slide (no bullets).\n"
            f"- Slide 2 onward should contain content selected by user in {content_format.lower()} format.\n"
            f"- The content should be {detail_level.lower()} and tailored for clear presentations.\n"
            "Format clearly like:\n"
            "1. Title of Slide 1\n"
            "2. Title of Slide 2\n"
            "content based on content formate selected by user"
            "and so on. Do not include any markdown formatting (e.g., **bold** or *italic*), only plain text."
        )
        user_message = f"Topic: {prompt}\nPlease generate a presentation content with exactly {num_slides} slides and {content_format.lower()} as described above.For brief generation, the text should be less than 100 words per slide.For detailed generation, the text should be more than 200 words per slide."

        outline_text = ""

        if provider == "openai":
            client = OpenAI(api_key=api_key)
            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ]
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature  # ✅ ADDED
            )
            outline_text = response.choices[0].message.content

        elif provider == "gemini":
            configure_gemini(api_key=api_key)
            model_instance = GenerativeModel(model)
            content = system_message + "\n" + user_message
            response = model_instance.generate_content(
                content,
                generation_config={"temperature": temperature}  # ✅ ADDED
            )
            outline_text = response.text

        elif provider == "ollama":
            ollama_url_final = ollama_url.rstrip("/") + "/api/generate"
            payload = {
                "model": model,
                "prompt": system_message + "\n" + user_message,
                "stream": True,
                "options": {"temperature": temperature}  # ✅ ADDED
            }

            max_retries = 3
            for attempt in range(max_retries):
                try:
                    with requests.post(ollama_url_final, json=payload, stream=True, timeout=120) as resp:
                        resp.raise_for_status()

                        outline_text = ""
                        for line in resp.iter_lines(decode_unicode=True):
                            if line.strip():
                                try:
                                    data = json.loads(line)
                                    outline_text += data.get("response", "")
                                except json.JSONDecodeError:
                                    continue
                        outline_text = outline_text.strip()
                    break
                except requests.exceptions.RequestException as e:
                    if attempt < max_retries - 1:
                        time.sleep(2)
                    else:
                        return JSONResponse(content={"error": f"Failed to connect to Ollama after {max_retries} attempts: {str(e)}"})

        else:
            return JSONResponse(content={"error": "Unsupported provider selected."})

        slides = parse_outline(outline_text)

        ppt_app = win32com.client.Dispatch("PowerPoint.Application")
        ppt_app.Visible = True
        presentation = ppt_app.Presentations.Add()

        adjusted_bg_path = ""
        if bg_image_base64:
            image_data = base64.b64decode(bg_image_base64)
            pil_image = Image.open(BytesIO(image_data)).convert("RGBA")
            if opacity < 100:
                alpha = pil_image.split()[3]
                alpha = alpha.point(lambda p: int(p * (opacity / 100.0)))
                pil_image.putalpha(alpha)

            adjusted_bg_path = os.path.join(os.getcwd(), f"temp_bg_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            pil_image.save(adjusted_bg_path)

        for i, slide_data in enumerate(slides):
            title = slide_data["title"]
            bullets = slide_data["bullets"]

            if i == 0:
                slide = presentation.Slides.Add(presentation.Slides.Count + 1, 1)
            else:
                slide = presentation.Slides.Add(presentation.Slides.Count + 1, 2)

            if adjusted_bg_path and os.path.exists(adjusted_bg_path):
                slide.FollowMasterBackground = False
                fill = slide.Background.Fill
                fill.UserPicture(adjusted_bg_path)

            title_shape = slide.Shapes.Title
            title_range = title_shape.TextFrame.TextRange
            title_range.Text = title
            title_range.Font.Bold = False
            title_range.Font.Name = "Arial"

            if i != 0:
                content_shape = slide.Shapes.Placeholders(2)
                content_range = content_shape.TextFrame.TextRange
                content_range.Text = "\n".join(bullets)
                content_range.Font.Bold = False
                content_range.Font.Name = "Arial"

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        save_filename = f"generated_presentation_{timestamp}.pptx"
        downloads_path = str(Path.home() / "Downloads")
        save_path = os.path.join(downloads_path, save_filename)

        presentation.SaveAs(save_path)

        if adjusted_bg_path and os.path.exists(adjusted_bg_path):
            os.remove(adjusted_bg_path)

        return JSONResponse(content={"message": f"Presentation created in Downloads folder: {save_path}"})

    except Exception as e:
        return JSONResponse(content={"error": str(e)})

def parse_outline(outline_text):
    slides = []
    slide_matches = re.findall(r'(\d+\..*?)(?=(\n\d+\.|\Z))', outline_text, re.S)

    for match in slide_matches:
        block = match[0]
        lines = block.strip().split("\n")
        if not lines:
            continue

        title_line = lines[0].strip()
        title_line = re.sub(r"^\d+\.\s*", "", title_line).strip()
        # Updated line below to handle *, -, • and spaces
        bullets = [line.lstrip("-•* ").strip() for line in lines[1:] if line.strip()]
        slides.append({"title": title_line, "bullets": bullets})

    return slides
