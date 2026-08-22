from dotenv import load_dotenv

load_dotenv()

from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, Response

from controllers.youtube_controllers import (
    videoLoad as youtube_video_load,
    QAWithAi as chat_with_ai,
    analyzeSentiment as analyze_sentiment,
    makeNotes,
    makeNotesStream,
    notesPdf,
)
from controllers import auth_controller, session_controller
from auth.deps import get_current_user
from database.database import ensure_indexes
from models.chatmodel import ChatModel
from models.uploadModel import UploadModel
from models.auth_model import LoginModel, SignupModel
from models.session_model import RenameModel



router = APIRouter(prefix="/youtube")


@router.post("/analyze")
async def analyze_video(upload_model: UploadModel, user: dict = Depends(get_current_user)):
    return await youtube_video_load(
        upload_model.url, upload_model.lang, upload_model.session_id, user
    )


@router.post("/chat")
async def chat_with_ai_route(chat_model: ChatModel, user: dict = Depends(get_current_user)):
    return await chat_with_ai(chat_model.session_id, chat_model.user_query, user)


@router.post("/analyze_sentiment")
async def analyze_sentiment_route(session_id: str, user: dict = Depends(get_current_user)):
    return await analyze_sentiment(session_id, user)


@router.get("/make_notes")
async def make_notes(session_id: str, user: dict = Depends(get_current_user)):
    return await makeNotes(session_id, user)


@router.get("/make_notes/stream")
async def make_notes_stream(session_id: str, user: dict = Depends(get_current_user)):
    generator = await makeNotesStream(session_id, user)
    return StreamingResponse(
        generator,
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/notes/pdf")
async def notes_pdf(session_id: str, user: dict = Depends(get_current_user)):
    pdf_bytes, filename = await notesPdf(session_id, user)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )



auth_router = APIRouter(prefix="/auth")


@auth_router.post("/signup")
async def signup_route(payload: SignupModel):
    return await auth_controller.signup(payload)


@auth_router.post("/login")
async def login_route(payload: LoginModel):
    return await auth_controller.login(payload)


@auth_router.get("/me")
async def me_route(user: dict = Depends(get_current_user)):
    return auth_controller.public_user(user)



session_router = APIRouter(prefix="/sessions")


@session_router.post("")
async def create_session_route(user: dict = Depends(get_current_user)):
    return await session_controller.create(user)


@session_router.get("")
async def list_sessions_route(user: dict = Depends(get_current_user)):
    return await session_controller.list_all(user)


@session_router.get("/{session_id}")
async def get_session_route(session_id: str, user: dict = Depends(get_current_user)):
    return await session_controller.detail(session_id, user)


@session_router.patch("/{session_id}")
async def rename_session_route(
    session_id: str, payload: RenameModel, user: dict = Depends(get_current_user)
):
    return await session_controller.rename(session_id, payload.title, user)


@session_router.delete("/{session_id}")
async def delete_session_route(session_id: str, user: dict = Depends(get_current_user)):
    return await session_controller.remove(session_id, user)



@asynccontextmanager
async def lifespan(app: FastAPI):
   
    ensure_indexes()
    yield


app = FastAPI(title="Tube Analyzer API", lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://tube-sense.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(auth_router)
app.include_router(session_router)



# if __name__ == "__main__":

#     #print(asyncio.run(make_notes()))
#     print(make_notes())



