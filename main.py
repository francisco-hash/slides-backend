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
    slides: List[SlideItem]
    access_token: str

@app.post("/generate-slides")
async def generate_slides(req: DeckRequest):
    try:
        creds = Credentials(token=req.access_token)
        drive  = build("drive",  "v3", credentials=creds)
        slides = build("slides", "v1", credentials=creds)

        # Copy template
        new_file = drive.files().copy(
            fileId=req.templateId,
            body={"name": f"{req.title} – {uuid.uuid4().hex[:6]}"}
        ).execute()
        pres_id = new_file["id"]

        return {
            "presentationId": pres_id,
            "presentationUrl": f"https://docs.google.com/presentation/d/{pres_id}/edit"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
