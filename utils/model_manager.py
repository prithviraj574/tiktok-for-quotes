import torch
import threading
import os
from utils.model_classes import UserRecommender


# Global model variable and lock
MODEL_PATH = os.path.join(os.getcwd(), "models", "running_prod_model.pth")

model = None
model_lock = threading.Lock()

def load_model():
    global model
    model = UserRecommender()
    model.load_state_dict(torch.load(MODEL_PATH))
    model.eval()
    return model
