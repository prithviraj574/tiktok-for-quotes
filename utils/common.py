import sqlite3
import os
import pandas as pd
from fastapi import Request, Response
from datetime import datetime, timedelta
from utils.model_manager import load_model, model, model_lock, MODEL_PATH
import torch
import copy

quote_recc_count = 10
interaction_threshold = 5


DB_PATH = os.path.join(os.getcwd(), "app.db")  # Single database file

# Initialize SQLite database
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Users Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            cookie_id TEXT UNIQUE
        )
    ''')    
    # Set the initial sequence value to start from 16
    c.execute("INSERT OR IGNORE INTO SQLITE_SEQUENCE (name, seq) VALUES ('users', 15)")
    # Interactions Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS interactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            quote_id INTEGER,
            is_liked BOOLEAN,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            was_trained_on BOOLEAN DEFAULT FALSE,
            FOREIGN KEY(user_id) REFERENCES users(user_id),
            FOREIGN KEY(quote_id) REFERENCES quotes(id)
        )
    ''')
    # Quotes Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS quotes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            quote TEXT,
            author TEXT
        )
    ''')
    conn.commit()
    conn.close()


# Check if user cookie exists
def check_user_cookie(cookie_id: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT user_id FROM users WHERE cookie_id = ?', (cookie_id,))
    result = c.fetchone()
    conn.close()
    return result is not None


# Get or create user
def get_or_create_user(request: Request, response: Response) -> int:
    cookie_id = request.cookies.get("user_cookie")    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if cookie_id and check_user_cookie(cookie_id):
        c.execute('SELECT user_id FROM users WHERE cookie_id = ?', (cookie_id,))
        user_id = c.fetchone()[0]
        conn.close()
        return user_id
    # Create new user if cookie doesn't exist
    c.execute('INSERT INTO users (cookie_id) VALUES (?)', (None,))
    new_user_id = c.lastrowid
    new_cookie_id = f"user_{new_user_id}"
    c.execute('UPDATE users SET cookie_id = ? WHERE user_id = ?', (new_cookie_id, new_user_id))
    conn.commit()
    conn.close()
    response.set_cookie(key="user_cookie", value=new_cookie_id, httponly=True)
    return new_user_id


# Initialize quote data
def init_quote_data():
    conn = sqlite3.connect(DB_PATH)
    quote_data = pd.read_csv(os.path.join(os.getcwd(), "data", "sampled_quotes.csv"))
    quote_data.drop(columns=["Unnamed: 0"], inplace=True)
    
    quote_data = quote_data[["quote", "author"]].reset_index()
    quote_data.rename(columns={"index": "id"}, inplace=True)
    
    quote_data.to_sql("quotes", conn, if_exists="replace", index=False) 
    conn.commit()
    conn.close()


def get_quotes_from_ids(ids):
    """ Fetch quotes by their IDs from the database. """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Dynamically generate correct SQL query for multiple values
    query = f"SELECT id, quote, author FROM quotes WHERE id IN ({','.join('?' * len(ids))})"
    c.execute(query, ids)

    result = c.fetchall()
    conn.close()
    return result



def get_interacted_quotes(user_id):
    """ Get quotes the user interacted with in the last 10 days. """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    ten_days_ago = datetime.now() - timedelta(days=10)
    c.execute("SELECT DISTINCT quote_id FROM interactions WHERE user_id = ? AND timestamp > ?", (user_id, ten_days_ago))
    
    result = [row[0] for row in c.fetchall()]  # Extract quote IDs
    conn.close()
    return result

# WORK IN-Progress
def train_new_model(interaction_data):
    global model
    with model_lock:
        if model is None:
            model = load_model()  # Fallback in case model is not loaded
    new_model = copy.deepcopy(model)
    return new_model


def retrain_model_background(interaction_ids):
    """
    Background task to retrain the model using interactions that haven't been
    trained on yet. This function:
      1. Loads the interaction data from the DB.
      2. Trains a new model.
      3. Saves the new model to disk.
      4. Updates the global model in memory.
      5. Marks these interactions as trained.
    """
    # print(f"Retraining model using interaction IDs: {interaction_ids}")

    # 1. Get interaction data (if needed for training)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    query = f"SELECT user_id, quote_id, is_liked, timestamp FROM interactions WHERE id IN ({','.join('?' for _ in interaction_ids)})"
    c.execute(query, interaction_ids)
    interaction_data = c.fetchall()
    conn.close()

    # 2. Train a new model based on the interaction data.
    new_model = train_new_model(interaction_data)
    # global model
    # new_model = model

    # 3. Save the new model to disk.
    torch.save(new_model.state_dict(), MODEL_PATH)

    # 4. Safely update the in-memory model.
    global model
    with model_lock:
        if model is None:
            model = load_model()  # Fallback in case model is not loaded
 
    # 5. Mark these interactions as trained.
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    query_update = f"UPDATE interactions SET was_trained_on = 1 WHERE id IN ({','.join('?' for _ in interaction_ids)})"
    c.execute(query_update, interaction_ids)
    conn.commit()
    conn.close()

    # print("Model retraining complete and interactions updated.")

