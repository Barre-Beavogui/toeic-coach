import streamlit as st
import json
import pandas as pd
import datetime
import random
import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# App configuration
st.set_page_config(page_title="TOEIC Coach", page_icon="📈")

# Gemini Setup
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    model = None

# Paths
DATA_DIR = "data"
PROGRESS_FILE = os.path.join(DATA_DIR, "progress.json")
VOCAB_FILE = os.path.join(DATA_DIR, "vocab.json")
QUIZ_FILE = os.path.join(DATA_DIR, "quiz.json")

# Helper to load JSON
def load_json(file_path):
    if not os.path.exists(file_path):
        return {"history": []} if "progress" in file_path else []
    with open(file_path, 'r') as f:
        return json.load(f)

# Helper to save JSON
def save_json(file_path, data):
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=4)

# AI Coaching Function
def get_ai_advice(history):
    if not model:
        return "Configurez votre GEMINI_API_KEY dans le fichier .env pour recevoir des conseils personnalisés."
    
    prompt = f"""
    En tant que coach expert TOEIC, analyse mon historique de progression suivant :
    {json.dumps(history[-5:])}
    
    Donne-moi 3 conseils précis pour m'améliorer, encourage-moi et suggère-moi un point de grammaire à réviser.
    Sois concis et motivant.
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Erreur lors de la génération du conseil : {str(e)}"

# Initialize Session State
if 'current_page' not in st.session_state:
    st.session_state.current_page = "Dashboard"
if 'quiz_submitted' not in st.session_state:
    st.session_state.quiz_submitted = False
if 'flashcard_index' not in st.session_state:
    st.session_state.flashcard_index = 0
if 'show_translation' not in st.session_state:
    st.session_state.show_translation = False

# Sidebar Navigation
st.sidebar.title("TOEIC Coach")
page = st.sidebar.radio("Navigation", ["Dashboard", "Quiz TOEIC", "Flashcards Vocabulaire", "Coach IA Gemini"])
st.session_state.current_page = page

# --- Dashboard Section ---
if st.session_state.current_page == "Dashboard":
    st.title("📊 Votre Progression TOEIC")
    
    progress_data = load_json(PROGRESS_FILE)
    history = progress_data.get("history", [])
    
    if not history:
        st.info("Vous n'avez pas encore complété de quiz. Commencez par la section 'Quiz TOEIC' !")
    else:
        df = pd.DataFrame(history)
        df['date'] = pd.to_datetime(df['date'])
        
        # Metrics
        col1, col2, col3 = st.columns(3)
        avg_score = df['score'].mean()
        total_quizzes = len(df)
        last_score = df['score'].iloc[-1]
        
        col1.metric("Score Moyen", f"{avg_score:.1f}%")
        col2.metric("Quiz Complétés", total_quizzes)
        col3.metric("Dernier Score", f"{last_score}%")
        
        # Progress Chart
        st.subheader("Évolution de vos scores")
        chart_data = df.set_index('date')['score']
        st.line_chart(chart_data)
        
        # History Table
        st.subheader("Historique récent")
        st.dataframe(df.sort_values(by='date', ascending=False), use_container_width=True)

# --- Coach IA Section ---
elif st.session_state.current_page == "Coach IA Gemini":
    st.title("🤖 Coach IA Gemini")
    st.write("Analyse personnalisée de vos performances par l'IA.")
    
    progress_data = load_json(PROGRESS_FILE)
    history = progress_data.get("history", [])
    
    if not history:
        st.warning("Complétez au moins un quiz pour que l'IA puisse analyser vos performances.")
    else:
        if st.button("Obtenir mon analyse personnalisée"):
            with st.spinner("Analyse en cours par Gemini..."):
                advice = get_ai_advice(history)
                st.markdown(f"### 💡 Conseils de votre Coach\n\n{advice}")
                
# --- Quiz TOEIC Section ---
elif st.session_state.current_page == "Quiz TOEIC":
    st.title("✍️ Quiz TOEIC")
    
    quiz_questions = load_json(QUIZ_FILE)
    
    with st.form("toeic_quiz"):
        user_answers = {}
        for q in quiz_questions:
            st.write(f"**Q{q['id']}:** {q['question']}")
            user_answers[q['id']] = st.radio(f"Choisissez une option pour Q{q['id']}", q['options'], key=f"q_{q['id']}", label_visibility="collapsed")
            st.divider()
            
        submitted = st.form_submit_state = st.form_submit_button("Soumettre le Quiz")
        
        if submitted:
            score = 0
            for q in quiz_questions:
                if user_answers[q['id']] == q['answer']:
                    score += 1
            
            percentage = int((score / len(quiz_questions)) * 100)
            st.success(f"Quiz terminé ! Votre score : {score}/{len(quiz_questions)} ({percentage}%)")
            
            # Save progress
            progress_data = load_json(PROGRESS_FILE)
            new_entry = {
                "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                "score": percentage
            }
            progress_data["history"].append(new_entry)
            save_json(PROGRESS_FILE, progress_data)
            st.balloons()

# --- Flashcards Vocabulaire Section ---
elif st.session_state.current_page == "Flashcards Vocabulaire":
    st.title("📚 Flashcards Vocabulaire")
    
    vocab_list = load_json(VOCAB_FILE)
    
    if 'vocab_order' not in st.session_state:
        st.session_state.vocab_order = list(range(len(vocab_list)))
        random.shuffle(st.session_state.vocab_order)

    current_idx = st.session_state.flashcard_index % len(vocab_list)
    word_data = vocab_list[st.session_state.vocab_order[current_idx]]
    
    st.markdown(f"""
    <div style="border: 2px solid #4CAF50; border-radius: 10px; padding: 40px; text-align: center; background-color: #f9f9f9; color: #333;">
        <h1 style="color: #2E7D32;">{word_data['word']}</h1>
    </div>
    """, unsafe_allow_html=True)
    
    st.write("")
    
    if st.button("Voir la définition / Traduction"):
        st.session_state.show_translation = True
        
    if st.session_state.show_translation:
        st.info(f"**Définition:** {word_data['definition']}")
        st.write(f"**Exemple:** *{word_data['example']}*")
        
    st.write("")
    
    if st.button("Mot Suivant ➡️"):
        st.session_state.flashcard_index += 1
        st.session_state.show_translation = False
        st.rerun()

    st.progress((current_idx + 1) / len(vocab_list), text=f"Progression : {current_idx + 1}/{len(vocab_list)}")
