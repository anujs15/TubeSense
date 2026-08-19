from dotenv import load_dotenv

load_dotenv()

from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse

from controllers.youtube_controllers import (
    videoLoad as youtube_video_load,
    QAWithAi as chat_with_ai,
    analyzeSentiment as analyze_sentiment,
    makeNotes,
    makeNotesStream,
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


@router.get("/make_notes/stream")
async def make_notes_stream():
    
    generator = await makeNotesStream()
    return StreamingResponse(
        generator,
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  
        },
    )


app = FastAPI(title="Tube Analyzer API")



app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


_images_dir = Path(__file__).resolve().parent / "images"
_images_dir.mkdir(exist_ok=True)
app.mount("/images", StaticFiles(directory=str(_images_dir)), name="images")



# if __name__ == "__main__":

#     #print(asyncio.run(make_notes()))
#     print(make_notes())



#https://www.youtube.com/watch?v=Wr1JjhTt1Xg