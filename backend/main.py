import os
import random
import spacy
import nltk
from transformers import pipeline
from openai import OpenAI
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict

# Initialize FastAPI
app = FastAPI(title="AI Quiz Generator API")

# Download necessary NLP resources
nltk.download('punkt')
nltk.download('stopwords')

# Load NLP models
try:
    nlp = spacy.load("en_core_web_md")
except OSError:
    raise RuntimeError("Spacy model 'en_core_web_md' is not installed. Run: python -m spacy download en_core_web_md")

summarizer = pipeline("summarization")

# Configure OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("Missing OpenAI API Key. Set 'OPENAI_API_KEY' in your environment variables.")

client = OpenAI(api_key=OPENAI_API_KEY)

# Models
class TextInput(BaseModel):
    content: str
    num_questions: int = 5
    difficulty: str = "medium"

class Question(BaseModel):
    question_text: str
    options: List[str]
    correct_answer: int
    explanation: str
    difficulty: str
    topic: str

class Quiz(BaseModel):
    title: str
    questions: List[Question]
    source_text_summary: str

# Preprocess text
def preprocess_text(text: str) -> str:
    return " ".join(text.split())

# Extract named entities
def extract_entities(text: str) -> Dict:
    doc = nlp(text)
    entities = {}
    for ent in doc.ents:
        entities.setdefault(ent.label_, []).append(ent.text)
    return entities

# Extract key concepts
def extract_key_concepts(text: str, max_concepts: int = 10) -> List[str]:
    doc = nlp(text)
    concepts = list(set(chunk.text for chunk in doc.noun_chunks))
    return concepts[:max_concepts]

# Summarize text
def summarize_text(text: str, max_length: int = 150) -> str:
    if len(text.split()) > 100:
        summary = summarizer(text, max_length=max_length, min_length=30, do_sample=False)
        return summary[0]['summary_text']
    return text

# Generate questions
def generate_questions(text: str, entities: Dict, concepts: List[str], num_questions: int, difficulty: str) -> List[Question]:
    summary = summarize_text(text)
    questions = []
    topics = list(entities.keys()) + ["General Understanding"]
    
    for _ in range(num_questions):
        topic = random.choice(topics)
        context = summary if topic == "General Understanding" else ", ".join(entities.get(topic, concepts))
        prompt = f"""
        Generate a multiple-choice question based on this context:
        Context: {context}
        Difficulty: {difficulty}
        Format:
        Question: [question text]
        A. [option1]
        B. [option2]
        C. [option3]
        D. [option4]
        Correct Answer: [A, B, C, or D]
        Explanation: [explanation]
        """
        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}]
            )
            gpt_response = response.choices[0].message.content.strip()
            question = parse_gpt_question(gpt_response, topic, difficulty)
            if question:
                questions.append(question)
        except Exception as e:
            print(f"Error generating question: {e}")
    return questions

# Parse GPT-generated question
def parse_gpt_question(response: str, topic: str, difficulty: str) -> Question:
    try:
        lines = response.split("\n")
        question_text, options, correct_answer, explanation = "", [], -1, ""
        answer_map = {"A": 0, "B": 1, "C": 2, "D": 3}
        
        for line in lines:
            if line.startswith("Question:"):
                question_text = line[9:].strip()
            elif line.startswith(("A.", "B.", "C.", "D.")):
                options.append(line[2:].strip())
            elif line.startswith("Correct Answer:"):
                correct_answer = answer_map.get(line[15:].strip(), -1)
            elif line.startswith("Explanation:"):
                explanation = line[12:].strip()
                
        if question_text and len(options) == 4 and correct_answer >= 0:
            return Question(
                question_text=question_text,
                options=options,
                correct_answer=correct_answer,
                explanation=explanation,
                difficulty=difficulty,
                topic=topic
            )
    except Exception as e:
        print(f"Error parsing question: {e}")
    return None

# API Endpoint
@app.post("/generate-quiz/", response_model=Quiz)
async def generate_quiz(input_data: TextInput):
    try:
        processed_text = preprocess_text(input_data.content)
        entities = extract_entities(processed_text)
        concepts = extract_key_concepts(processed_text)
        questions = generate_questions(processed_text, entities, concepts, input_data.num_questions, input_data.difficulty)
        
        title_prompt = f"Generate a short quiz title for: {summarize_text(processed_text, 100)}"
        title_response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": title_prompt}],
            max_tokens=30,
            temperature=0.7
        )
        title = title_response.choices[0].message.content.strip()
        
        return Quiz(title=title, questions=questions, source_text_summary=summarize_text(processed_text))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
