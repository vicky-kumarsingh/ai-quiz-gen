# app.py - Streamlit frontend
# !pip install matplotlib
import streamlit as st
import requests
import json
import pandas as pd
# import matplotlib.pyplot as plt
from io import BytesIO
import base64

# Configuration
API_URL = "http://localhost:8000"  # FastAPI backend URL

st.set_page_config(
    page_title="AI Quiz Generator",
    page_icon="❓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better UI
st.markdown("""
<style>
    .main {
        background-color: #f5f7f9;
    }
    .stTextInput > div > div > input {
        padding: 12px;
        font-size: 16px;
    }
    .quiz-question {
        background-color: white;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .option {
        padding: 10px;
        border-radius: 5px;
        margin: 5px 0;
        cursor: pointer;
        transition: background-color 0.3s;
    }
    .option:hover {
        background-color: #f0f0f0;
    }
    .correct {
        background-color: #d4edda;
        border-color: #c3e6cb;
    }
    .incorrect {
        background-color: #f8d7da;
        border-color: #f5c6cb;
    }
    .explanation {
        background-color: #e9ecef;
        padding: 15px;
        border-radius: 5px;
        margin-top: 10px;
    }
    .title {
        text-align: center;
        font-family: 'Arial', sans-serif;
        margin-bottom: 30px;
    }
</style>
""", unsafe_allow_html=True)

# Session state for quiz data
if 'quiz' not in st.session_state:
    st.session_state.quiz = None
if 'current_question' not in st.session_state:
    st.session_state.current_question = 0
if 'answers' not in st.session_state:
    st.session_state.answers = []
if 'quiz_completed' not in st.session_state:
    st.session_state.quiz_completed = False
if 'show_explanation' not in st.session_state:
    st.session_state.show_explanation = False

# Sidebar for input and configuration
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/quiz.png", width=100)
    st.title("AI Quiz Generator")
    st.markdown("Generate custom quizzes from any text with AI")
    
    input_method = st.radio(
        "Choose input method",
        ("Text", "Upload File", "URL")
    )
    
    if input_method == "Text":
        text_input = st.text_area("Enter your text here", height=300)
    elif input_method == "Upload File":
        uploaded_file = st.file_uploader("Upload a text file", type=["txt", "pdf", "docx"])
        if uploaded_file:
            # Here you would add code to extract text from different file types
            # For now, assume it's a text file
            text_input = uploaded_file.read().decode()
    else:  # URL
        url_input = st.text_input("Enter URL")
        if url_input:
            # Here you would add code to scrape text from URL
            # For simplicity, we'll just use a placeholder
            text_input = "Text extracted from URL would go here"
    
    num_questions = st.slider("Number of questions", 1, 20, 5)
    difficulty = st.select_slider(
        "Difficulty level",
        options=["easy", "medium", "hard"]
    )
    
    # Generate quiz button
    if st.button("Generate Quiz"):
        if input_method == "Text" and text_input:
            with st.spinner("Generating quiz..."):
                try:
                    response = requests.post(
                        f"{API_URL}/generate-quiz/",
                        json={"content": text_input, "num_questions": num_questions, "difficulty": difficulty}
                    )
                    
                    if response.status_code == 200:
                        st.session_state.quiz = response.json()
                        st.session_state.current_question = 0
                        st.session_state.answers = []
                        st.session_state.quiz_completed = False
                        st.session_state.show_explanation = False
                        st.success("Quiz generated successfully!")
                    else:
                        st.error(f"Error: {response.text}")
                except Exception as e:
                    st.error(f"Failed to connect to the backend: {str(e)}")
        else:
            st.warning("Please enter some text to generate a quiz")

# Main content - Display quiz
if st.session_state.quiz:
    quiz = st.session_state.quiz
    
    # Display quiz title
    st.markdown(f"<h1 class='title'>{quiz['title']}</h1>", unsafe_allow_html=True)
    
    # Progress bar
    progress = (st.session_state.current_question + 1) / len(quiz['questions'])
    st.progress(progress)
    
    # Display current question
    if not st.session_state.quiz_completed:
        question = quiz['questions'][st.session_state.current_question]
        
        # Create columns for better layout
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.markdown(f"<div class='quiz-question'>", unsafe_allow_html=True)
            st.markdown(f"### Question {st.session_state.current_question + 1} of {len(quiz['questions'])}")
            st.markdown(f"**{question['question_text']}**")
            
            # Display options
            selected_option = None
            
            for i, option in enumerate(question['options']):
                option_key = f"q{st.session_state.current_question}_opt{i}"
                
                # If answer already provided (going back to review)
                if len(st.session_state.answers) > st.session_state.current_question:
                    selected = st.session_state.answers[st.session_state.current_question] == i
                    correct = question['correct_answer'] == i
                    
                    if selected and correct:
                        st.markdown(f"<div class='option correct'>✓ {chr(65+i)}. {option}</div>", unsafe_allow_html=True)
                    elif selected and not correct:
                        st.markdown(f"<div class='option incorrect'>✗ {chr(65+i)}. {option}</div>", unsafe_allow_html=True)
                    elif not selected and correct:
                        st.markdown(f"<div class='option correct'>{chr(65+i)}. {option}</div>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<div class='option'>{chr(65+i)}. {option}</div>", unsafe_allow_html=True)
                else:
                    # New question, no answer yet
                    if st.button(f"{chr(65+i)}. {option}", key=option_key):
                        selected_option = i
            
            # Show explanation if answer was given
            if (len(st.session_state.answers) > st.session_state.current_question or
                st.session_state.show_explanation):
                st.markdown(f"<div class='explanation'><strong>Explanation:</strong> {question['explanation']}</div>", 
                            unsafe_allow_html=True)
            
            st.markdown(f"</div>", unsafe_allow_html=True)
            
            # Navigation buttons
            col_prev, col_next = st.columns(2)
            
            with col_prev:
                if st.session_state.current_question > 0:
                    if st.button("← Previous Question"):
                        st.session_state.current_question -= 1
                        st.experimental_rerun()
            
            with col_next:
                if selected_option is not None:
                    # Save the answer
                    if len(st.session_state.answers) > st.session_state.current_question:
                        st.session_state.answers[st.session_state.current_question] = selected_option
                    else:
                        st.session_state.answers.append(selected_option)
                    
                    # Show explanation
                    st.session_state.show_explanation = True
                    
                    # If last question, show results button
                    if st.session_state.current_question == len(quiz['questions']) - 1:
                        if st.button("Show Results"):
                            st.session_state.quiz_completed = True
                            st.experimental_rerun()
                    else:
                        if st.button("Next Question →"):
                            st.session_state.current_question += 1
                            st.session_state.show_explanation = False
                            st.experimental_rerun()
        
        with col2:
            # Show source text summary
            st.markdown("### Source Material")
            st.markdown(f"*{quiz['source_text_summary']}*")
            
            # Metadata about the question
            st.markdown("### Question Info")
            st.markdown(f"**Topic:** {question['topic']}")
            st.markdown(f"**Difficulty:** {question['difficulty'].capitalize()}")
    else:
        # Quiz completed - show results
        st.markdown("## Quiz Results")
        
        # Calculate score
        correct_answers = sum(1 for i, ans in enumerate(st.session_state.answers) 
                            if ans == quiz['questions'][i]['correct_answer'])
        score_percentage = (correct_answers / len(quiz['questions'])) * 100
        
        # Create a visually appealing score card
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown(f"<div style='background-color:white; padding:30px; border-radius:10px; text-align:center;'>",
                       unsafe_allow_html=True)
            st.markdown(f"<h1 style='font-size:48px;'>{score_percentage:.1f}%</h1>", unsafe_allow_html=True)
            st.markdown(f"<p>You answered <b>{correct_answers}/{len(quiz['questions'])}</b> questions correctly</p>",
                       unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
            
            # Question breakdown table
            st.markdown("### Question Breakdown")
            results_data = []
            
            for i, question in enumerate(quiz['questions']):
                user_answer = st.session_state.answers[i]
                is_correct = user_answer == question['correct_answer']
                
                results_data.append({
                    "Question": i + 1,
                    "Topic": question['topic'],
                    "Your Answer": chr(65 + user_answer),
                    "Correct Answer": chr(65 + question['correct_answer']),
                    "Status": "✓ Correct" if is_correct else "✗ Incorrect"
                })
            
            results_df = pd.DataFrame(results_data)
            st.dataframe(results_df, use_container_width=True)
        
        with col2:
            # Generate analytics charts
            st.markdown("### Performance Analytics")
            
            # Performance by topic
            topic_performance = {}
            for i, question in enumerate(quiz['questions']):
                topic = question['topic']
                is_correct = st.session_state.answers[i] == question['correct_answer']
                
                if topic not in topic_performance:
                    topic_performance[topic] = {"correct": 0, "total": 0}
                
                topic_performance[topic]["total"] += 1
                if is_correct:
                    topic_performance[topic]["correct"] += 1
            
            # Create topic performance chart
            topics = list(topic_performance.keys())
            percentages = [t["correct"]/t["total"]*100 for t in topic_performance.values()]
            
            fig, ax = plt.subplots(figsize=(8, 4))
            bars = ax.barh(topics, percentages, color='skyblue')
            ax.set_xlabel('Correctness (%)')
            ax.set_xlim(0, 100)
            
            # Add percentage labels to bars
            for bar in bars:
                width = bar.get_width()
                label_x_pos = width if width > 10 else 10
                ax.text(label_x_pos, bar.get_y() + bar.get_height()/2, f'{width:.1f}%',
                       va='center', color='black' if width > 10 else 'black')
            
            st.pyplot(fig)
            
            # Option for restart
            if st.button("Start a New Quiz"):
                st.session_state.quiz = None
                st.session_state.current_question = 0
                st.session_state.answers = []
                st.session_state.quiz_completed = False
                st.experimental_rerun()
else:
    # Show welcome screen when no quiz is active
    st.markdown("<h1 style='text-align:center;'>Welcome to AI Quiz Generator</h1>", unsafe_allow_html=True)
    st.markdown("""
    <div style='text-align:center; padding:20px; background-color:white; border-radius:10px;'>
        <img src="https://img.icons8.com/color/96/000000/quiz.png" width="100">
        <h3>How it works:</h3>
        <ol style='text-align:left;'>
            <li>Enter text or upload a document in the sidebar</li>
            <li>Choose the number of questions and difficulty level</li>
            <li>Click "Generate Quiz" to create your custom quiz</li>
            <li>Answer the questions and see your results!</li>
        </ol>
    </div>
    """, unsafe_allow_html=True)
    
    # Features section
    st.markdown("## Features")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
        ### AI-Powered
        Uses advanced NLP and GPT-3.5 to create high-quality, relevant questions
        """)
    with col2:
        st.markdown("""
        ### Customizable
        Adjust difficulty and number of questions to fit your needs
        """)
    with col3:
        st.markdown("""
        ### Insightful
        Get detailed analytics about your performance
        """)

if __name__ == "__main__":
    # This will only execute in standalone mode
    pass
