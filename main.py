from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import uuid

app = FastAPI()

class SlideItem(BaseModel):
    slideNumber: int
    titulo: str
    texto: str
    visualSugerido: str | None = None

class DeckRequest(BaseModel):
    templateId: str
    title: str
    access_token: str
    slides: List[SlideItem]

@app.post("/generate-slides")
async def generate_slides(req: DeckRequest):
    try:
        creds = Credentials(token=req.access_token)
        drive = build("drive", "v3", credentials=creds)
        slides = build("slides", "v1", credentials=creds)

        # 1. Copy the template
        new_file = drive.files().copy(
            fileId=req.templateId,
            body={"name": f"{req.title} – {uuid.uuid4().hex[:6]}"}
        ).execute()

        pres_id = new_file["id"]

        # 2. Make it publicly accessible
        drive.permissions().create(
            fileId=pres_id,
            body={
                "type": "anyone",
                "role": "writer"
            },
            supportsAllDrives=True
        ).execute()

        # 3. Build all slide + text requests
        requests = []
        for index, slide in enumerate(req.slides):
            slide_id = f"slide_{index + 1}"
            title_box_id = f"title_{index + 1}"
            text_box_id = f"text_{index + 1}"

            requests.append({
                "createSlide": {
                    "objectId": slide_id,
                    "insertionIndex": "1",
                    "slideLayoutReference": {
                        "predefinedLayout": "BLANK"
                    }
                }
            })

            # Create title box
            requests.append({
                "createShape": {
                    "objectId": title_box_id,
                    "shapeType": "TEXT_BOX",
                    "elementProperties": {
                        "pageObjectId": slide_id,
                        "size": {
                            "height": {"magnitude": 50, "unit": "PT"},
                            "width": {"magnitude": 500, "unit": "PT"}
                        },
                        "transform": {
                            "scaleX": 1,
                            "scaleY": 1,
                            "translateX": 50,
                            "translateY": 50,
                            "unit": "PT"
                        }
                    }
                }
            })
            requests.append({
                "insertText": {
                    "objectId": title_box_id,
                    "text": slide.titulo
                }
            })

            # Create body text box
            requests.append({
                "createShape": {
                    "objectId": text_box_id,
                    "shapeType": "TEXT_BOX",
                    "elementProperties": {
                        "pageObjectId": slide_id,
                        "size": {
                            "height": {"magnitude": 200, "unit": "PT"},
                            "width": {"magnitude": 500, "unit": "PT"}
                        },
                        "transform": {
                            "scaleX": 1,
                            "scaleY": 1,
                            "translateX": 50,
                            "translateY": 120,
                            "unit": "PT"
                        }
                    }
                }
            })
            requests.append({
                "insertText": {
                    "objectId": text_box_id,
                    "text": slide.texto
                }
            })

        # 4. Send batch requests
        slides.presentations().batchUpdate(
            presentationId=pres_id,
            body={"requests": requests}
        ).execute()

        # 5. Get the correct viewable URL from Google Drive
        file_meta = drive.files().get(fileId=pres_id, fields="id, webViewLink").execute()

        return {
            "presentationId": pres_id,
            "presentationUrl": file_meta.get("webViewLink")
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
