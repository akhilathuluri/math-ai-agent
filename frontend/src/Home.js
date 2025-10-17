import React, { useState } from 'react';
import { Send, Loader, Brain, Search, Database } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';
import { askQuestion, submitFeedback } from './api';
import './App.css';

// Function to convert parentheses-wrapped LaTeX to proper delimiters
const sanitizeLaTeX = (text) => {
  if (!text) return text;
  
  // First, protect actual function calls and regular parentheses by temporarily replacing them
  // We'll look for LaTeX-specific patterns
  
  // Convert display math: [ ... ] to $$ ... $$
  text = text.replace(/\\\[\s*/g, '\n$$\n');
  text = text.replace(/\s*\\\]/g, '\n$$\n');
  
  // Convert inline math with backslash-paren: \( ... \) to $ ... $
  text = text.replace(/\\\(\s*/g, '$');
  text = text.replace(/\s*\\\)/g, '$');
  
  // Also handle cases where parentheses wrap LaTeX commands
  // Look for (P(...)) pattern where P is followed by backslash or math symbols
  text = text.replace(/\(([A-Z])\\([a-z]+)\{([^}]+)\}\)/g, '$$1\\$2{$3}$');
  
  // Handle standalone (P(x)) style notation - convert to $P(x)$
  text = text.replace(/\(([A-Z])\(([^)]+)\)\)/g, '$$1($2)$');
  
  // Handle other math expressions in parentheses with LaTeX commands
  text = text.replace(/\(([^()]*\\[a-zA-Z]+[^()]*)\)/g, '$$1$');
  
  return text;
};

function Home() {
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState(null);
  const [error, setError] = useState(null);
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(false);
  const [showDetailedFeedback, setShowDetailedFeedback] = useState(false);
  const [selectedRating, setSelectedRating] = useState(0);
  const [userComment, setUserComment] = useState('');
  const [correctAnswer, setCorrectAnswer] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!question.trim()) {
      return;
    }

    setLoading(true);
    setError(null);
    setResponse(null);
    setFeedbackSubmitted(false);

    try {
      const data = await askQuestion(question);
      setResponse(data);
    } catch (err) {
      setError(err.error || 'An error occurred while processing your question');
    } finally {
      setLoading(false);
    }
  };

  const handleFeedback = async (rating, isCorrect, userFeedback = '', corrections = '') => {
    if (!response) return;

    try {
      const feedbackData = {
        question: response.question,
        answer: response.answer,
        rating: rating,
        is_correct: isCorrect,
        user_feedback: userFeedback,
      };

      // Add corrections if provided
      if (corrections && corrections.trim()) {
        feedbackData.corrections = {
          correct_answer: corrections.trim()
        };
      }

      await submitFeedback(feedbackData);
      setFeedbackSubmitted(true);
      setShowDetailedFeedback(false);
      setSelectedRating(0);
      setUserComment('');
      setCorrectAnswer('');
    } catch (err) {
      console.error('Failed to submit feedback:', err);
      alert('Failed to submit feedback. Please try again.');
    }
  };

  const handleQuickFeedback = (rating, isCorrect) => {
    if (rating <= 2) {
      // For low ratings, show detailed feedback form
      setSelectedRating(rating);
      setShowDetailedFeedback(true);
    } else {
      // For high ratings, submit immediately
      handleFeedback(rating, isCorrect);
    }
  };

  const handleDetailedFeedbackSubmit = () => {
    const isCorrect = selectedRating >= 4;
    handleFeedback(selectedRating, isCorrect, userComment, correctAnswer);
  };

  const getRoutingIcon = (decision) => {
    switch (decision) {
      case 'knowledge_base':
        return <Database className="w-4 h-4" />;
      case 'web_search':
        return <Search className="w-4 h-4" />;
      default:
        return <Brain className="w-4 h-4" />;
    }
  };

  const getRoutingColor = (decision) => {
    switch (decision) {
      case 'knowledge_base':
        return 'bg-green-100 text-green-800';
      case 'web_search':
        return 'bg-blue-100 text-blue-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Main Content */}
      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Info Card */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-2">
            How it works
          </h2>
          <ul className="text-sm text-gray-600 space-y-1">
            <li>• Ask any mathematical question (algebra, calculus, geometry, etc.)</li>
            <li>• Get step-by-step solutions with explanations</li>
            <li>• Provide feedback to help the system improve</li>
            <li>• Questions are routed intelligently between knowledge base and web search</li>
          </ul>
        </div>

        {/* Question Input Form */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <form onSubmit={handleSubmit}>
            <label htmlFor="question" className="block text-sm font-medium text-gray-700 mb-2">
              Ask a Mathematical Question
            </label>
            <div className="relative">
              <textarea
                id="question"
                rows="4"
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                placeholder="e.g., Solve the equation: 2x + 5 = 13"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                disabled={loading}
              />
            </div>
            <div className="mt-4 flex justify-between items-center">
              <p className="text-xs text-gray-500">
                {question.length}/500 characters
              </p>
              <button
                type="submit"
                disabled={loading || !question.trim()}
                className="inline-flex items-center px-6 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {loading ? (
                  <>
                    <Loader className="animate-spin w-5 h-5 mr-2" />
                    Processing...
                  </>
                ) : (
                  <>
                    <Send className="w-5 h-5 mr-2" />
                    Get Solution
                  </>
                )}
              </button>
            </div>
          </form>
        </div>

        {/* Error Display */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6 fade-in">
            <p className="text-red-800">{error}</p>
          </div>
        )}

        {/* Response Display */}
        {response && (
          <div className="bg-white rounded-lg shadow-md p-6 mb-6 fade-in">
            {/* Metadata */}
            <div className="flex items-center justify-between mb-4 pb-4 border-b">
              <div className="flex items-center space-x-4">
                <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium ${getRoutingColor(response.routing_decision)}`}>
                  {getRoutingIcon(response.routing_decision)}
                  <span className="ml-2">{response.routing_decision.replace('_', ' ')}</span>
                </span>
                <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
                  {response.topic}
                </span>
                {response.mcp_used && (
                  <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                    <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    MCP Used
                  </span>
                )}
              </div>
              <div className="text-sm text-gray-600">
                Confidence: {(response.confidence_score * 100).toFixed(0)}%
              </div>
            </div>

            {/* Answer */}
            <div className="math-content prose max-w-none">
              <ReactMarkdown 
                remarkPlugins={[remarkMath]}
                rehypePlugins={[rehypeKatex]}
              >
                {sanitizeLaTeX(response.answer)}
              </ReactMarkdown>
            </div>

            {/* Sources */}
            {response.sources && response.sources.length > 0 && (
              <div className="mt-6 pt-4 border-t">
                <h3 className="text-sm font-semibold text-gray-700 mb-2">
                  Sources {response.mcp_used && <span className="text-green-600">(via MCP)</span>}:
                </h3>
                <ul className="text-sm text-gray-600 space-y-1">
                  {response.sources.map((source, idx) => {
                    const isMCP = source.includes('[MCP]');
                    const cleanSource = source.replace('[MCP] ', '');
                    return (
                      <li key={idx} className={isMCP ? 'flex items-center' : ''}>
                        {isMCP && (
                          <span className="inline-block w-2 h-2 bg-green-500 rounded-full mr-2"></span>
                        )}
                        {cleanSource.startsWith('http') ? (
                          <a href={cleanSource} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
                            {cleanSource}
                          </a>
                        ) : (
                          cleanSource
                        )}
                      </li>
                    );
                  })}
                </ul>
              </div>
            )}

            {/* Feedback Section */}
            <div className="mt-6 pt-4 border-t">
              <h3 className="text-sm font-semibold text-gray-700 mb-3">
                Was this answer helpful?
              </h3>
              {!feedbackSubmitted ? (
                <>
                  {!showDetailedFeedback ? (
                    /* Quick Feedback Buttons */
                    <div className="space-y-3">
                      <div className="flex flex-wrap gap-2">
                        <button
                          onClick={() => handleQuickFeedback(5, true)}
                          className="px-4 py-2 bg-green-100 text-green-800 rounded-lg hover:bg-green-200 transition-colors text-sm font-medium flex items-center"
                        >
                          <span className="mr-2">⭐⭐⭐⭐⭐</span>
                          Perfect!
                        </button>
                        <button
                          onClick={() => handleQuickFeedback(4, true)}
                          className="px-4 py-2 bg-green-50 text-green-700 rounded-lg hover:bg-green-100 transition-colors text-sm font-medium flex items-center"
                        >
                          <span className="mr-2">⭐⭐⭐⭐</span>
                          Good
                        </button>
                        <button
                          onClick={() => handleQuickFeedback(3, true)}
                          className="px-4 py-2 bg-yellow-100 text-yellow-800 rounded-lg hover:bg-yellow-200 transition-colors text-sm font-medium flex items-center"
                        >
                          <span className="mr-2">⭐⭐⭐</span>
                          Okay
                        </button>
                        <button
                          onClick={() => handleQuickFeedback(2, false)}
                          className="px-4 py-2 bg-orange-100 text-orange-800 rounded-lg hover:bg-orange-200 transition-colors text-sm font-medium flex items-center"
                        >
                          <span className="mr-2">⭐⭐</span>
                          Poor
                        </button>
                        <button
                          onClick={() => handleQuickFeedback(1, false)}
                          className="px-4 py-2 bg-red-100 text-red-800 rounded-lg hover:bg-red-200 transition-colors text-sm font-medium flex items-center"
                        >
                          <span className="mr-2">⭐</span>
                          Wrong
                        </button>
                      </div>
                      <p className="text-xs text-gray-500 mt-2">
                        💡 Ratings of 1-2 will prompt you to provide the correct answer to help improve the system
                      </p>
                    </div>
                  ) : (
                    /* Detailed Feedback Form */
                    <div className="space-y-4 bg-gray-50 p-4 rounded-lg">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Your Rating: {selectedRating} / 5 stars
                        </label>
                        <div className="flex gap-1">
                          {[1, 2, 3, 4, 5].map((star) => (
                            <button
                              key={star}
                              onClick={() => setSelectedRating(star)}
                              className={`text-2xl transition-colors ${
                                star <= selectedRating ? 'text-yellow-400' : 'text-gray-300'
                              }`}
                            >
                              ⭐
                            </button>
                          ))}
                        </div>
                      </div>

                      <div>
                        <label htmlFor="userComment" className="block text-sm font-medium text-gray-700 mb-2">
                          What was wrong or could be improved? (Optional)
                        </label>
                        <textarea
                          id="userComment"
                          rows="3"
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none text-sm"
                          placeholder="e.g., The explanation was unclear, steps were missing, wrong formula used..."
                          value={userComment}
                          onChange={(e) => setUserComment(e.target.value)}
                        />
                      </div>

                      {selectedRating <= 2 && (
                        <div>
                          <label htmlFor="correctAnswer" className="block text-sm font-medium text-red-700 mb-2">
                            What is the correct answer? (Helps AI learn) ⭐
                          </label>
                          <textarea
                            id="correctAnswer"
                            rows="3"
                            className="w-full px-3 py-2 border border-red-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent resize-none text-sm bg-red-50"
                            placeholder="Provide the correct solution or answer here..."
                            value={correctAnswer}
                            onChange={(e) => setCorrectAnswer(e.target.value)}
                          />
                          <p className="text-xs text-red-600 mt-1">
                            ✨ This correction will be used to train the AI and improve future responses!
                          </p>
                        </div>
                      )}

                      <div className="flex gap-2 pt-2">
                        <button
                          onClick={handleDetailedFeedbackSubmit}
                          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
                        >
                          Submit Feedback
                        </button>
                        <button
                          onClick={() => {
                            setShowDetailedFeedback(false);
                            setSelectedRating(0);
                            setUserComment('');
                            setCorrectAnswer('');
                          }}
                          className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors text-sm font-medium"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                  <p className="text-green-800 text-sm font-medium flex items-center">
                    <span className="text-xl mr-2">✅</span>
                    Thank you for your feedback! It helps improve the system.
                  </p>
                  <p className="text-green-700 text-xs mt-1">
                    Your input will be used in the next learning cycle to make the AI smarter.
                  </p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Example Questions */}
        {!response && !loading && (
          <div className="bg-white rounded-lg shadow-md p-6">
            <h3 className="text-md font-semibold text-gray-900 mb-3">
              Example Questions
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {[
                'Solve: x² + 5x + 6 = 0',
                'What is the derivative of 3x² + 2x?',
                'Find the area of a circle with radius 7',
                'Explain the Pythagorean theorem',
              ].map((example, idx) => (
                <button
                  key={idx}
                  onClick={() => setQuestion(example)}
                  className="text-left px-4 py-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors text-sm text-gray-700"
                >
                  {example}
                </button>
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default Home;
