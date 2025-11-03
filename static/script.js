// Global variables
let currentQuiz = null;
let currentQuestionIndex = 0;
let userAnswers = {};
let quizData = null;

// DOM elements
const textInput = document.getElementById('text-input');
const charCount = document.getElementById('char-count');
const generateBtn = document.getElementById('generate-btn');
const numQuestions = document.getElementById('num-questions');
const difficulty = document.getElementById('difficulty');
const questionType = document.getElementById('question-type');

// Sections
const inputSection = document.getElementById('input-section');
const loadingSection = document.getElementById('loading-section');
const quizSection = document.getElementById('quiz-section');
const resultsSection = document.getElementById('results-section');

// Quiz elements
const questionText = document.getElementById('question-text');
const optionsContainer = document.getElementById('options-container');
const currentQuestionSpan = document.getElementById('current-question');
const totalQuestionsSpan = document.getElementById('total-questions');
const quizProgress = document.getElementById('quiz-progress');
const prevBtn = document.getElementById('prev-btn');
const nextBtn = document.getElementById('next-btn');
const submitQuizBtn = document.getElementById('submit-quiz-btn');

// Results elements
const scorePercentage = document.getElementById('score-percentage');
const scoreDetails = document.getElementById('score-details');
const resultsList = document.getElementById('results-list');
const restartBtn = document.getElementById('restart-btn');

// Loading elements
const loadingTitle = document.getElementById('loading-title');
const loadingDescription = document.getElementById('loading-description');
const exportBtn = document.getElementById('export-btn');

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    initializeEventListeners();
    updateCharCount();
});

function initializeEventListeners() {
    // Text input character counter
    textInput.addEventListener('input', updateCharCount);
    
    // Generate quiz button
    generateBtn.addEventListener('click', generateQuiz);
    
    // Quiz navigation
    prevBtn.addEventListener('click', previousQuestion);
    nextBtn.addEventListener('click', nextQuestion);
    submitQuizBtn.addEventListener('click', submitQuiz);
    
    // Results actions
    restartBtn.addEventListener('click', restartQuiz);
    exportBtn.addEventListener('click', exportQuiz);
    
    // Enter key handling for text input
    textInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && e.ctrlKey && generateBtn.disabled === false) {
            generateQuiz();
        }
    });
}

function updateCharCount() {
    const count = textInput.value.length;
    charCount.textContent = count;
    
    const counter = charCount.parentElement;
    if (count >= 200) {
        counter.classList.add('valid');
        counter.classList.remove('invalid');
        generateBtn.disabled = false;
    } else {
        counter.classList.add('invalid');
        counter.classList.remove('valid');
        generateBtn.disabled = true;
    }
}

async function generateQuiz() {
    const text = textInput.value.trim();
    
    if (text.length < 200) {
        alert('Please provide at least 200 characters of text.');
        return;
    }
    
    // Show loading section
    showSection('loading');
    
    const requestData = {
        text: text,
        num_questions: parseInt(numQuestions.value),
        difficulty: difficulty.value,
        question_type: questionType.value
    };
    
    try {
        // Update loading message for quiz generation
        updateLoadingMessage('Generating Your Quiz...', 'Our AI is analyzing your text and creating intelligent questions');
        
        // Simulate loading time for better UX
        setTimeout(async () => {
            const response = await fetch('/api/generate-quiz', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestData)
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            quizData = await response.json();
            console.log('Quiz generated:', quizData);
            
            // Initialize quiz
            initializeQuiz(quizData);
            showSection('quiz');
        }, 2000);
        
    } catch (error) {
        console.error('Error generating quiz:', error);
        alert('Failed to generate quiz. Please try again.');
        showSection('input');
    }
}

function initializeQuiz(quiz) {
    currentQuiz = quiz;
    currentQuestionIndex = 0;
    userAnswers = {};
    
    totalQuestionsSpan.textContent = quiz.questions.length;
    document.getElementById('quiz-title').textContent = quiz.title;
    
    displayCurrentQuestion();
}

function displayCurrentQuestion() {
    const question = currentQuiz.questions[currentQuestionIndex];
    
    // Update question counter and progress
    currentQuestionSpan.textContent = currentQuestionIndex + 1;
    const progress = ((currentQuestionIndex + 1) / currentQuiz.questions.length) * 100;
    quizProgress.style.width = `${progress}%`;
    
    // Display question text
    questionText.textContent = question.question;
    
    // Clear and populate options
    optionsContainer.innerHTML = '';
    
    question.options.forEach((option, index) => {
        const optionDiv = document.createElement('div');
        optionDiv.className = 'option';
        
        const optionLetter = String.fromCharCode(65 + index); // A, B, C, D
        
        optionDiv.innerHTML = `
            <input type="radio" name="question_${question.id}" value="${optionLetter}" id="option_${index}">
            <label for="option_${index}">${optionLetter}. ${option.text}</label>
        `;
        
        // Add click event to the entire option div
        optionDiv.addEventListener('click', function() {
            selectOption(optionDiv, optionLetter);
        });
        
        optionsContainer.appendChild(optionDiv);
    });
    
    // Restore previous selection if exists
    const previousAnswer = userAnswers[question.id];
    if (previousAnswer) {
        const optionIndex = previousAnswer.charCodeAt(0) - 65; // Convert A,B,C,D to 0,1,2,3
        const optionDivs = optionsContainer.querySelectorAll('.option');
        if (optionDivs[optionIndex]) {
            selectOption(optionDivs[optionIndex], previousAnswer);
        }
    }
    
    // Update navigation buttons
    updateNavigationButtons();
}

function selectOption(optionDiv, value) {
    // Remove selection from all options
    optionsContainer.querySelectorAll('.option').forEach(opt => {
        opt.classList.remove('selected');
    });
    
    // Add selection to clicked option
    optionDiv.classList.add('selected');
    
    // Update radio button
    const radio = optionDiv.querySelector('input[type="radio"]');
    radio.checked = true;
    
    // Store answer
    const currentQuestion = currentQuiz.questions[currentQuestionIndex];
    userAnswers[currentQuestion.id] = value;
    
    // Update navigation buttons
    updateNavigationButtons();
}

function updateNavigationButtons() {
    const isFirstQuestion = currentQuestionIndex === 0;
    const isLastQuestion = currentQuestionIndex === currentQuiz.questions.length - 1;
    const hasAnswer = userAnswers[currentQuiz.questions[currentQuestionIndex].id];
    
    prevBtn.disabled = isFirstQuestion;
    
    if (isLastQuestion) {
        nextBtn.style.display = 'none';
        submitQuizBtn.style.display = 'inline-flex';
        submitQuizBtn.disabled = !hasAnswer;
    } else {
        nextBtn.style.display = 'inline-flex';
        submitQuizBtn.style.display = 'none';
        nextBtn.disabled = !hasAnswer;
    }
}

function previousQuestion() {
    if (currentQuestionIndex > 0) {
        currentQuestionIndex--;
        displayCurrentQuestion();
    }
}

function nextQuestion() {
    if (currentQuestionIndex < currentQuiz.questions.length - 1) {
        currentQuestionIndex++;
        displayCurrentQuestion();
    }
}

async function submitQuiz() {
    // Check if all questions are answered
    const totalQuestions = currentQuiz.questions.length;
    const answeredQuestions = Object.keys(userAnswers).length;
    
    if (answeredQuestions < totalQuestions) {
        const unanswered = totalQuestions - answeredQuestions;
        if (!confirm(`You have ${unanswered} unanswered questions. Submit anyway?`)) {
            return;
        }
    }
    
    showSection('loading');
    
    // Update loading message for quiz evaluation
    updateLoadingMessage('Evaluating Your Answers...', 'Calculating your score and preparing detailed results');
    
    try {
        const submission = {
            quiz_id: currentQuiz.id,
            answers: userAnswers
        };
        
        // Simulate API call delay
        setTimeout(async () => {
            const response = await fetch('/api/evaluate-quiz', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(submission)
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const results = await response.json();
            displayResults(results);
            showSection('results');
        }, 1500);
        
    } catch (error) {
        console.error('Error submitting quiz:', error);
        alert('Failed to submit quiz. Please try again.');
        showSection('quiz');
    }
}

function displayResults(results) {
    console.log('📊 Displaying results:', results);
    
    // Update score display
    const percentage = Math.round(results.percentage);
    scorePercentage.textContent = `${percentage}%`;
    scoreDetails.textContent = `You scored ${results.score} out of ${results.total_questions} questions correctly`;
    
    // Update score circle color based on performance
    const scoreCircle = document.querySelector('.score-circle');
    scoreCircle.className = 'score-circle'; // Reset classes
    
    if (percentage >= 80) {
        scoreCircle.classList.add('high');
    } else if (percentage >= 60) {
        scoreCircle.classList.add('medium');
    } else {
        scoreCircle.classList.add('low');
    }
    
    // Display detailed results using the detailed_results from backend
    resultsList.innerHTML = '';
    
    if (results.detailed_results && results.detailed_results.length > 0) {
        results.detailed_results.forEach((result, index) => {
            const resultItem = document.createElement('div');
            const isCorrect = result.is_correct;
            
            resultItem.className = `result-item ${isCorrect ? 'correct' : 'incorrect'}`;
            resultItem.innerHTML = `
                <div class="question-result">
                    <div class="question-header">
                        <strong>Q${result.question_id}:</strong> 
                        <span class="question-text">${result.question_text}</span>
                    </div>
                    <div class="answer-details">
                        <div class="user-answer">
                            <strong>Your Answer:</strong> 
                            <span class="${isCorrect ? 'correct-answer' : 'wrong-answer'}">
                                ${result.selected}: ${result.selected_text}
                                ${isCorrect ? ' ✅' : ' ❌'}
                            </span>
                        </div>
                        <div class="correct-answer-show">
                            <strong>Correct Answer:</strong> 
                            <span class="correct-answer">
                                ${result.correct}: ${result.correct_text} ✅
                            </span>
                        </div>
                        <div class="explanation-text">
                            <strong>Explanation:</strong> ${result.explanation || 'No explanation available'}
                        </div>
                        ${!isCorrect ? `
                        <div class="comparison-note">
                            <small><em>❌ You selected the wrong option</em></small>
                        </div>
                        ` : `
                        <div class="comparison-note">
                            <small><em>✅ Excellent! You got it right</em></small>
                        </div>
                        `}
                        ${result.all_options ? `
                        <div class="all-options-display">
                            <small><strong>All Options:</strong></small>
                            <div class="options-grid">
                                ${result.all_options.map(opt => `
                                    <div class="option-item ${opt.is_correct ? 'correct-option' : ''} ${opt.letter === result.selected ? 'selected-option' : ''}">
                                        <span class="option-letter">${opt.letter}.</span>
                                        <span class="option-text">${opt.text}</span>
                                        ${opt.is_correct ? '<span class="correct-mark">✅</span>' : ''}
                                        ${opt.letter === result.selected && !opt.is_correct ? '<span class="wrong-mark">❌</span>' : ''}
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                        ` : ''}
                    </div>
                </div>
                <div class="result-icon">
                    <i class="fas fa-${isCorrect ? 'check-circle' : 'times-circle'}" 
                       style="color: ${isCorrect ? '#10b981' : '#ef4444'}; font-size: 20px;"></i>
                </div>
            `;
            
            resultsList.appendChild(resultItem);
        });
    } else {
        // Fallback display if detailed results not available
        currentQuiz.questions.forEach((question, index) => {
            const resultItem = document.createElement('div');
            const questionNum = (index + 1).toString();
            const isCorrect = results.correct_answers.includes(parseInt(questionNum));
            const userAnswer = userAnswers[questionNum] || 'No answer';
            
            resultItem.className = `result-item ${isCorrect ? 'correct' : 'incorrect'}`;
            resultItem.innerHTML = `
                <div>
                    <strong>Q${index + 1}:</strong> ${question.question.substring(0, 60)}${question.question.length > 60 ? '...' : ''}
                    <br>
                    <small>Your answer: ${userAnswer} | Status: ${isCorrect ? 'Correct ✓' : 'Wrong ✗'}</small>
                </div>
                <div>
                    <i class="fas fa-${isCorrect ? 'check' : 'times'}" style="color: ${isCorrect ? '#10b981' : '#ef4444'}"></i>
                </div>
            `;
            
            resultsList.appendChild(resultItem);
        });
    }
}

function restartQuiz() {
    // Reset all variables
    currentQuiz = null;
    currentQuestionIndex = 0;
    userAnswers = {};
    quizData = null;
    
    // Reset form
    textInput.value = '';
    numQuestions.value = '5';
    difficulty.value = 'medium';
    questionType.value = 'mixed';
    
    // Update character count and show input section
    updateCharCount();
    showSection('input');
}

async function exportQuiz() {
    if (!currentQuiz) {
        alert('No quiz to export');
        return;
    }
    
    try {
        const response = await fetch(`/api/export-quiz/${currentQuiz.id}`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = `quiz_${currentQuiz.id}.txt`;
        
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
    } catch (error) {
        console.error('Error exporting quiz:', error);
        alert('Failed to export quiz. Please try again.');
    }
}

function showSection(sectionName) {
    // Hide all sections
    document.querySelectorAll('.section').forEach(section => {
        section.classList.remove('active');
    });
    
    // Show target section
    const targetSection = document.getElementById(`${sectionName}-section`);
    if (targetSection) {
        targetSection.classList.add('active');
    }
}

function updateLoadingMessage(title, description) {
    if (loadingTitle && loadingDescription) {
        loadingTitle.textContent = title;
        loadingDescription.textContent = description;
    }
}

// Utility function to show loading state
function showLoading(message = 'Loading...') {
    const loadingContainer = document.querySelector('.loading-container h2');
    if (loadingContainer) {
        loadingContainer.textContent = message;
    }
}