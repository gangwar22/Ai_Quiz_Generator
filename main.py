from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
import random
import re
import nltk
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, pipeline
import torch
import time
import threading
import webbrowser
import uvicorn

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)

try:
    nltk.data.find('corpora/stopwords')  
except LookupError:
    nltk.download('stopwords', quiet=True)

app = FastAPI()

# Add CORS middleware to allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Global variables for AI models
tokenizer = None
model = None
qa_pipeline = None

# Quiz storage for tracking generated quizzes
quiz_storage = {}

def load_ai_models():
    """Load AI models for question generation"""
    global tokenizer, model, qa_pipeline
    
    if tokenizer is None or model is None:
        print("🤖 Loading T5 model for question generation...")
        try:
            # Try to load the specialized QG model first
            tokenizer = AutoTokenizer.from_pretrained("valhalla/t5-base-qa-qg-hl")
            model = AutoModelForSeq2SeqLM.from_pretrained("valhalla/t5-base-qa-qg-hl")
            print("✅ Specialized T5 QG model loaded successfully!")
        except Exception as e:
            print(f"⚠️  Specialized model failed, using T5-small: {e}")
            # Fallback to smaller model
            tokenizer = AutoTokenizer.from_pretrained("t5-small")
            model = AutoModelForSeq2SeqLM.from_pretrained("t5-small")
            print("✅ T5-small model loaded successfully!")
    
    if qa_pipeline is None:
        try:
            print("🤖 Loading QA pipeline...")
            qa_pipeline = pipeline("question-answering", model="distilbert-base-cased-distilled-squad")
            print("✅ QA pipeline loaded successfully!")
        except Exception as e:
            print(f"⚠️  QA pipeline failed: {e}")
            qa_pipeline = None

class QuizRequest(BaseModel):
    text: str
    num_questions: int = 5
    difficulty: str = "medium"
    question_type: str = "mixed"

class MCQOption(BaseModel):
    text: str
    is_correct: bool

class MCQuestion(BaseModel):
    id: int
    question: str
    options: List[MCQOption]
    correct_answer: str
    difficulty: str
    explanation: str = ""

class Quiz(BaseModel):
    id: str
    title: str
    description: str
    questions: List[MCQuestion]
    total_questions: int
    difficulty: str
    created_at: str

class QuizSubmission(BaseModel):
    quiz_id: str
    answers: Dict[str, str]

class QuizResult(BaseModel):
    quiz_id: str
    score: int
    total_questions: int
    percentage: float
    correct_answers: List[int]
    incorrect_answers: List[int]
    detailed_results: List[Dict[str, Any]] = []

def extract_key_sentences(text: str, max_sentences: int = 15) -> List[str]:
    """Extract key sentences from text using advanced methods"""
    from nltk.tokenize import sent_tokenize
    from nltk.corpus import stopwords
    
    try:
        # Use NLTK for better sentence segmentation
        sentences = sent_tokenize(text)
        stop_words = set(stopwords.words('english'))
        
        # Score sentences based on content richness
        scored_sentences = []
        for sentence in sentences:
            words = sentence.lower().split()
            # Filter out very short sentences
            if len(words) < 5:
                continue
            
            # Calculate content score
            content_words = [w for w in words if w not in stop_words and len(w) > 3]
            score = len(content_words) / len(words) if words else 0
            
            # Bonus for sentences with numbers, proper nouns, technical terms
            if any(char.isdigit() for char in sentence):
                score += 0.2
            if any(word[0].isupper() and len(word) > 1 for word in sentence.split()):
                score += 0.1
            
            scored_sentences.append((sentence.strip(), score))
        
        # Sort by score and return top sentences
        scored_sentences.sort(key=lambda x: x[1], reverse=True)
        return [sent[0] for sent in scored_sentences[:max_sentences]]
        
    except Exception as e:
        print(f"⚠️  Advanced sentence extraction failed: {e}")
        # Fallback to simple method
        sentences = re.split(r'[.!?]+', text.strip())
        clean_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 20 and len(sentence.split()) > 4:
                clean_sentences.append(sentence)
        return clean_sentences[:max_sentences]

def generate_ai_question(sentence: str, difficulty: str = "medium") -> str:
    """Generate question using AI model"""
    global tokenizer, model
    
    try:
        load_ai_models()
        
        # Different prompts based on difficulty
        if difficulty == "easy":
            prompt = f"generate question: {sentence}"
        elif difficulty == "hard":
            prompt = f"generate complex analytical question: {sentence}"
        else:  # medium
            prompt = f"generate comprehension question: {sentence}"
        
        # Tokenize input
        inputs = tokenizer(prompt, return_tensors="pt", max_length=512, truncation=True)
        
        # Generate question
        with torch.no_grad():
            outputs = model.generate(
                inputs.input_ids,
                max_length=100,
                num_beams=4,
                temperature=0.8,
                do_sample=True,
                early_stopping=True,
                pad_token_id=tokenizer.eos_token_id
            )
        
        question = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Clean up the question
        question = question.strip()
        if not question.endswith('?'):
            question += '?'
            
        return question
        
    except Exception as e:
        print(f"⚠️  AI question generation failed: {e}")
        # Fallback to pattern-based generation
        return generate_fallback_question(sentence, difficulty)

def generate_fallback_question(sentence: str, difficulty: str) -> str:
    """Fallback question generation using patterns"""
    sentence = sentence.strip()
    words = sentence.split()
    
    # Extract key entities
    important_words = [w for w in words if len(w) > 3 and w[0].isupper()]
    
    if difficulty == "easy":
        patterns = [
            f"What is mentioned in the text about {important_words[0] if important_words else words[0]}?",
            f"According to the passage, what is {words[1] if len(words) > 1 else 'the main topic'}?",
        ]
    elif difficulty == "hard":
        patterns = [
            f"Analyze the relationship between {important_words[0] if important_words else words[0]} and {important_words[1] if len(important_words) > 1 else words[-1]}.",
            f"What can be inferred from the statement about {words[2] if len(words) > 2 else 'the concept'}?",
        ]
    else:  # medium
        patterns = [
            f"What does the text explain about {important_words[0] if important_words else words[0]}?",
            f"According to the information provided, how is {words[1] if len(words) > 1 else 'this'} described?",
        ]
    
    question = random.choice(patterns)
    if not question.endswith('?'):
        question += '?'
    return question

def generate_smart_options(sentence: str, full_text: str, difficulty: str = "medium") -> tuple:
    """Generate intelligent multiple choice options"""
    try:
        # Tokenize the text for analysis
        words = nltk.word_tokenize(sentence)
        pos_tags = nltk.pos_tag(words)
        
        # Extract key information from sentence
        nouns = [word for word, pos in pos_tags if pos.startswith('NN')]
        verbs = [word for word, pos in pos_tags if pos.startswith('VB')]
        adjectives = [word for word, pos in pos_tags if pos.startswith('JJ')]
        
        # Generate correct answer based on sentence
        correct_answer = extract_answer_from_sentence(sentence, difficulty)
        
        # Generate distractors
        distractors = generate_distractors(sentence, full_text, nouns, verbs, adjectives, difficulty)
        
        # Combine all options
        all_options = [correct_answer] + distractors
        
        # Ensure we have exactly 4 options
        while len(all_options) < 4:
            all_options.append(f"None of the above mentioned options")
        
        # Shuffle and find correct position
        random.shuffle(all_options)
        correct_pos = all_options.index(correct_answer)
        correct_letter = chr(65 + correct_pos)  # A, B, C, D
        
        return all_options, correct_letter
        
    except Exception as e:
        print(f"⚠️  Smart options generation failed: {e}")
        return generate_options_simple(sentence, 4), "A"

def extract_answer_from_sentence(sentence: str, difficulty: str) -> str:
    """Extract the most appropriate answer from sentence"""
    words = sentence.split()
    
    if difficulty == "easy":
        # Simple factual answer
        if len(words) > 10:
            return " ".join(words[:8]) + "..."
        else:
            return sentence
    elif difficulty == "hard":
        # More complex analytical answer
        important_part = " ".join(words[2:8]) if len(words) > 8 else sentence
        return f"The concept that {important_part.lower()}"
    else:  # medium
        # Balanced answer
        if len(words) > 6:
            return " ".join(words[:6]) + "..."
        else:
            return sentence

def generate_distractors(sentence: str, full_text: str, nouns: list, verbs: list, adjectives: list, difficulty: str) -> list:
    """Generate realistic wrong answers"""
    distractors = []
    
    # Get other sentences from text for context
    other_sentences = [s.strip() for s in full_text.split('.') if s.strip() and s != sentence]
    
    # Type 1: Partially correct but modified
    if nouns and verbs:
        modified = f"{random.choice(nouns)} {random.choice(verbs)} differently than described"
        distractors.append(modified)
    
    # Type 2: Opposite/contradictory statement
    if adjectives:
        opposite_adj = get_opposite_adjective(random.choice(adjectives))
        distractor = sentence.replace(random.choice(adjectives), opposite_adj, 1)[:60] + "..."
        distractors.append(distractor)
    
    # Type 3: Information from other parts of text
    if other_sentences:
        other_info = random.choice(other_sentences)[:50] + "..."
        distractors.append(other_info)
    
    # Type 4: Plausible but incorrect
    if len(distractors) < 3:
        plausible = f"This information is not mentioned in the given text"
        distractors.append(plausible)
    
    return distractors[:3]

def get_opposite_adjective(adj: str) -> str:
    """Get opposite or contrasting adjective"""
    opposites = {
        'good': 'bad', 'big': 'small', 'fast': 'slow', 'high': 'low',
        'hot': 'cold', 'new': 'old', 'easy': 'difficult', 'light': 'dark',
        'strong': 'weak', 'hard': 'soft', 'clean': 'dirty', 'rich': 'poor'
    }
    return opposites.get(adj.lower(), 'different')

def generate_options_simple(sentence: str, num_options: int = 4) -> List[str]:
    """Generate simple options from sentence"""
    words = sentence.split()
    
    # Extract meaningful words (longer than 3 characters)
    meaningful_words = [word for word in words if len(word) > 3 and word.isalpha()]
    
    options = []
    
    # Use actual words from sentence
    if len(meaningful_words) >= num_options:
        selected_words = random.sample(meaningful_words, num_options)
        options = [word.capitalize() for word in selected_words]
    else:
        # Use available words and add generic options
        options = [word.capitalize() for word in meaningful_words]
        while len(options) < num_options:
            options.append(f"Alternative option {len(options) + 1}")
    
    return options

@app.get("/")
async def read_root():
    """Serve the main page"""
    return FileResponse("static/index.html")

@app.post("/api/generate-quiz")
async def create_quiz(request: QuizRequest):
    """Generate quiz from text"""
    try:
        print(f"📝 Received request: {len(request.text)} characters, {request.num_questions} questions")
        
        if len(request.text) < 200:
            raise HTTPException(status_code=400, detail="Text must be at least 200 characters long")
        
        # Extract sentences
        sentences = extract_key_sentences(request.text)
        print(f"📄 Extracted {len(sentences)} sentences")
        
        if not sentences:
            raise HTTPException(status_code=400, detail="Could not extract any sentences from the text")
        
        # Ensure we have enough sentences
        if len(sentences) < request.num_questions:
            # Repeat sentences if needed
            sentences = sentences * ((request.num_questions // len(sentences)) + 1)
        
        questions = []
        quiz_id = f"quiz_{random.randint(1000, 9999)}"
        
        print(f"🎯 Generating {request.num_questions} questions...")
        
        for i in range(request.num_questions):
            sentence = sentences[i % len(sentences)]
            
            # Generate question
            question_text = generate_ai_question(sentence, request.difficulty)
            
            # Generate smart options
            option_texts, correct_letter = generate_smart_options(sentence, request.text, request.difficulty)
            
            # Create MCQ options
            options = []
            for j, opt_text in enumerate(option_texts):
                letter = chr(65 + j)  # A, B, C, D
                is_correct = (letter == correct_letter)
                options.append(MCQOption(text=opt_text, is_correct=is_correct))
            
            # Find correct answer position
            correct_pos = None
            for idx, option in enumerate(options):
                if option.is_correct:
                    correct_pos = idx
                    break
            
            correct_letter = chr(65 + correct_pos) if correct_pos is not None else "A"
            
            question = MCQuestion(
                id=i + 1,
                question=question_text,
                options=options,
                correct_answer=correct_letter,
                difficulty=request.difficulty,
                explanation=f"Based on: {sentence[:80]}..."
            )
            
            questions.append(question)
            print(f"✅ Generated question {i+1}: {question_text[:50]}...")
        
        quiz = Quiz(
            id=quiz_id,
            title="AI Generated Quiz",
            description=f"Quiz generated from your content with {len(questions)} questions",
            questions=questions,
            total_questions=len(questions),
            difficulty=request.difficulty,
            created_at="2025-10-04"
        )
        
        # Store quiz in memory for later evaluation
        quiz_storage[quiz_id] = quiz
        
        print(f"🎉 Quiz generated successfully! ID: {quiz_id}")
        print(f"📦 Quiz stored in memory for evaluation")
        return quiz
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error creating quiz: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate quiz: {str(e)}")

@app.post("/api/evaluate-quiz")
async def evaluate_quiz(submission: QuizSubmission):
    """Evaluate quiz answers with actual quiz data"""
    try:
        print(f"🔍 Evaluating quiz: {submission.quiz_id}")
        print(f"📝 Received {len(submission.answers)} answers")
        
        # Get the quiz from our storage
        if submission.quiz_id not in quiz_storage:
            raise HTTPException(status_code=404, detail="Quiz not found")
        
        quiz = quiz_storage[submission.quiz_id]
        total_questions = len(quiz.questions)
        correct_count = 0
        
        detailed_results = []
        
        # Evaluate each answer against the actual quiz data
        for i, question in enumerate(quiz.questions):
            question_num = str(i + 1)  # Questions are numbered from 1
            selected_answer = submission.answers.get(question_num, "")
            
            # Find the correct answer
            correct_option = None
            correct_letter = ""
            
            for idx, option in enumerate(question.options):
                if option.is_correct:
                    correct_option = option.text
                    correct_letter = chr(65 + idx)  # A, B, C, D
                    break
            
            # Check if the selected answer is correct
            is_correct = (selected_answer == correct_letter)
            if is_correct:
                correct_count += 1
            
            # Get selected answer text
            selected_text = next((opt.text for idx, opt in enumerate(question.options) 
                                if chr(65 + idx) == selected_answer), "No answer provided")
            
            # Create detailed explanation
            if is_correct:
                explanation = f"✅ Excellent! Your answer '{correct_letter}: {correct_option}' is absolutely correct."
                status_message = "Correct Answer"
            else:
                explanation = f"❌ Incorrect answer. You selected '{selected_answer}: {selected_text}', but the correct answer is '{correct_letter}: {correct_option}'."
                status_message = "Wrong Answer"
            
            # Store detailed result
            detailed_results.append({
                "question_id": question_num,
                "question_text": question.question,
                "selected": selected_answer,
                "selected_text": selected_text,
                "correct": correct_letter,
                "correct_text": correct_option,
                "is_correct": is_correct,
                "explanation": explanation,
                "status": status_message,
                "all_options": [{"letter": chr(65 + idx), "text": opt.text, "is_correct": opt.is_correct} 
                              for idx, opt in enumerate(question.options)]
            })
        
        percentage = round((correct_count / total_questions) * 100, 1) if total_questions > 0 else 0
        
        print(f"✅ Evaluation completed: {correct_count}/{total_questions} ({percentage}%)")
        
        # Create lists of correct and incorrect question numbers
        correct_questions = [int(res["question_id"]) for res in detailed_results if res["is_correct"]]
        incorrect_questions = [int(res["question_id"]) for res in detailed_results if not res["is_correct"]]
        
        result = QuizResult(
            quiz_id=submission.quiz_id,
            score=correct_count,
            total_questions=total_questions,
            percentage=percentage,
            correct_answers=correct_questions,
            incorrect_answers=incorrect_questions,
            detailed_results=detailed_results
        )
        
        print(f"📊 Quiz evaluated: {correct_count}/{total_questions} correct ({percentage}%)")
        return result
        
    except Exception as e:
        print(f"❌ Error evaluating quiz: {e}")
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")

@app.get("/api/export-quiz/{quiz_id}")
async def export_quiz_pdf(quiz_id: str):
    """Export quiz as PDF"""
    try:
        if quiz_id not in quiz_storage:
            raise HTTPException(status_code=404, detail="Quiz not found")
        
        quiz = quiz_storage[quiz_id]
        
        # Create simple text format for download
        content = f"""AI Quiz Generator - Quiz Export

Title: {quiz.title}
Questions: {quiz.total_questions}
Difficulty: {quiz.difficulty}
Created: {quiz.created_at}

Questions & Answers:
{"="*50}

"""
        
        for i, question in enumerate(quiz.questions, 1):
            content += f"Q{i}: {question.question}\n\n"
            
            for j, option in enumerate(question.options):
                letter = chr(65 + j)  # A, B, C, D
                marker = "✓" if option.is_correct else " "
                content += f"  {letter}) {option.text} {marker}\n"
            
            correct_answer = next((chr(65 + j) for j, opt in enumerate(question.options) if opt.is_correct), "A")
            content += f"\nCorrect Answer: {correct_answer}\n\n{'-'*40}\n\n"
        
        # Return as downloadable text file
        from fastapi.responses import Response
        return Response(
            content=content,
            media_type="text/plain",
            headers={"Content-Disposition": f"attachment; filename=quiz_{quiz_id}.txt"}
        )
        
    except Exception as e:
        print(f"❌ Export error: {e}")
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "AI Quiz Generator is working perfectly! 🚀"}

if __name__ == "__main__":
    import uvicorn
    import webbrowser
    import threading
    import time
    
    def open_browser():
        """Open browser after server starts"""
        time.sleep(2)  # Wait for server to start
        webbrowser.open('http://localhost:8000')
        print("🌐 Browser opened at http://localhost:8000")
    
    # Start browser opener in background
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()
    
    print("🚀 Starting AI Quiz Generator...")
    print("🌐 Browser will open automatically...")
    
    uvicorn.run(app, host="localhost", port=8000)