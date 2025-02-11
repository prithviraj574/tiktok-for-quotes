from fastapi import FastAPI
import uvicorn
from routes.user import router as user_router
from utils.common import init_db, init_quote_data  # plus MODEL_PATH if needed
from utils.model_manager import model, model_lock, load_model
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    global model
    with model_lock:
        model = load_model()  # Load model once at startup
    yield  # Application runs...
    with model_lock:
        model = None  # Optional cleanup

app = FastAPI(lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # FE port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include the user router
app.include_router(user_router)

@app.get("/")
async def root():
    return {"message": "Hello World"}

if __name__ == "__main__":
    # Initialize the database and load quotes into the DB
    init_db()
    init_quote_data()
    uvicorn.run("main:app", reload=True, host="0.0.0.0", port=8000)

