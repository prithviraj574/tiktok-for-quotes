# Engaging TikTok-like Quote Feed

This project aims to deliver an engaging, TikTok-inspired feed featuring quotes that capture user interest. By combining state-of-the-art embedding techniques with a Two-Tower collaborative filtering model, the system recommends personalized quotes and adapts to user preferences over time.

---

## Project Structure

- **Data Source**  
  The quotes are a curated subset of the [Kaggle Quotes Dataset](https://www.kaggle.com/datasets/manann/quotes-500k?resource=download). Out of the available 500K quotes, we select 10K to keep the system simple and computationally efficient.

- **Frontend**  
  Contains all the React-based code for the user interface.

- **Pretraining**  
  This folder includes:
  - **Embedding Generation:** Creation of embeddings for quotes and authors.
  - **Interaction Simulation:** Using a large language model (LLM) to simulate user interactions. LLM-generated personas (with Myers-Briggs profiles) provide ratings (1-10) on quote engagement.
  - **Two-Tower Model Training:** Pretraining a Two-Tower model using the generated embeddings.

- **Deployment**  
  Contains FastAPI files for:
  - **Model Serving:** Endpoints to serve the recommendation model.
  - **Interaction Recording:** APIs for recording user feedback (like/dislike).
  - **Database Setup:** Configuration and setup of an SQLite database.
  - **(WIP)** Continuous model retraining to incorporate real-time feedback.

---

## Methodology

1. **Data Selection**  
   We work with a curated subset of 10K quotes from the larger dataset to balance simplicity and computational resource management.

2. **Addressing the Cold Start Problem**  
   To overcome the cold start issue:
   - We simulate user personas using an LLM.
   - The LLM generates structured outputs (using LangChain) that mimic Myers-Briggs personality profiles, rating quotes on a scale from 1 to 10 based on their likelihood to engage.

3. **Embedding Generation**  
   - **Quotes:** BERT is used to create embeddings that capture the semantic meaning of each quote.
   - **Authors:** BERT is also used to generate embeddings from the first two lines of the author's Wikipedia introduction, providing context about the author.

4. **Two-Tower Collaborative Filtering Model**  
   - **Pretraining:**  
     The Two-Tower model is pretrained using the quote and author embeddings.
   - **Model Structure:**  
     - The **quote tower** is frozen after pretraining since further user interactions are not expected to provide significant additional signals.
     - The **user tower** is updated continuously (with real-time retraining being a work in progress) to adapt to evolving user preferences.

5. **Recommendation Engine**  
   The model recommends the top 10 quotes for each user using a Two-Tower collaborative filtering approach. Given the small data size, we bypass the need for a matrix factorization step.

6. **Model Retraining**  
   After every 5 interactions, the model retrains to better capture and adjust to the user’s preferences.

---

## Future Enhancements

- **Real-Time Retraining: (WIP)** Further develop the continuous retraining mechanism for the user tower.
- **Enhanced Personalization:** Integrate additional user signals to refine recommendation quality.

---
