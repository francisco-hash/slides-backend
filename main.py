from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from typing import Optional
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import uuid

# ID de plantilla predeterminada de Google Slides
DEFAULT_TEMPLATE_ID = "1Kl6swruSuhq9KCPMMI7F2eVoDe0NxxeMfUTgpQArpqY"

app = FastAPI()

class SlideItem(BaseModel):
    slideNumber: int
    titulo: str
    texto: str
    visualSugerido: str | None = None

class DeckRequest(BaseModel):
    templateId: Optional[str] = None
    title: str
    access_token: str
    slides: List[SlideItem]

@app.post("/generate-slides")
async def generate_slides(req: DeckRequest):
    try:
        creds = Credentials(token=req.access_token)
        drive  = build("drive",  "v3", credentials=creds)
        slides = build("slides", "v1", credentials=creds)

        # 1. Copy the template
        template_id = req.templateId or DEFAULT_TEMPLATE_ID
        new_file = drive.files().copy(
            fileId=template_id,
            body={"name": f"{req.title} – {uuid.uuid4().hex[:6]}"}
        ).execute()
        pres_id = new_file["id"]

        # ✅ 2. Make the file accessible to anyone with the link
        drive.permissions().create(
            fileId=pres_id,
            body={
                "type": "anyone",
                "role": "writer"
            }
        ).execute()

        # 3. Build the slides content (optional: leave as title-only for now)
        requests = []
        for slide in req.slides:
            requests.append({
                "createSlide": {
                    "insertionIndex": "1",
                    "slideLayoutReference": {
                        "predefinedLayout": "TITLE_AND_BODY"
                    }
                }
            })
            # Optional: Insert title and text logic (needs object IDs if implemented)

        # 4. Apply batch requests to the presentation
        if requests:
            slides.presentations().batchUpdate(
                presentationId=pres_id,
                body={"requests": requests}
            ).execute()

        # 5. Return the link
        return {
            "presentationId": pres_id,
            "presentationUrl": f"https://docs.google.com/presentation/d/{pres_id}/edit"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
