from fastapi import APIRouter, Request, Response, BackgroundTasks
import sqlite3
import torch
from pydantic import BaseModel

from utils.common import (
    get_or_create_user,
    DB_PATH,
    quote_recc_count,
    get_quotes_from_ids,
    get_interacted_quotes,
    interaction_threshold,
    retrain_model_background,
)
from utils.model_manager import model, model_lock, load_model
from utils.model_classes import total_quotes

router = APIRouter()

@router.get("/get_recommendations")
def get_recommendations(request: Request, response: Response):
    user_id = get_or_create_user(request, response)

    # Get quotes the user has interacted with
    interacted_quotes = get_interacted_quotes(user_id)
    interacted_quotes_tensor = (
        torch.tensor(sorted(interacted_quotes), dtype=torch.long)
        if interacted_quotes
        else torch.tensor([])
    )

    # Use the latest model
    global model
    with model_lock:
        if model is None:
            model = load_model()  # Fallback in case model is not loaded

    # Remove interacted quotes from the dataset
    quotes_idx = torch.arange(0, total_quotes, dtype=torch.long)
    if len(interacted_quotes_tensor) > 0:
        mask = ~torch.isin(quotes_idx, interacted_quotes_tensor)
    else:
        mask = torch.ones_like(quotes_idx, dtype=torch.bool)

    # Get recommendations from the model
    recommendations = model.forward(torch.tensor(user_id), quotes_idx[mask])
    _, top_quotes_ids = torch.topk(recommendations, k=quote_recc_count)

    # Fetch recommended quote details
    recommended_quotes = get_quotes_from_ids(top_quotes_ids.tolist())
    # print(user_id)
    # print(recommended_quotes)
    return [{'id':x[0],'text':x[1],'author':x[2]} for x in recommended_quotes]

class InteractionPayload(BaseModel):
    quote_id: int
    is_liked: bool = False

@router.post("/post_interaction")
def post_interaction(
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
    payload: InteractionPayload
):
    """
    Records a user interaction and, if there are at least a threshold
    of untrained interactions, schedules a background task to retrain the model.
    """
    user_id = get_or_create_user(request, response)

    # Insert the interaction into the interactions table.
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO interactions (user_id, quote_id, is_liked)
        VALUES (?, ?, ?)
    """, (user_id, payload.quote_id, payload.is_liked))
    conn.commit()
    conn.close()

    # Check for untrained interactions (was_trained_on = 0).
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id FROM interactions WHERE was_trained_on = 0")
    rows = c.fetchall()
    conn.close()

    # Extract IDs from the query result.
    untrained_ids = [row[0] for row in rows]

    # If we have reached or exceeded the threshold, trigger background retraining.
    if len(untrained_ids) >= interaction_threshold:
        background_tasks.add_task(retrain_model_background, untrained_ids)

    return {"message": "success"}
