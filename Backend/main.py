from dotenv import load_dotenv

load_dotenv()

from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from controllers.youtube_controllers import (
    videoLoad as youtube_video_load,
    QAWithAi as chat_with_ai,
    analyzeSentiment as analyze_sentiment,
    makeNotes,
)
from models.chatmodel import ChatModel
from models.uploadModel import UploadModel


router = APIRouter(prefix="/youtube")


@router.post("/analyze")
async def analyze_video(upload_model: UploadModel):

    return await youtube_video_load(upload_model.url, upload_model.lang)

@router.post("/chat")
async def chat_with_ai_route(chat_model: ChatModel):

    return await chat_with_ai(chat_model.user_query)

@router.post("/analyze_sentiment")
async def analyze_sentiment_route():
    return await analyze_sentiment()

@router.get("/make_notes")
async def make_notes():

    return  await makeNotes()


app = FastAPI(title="Tube Analyzer API")

# NOTE: allow_origins=["*"] is permissive for local development.
# Restrict this to your frontend's origin(s) before deploying.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

# The notes writer saves generated images under ./images (see
# utils/note_decideImage.py) and references them in markdown as
# `images/<file>.png`. Serve that directory so the frontend can render them.
_images_dir = Path(__file__).resolve().parent / "images"
_images_dir.mkdir(exist_ok=True)
app.mount("/images", StaticFiles(directory=str(_images_dir)), name="images")



# if __name__ == "__main__":

#     #print(asyncio.run(make_notes()))
#     print(make_notes())



#https://www.youtube.com/watch?v=Wr1JjhTt1Xg