import React, { useState, useEffect } from 'react';
import { MessageSquare, ThumbsUp, ThumbsDown, TrendingUp, RefreshCw, AlertCircle, CheckCircle } from 'lucide-react';
import { getAllFeedback, getStatistics } from './api';
import './App.css';

function Feedback() {
  const [feedbackList, setFeedbackList] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalFeedback, setTotalFeedback] = useState(0);
  const itemsPerPage = 10;

  useEffect(() => {
    loadFeedback();
    loadStats();
  }, [currentPage]);

  const loadFeedback = async () => {
    setLoading(true);
    setError(null);
    try {
      const offset = (currentPage - 1) * itemsPerPage;
      const data = await getAllFeedback(itemsPerPage, offset);
      setFeedbackList(data.feedback || []);
      setTotalFeedback(data.total || 0);
    } catch (err) {
      setError(err.error || 'Failed to load feedback');
    } finally {
      setLoading(false);
    }
  };

  const loadStats = async () => {
    try {
      const data = await getStatistics();
      setStats(data.feedback_stats || null);
    } catch (err) {
      console.error('Failed to load stats:', err);
    }
  };

  const handleRefresh = () => {
    loadFeedback();
    loadStats();
  };

  const getRatingColor = (rating) => {
    if (rating >= 4) return 'text-green-600 bg-green-100';
    if (rating === 3) return 'text-yellow-600 bg-yellow-100';
    return 'text-red-600 bg-red-100';
  };

  const getRatingIcon = (rating) => {
    if (rating >= 4) return <ThumbsUp className="w-4 h-4" />;
    return <ThumbsDown className="w-4 h-4" />;
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleString();
  };

  const totalPages = Math.ceil(totalFeedback / itemsPerPage);

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Header */}
      <header className="bg-white shadow-sm mb-6">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <MessageSquare className="w-8 h-8 text-blue-600 mr-3" />
              <h1 className="text-2xl font-bold text-gray-900">Feedback Dashboard</h1>
            </div>
            <button
              onClick={handleRefresh}
              className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              <RefreshCw className="w-4 h-4 mr-2" />
              Refresh
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Statistics Cards */}
        {stats && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
            <div className="bg-white rounded-lg shadow-md p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Total Feedback</p>
                  <p className="text-3xl font-bold text-gray-900 mt-2">{stats.total_feedback || 0}</p>
                </div>
                <MessageSquare className="w-12 h-12 text-blue-600 opacity-20" />
              </div>
            </div>

            <div className="bg-white rounded-lg shadow-md p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Average Rating</p>
                  <p className="text-3xl font-bold text-gray-900 mt-2">
                    {stats.average_rating ? stats.average_rating.toFixed(1) : '0.0'}/5
                  </p>
                </div>
                <TrendingUp className="w-12 h-12 text-green-600 opacity-20" />
              </div>
            </div>

            <div className="bg-white rounded-lg shadow-md p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Accuracy Rate</p>
                  <p className="text-3xl font-bold text-gray-900 mt-2">
                    {stats.accuracy_rate ? (stats.accuracy_rate * 100).toFixed(0) : '0'}%
                  </p>
                </div>
                <CheckCircle className="w-12 h-12 text-green-600 opacity-20" />
              </div>
            </div>
          </div>
        )}

        {/* Rating Distribution */}
        {stats && stats.feedback_by_rating && (
          <div className="bg-white rounded-lg shadow-md p-6 mb-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Rating Distribution</h3>
            <div className="space-y-3">
              {[5, 4, 3, 2, 1].map((rating) => {
                const count = stats.feedback_by_rating[rating] || 0;
                const percentage = stats.total_feedback > 0 
                  ? (count / stats.total_feedback * 100).toFixed(0) 
                  : 0;
                return (
                  <div key={rating} className="flex items-center">
                    <span className="text-sm font-medium text-gray-600 w-12">{rating} ★</span>
                    <div className="flex-1 bg-gray-200 rounded-full h-4 mx-4">
                      <div
                        className={`h-4 rounded-full ${
                          rating >= 4 ? 'bg-green-500' : rating === 3 ? 'bg-yellow-500' : 'bg-red-500'
                        }`}
                        style={{ width: `${percentage}%` }}
                      ></div>
                    </div>
                    <span className="text-sm font-medium text-gray-600 w-16 text-right">
                      {count} ({percentage}%)
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Error Display */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
            <div className="flex items-center">
              <AlertCircle className="w-5 h-5 text-red-600 mr-2" />
              <p className="text-red-800">{error}</p>
            </div>
          </div>
        )}

        {/* Loading State */}
        {loading ? (
          <div className="bg-white rounded-lg shadow-md p-12 text-center">
            <RefreshCw className="w-12 h-12 text-blue-600 animate-spin mx-auto mb-4" />
            <p className="text-gray-600">Loading feedback...</p>
          </div>
        ) : (
          <>
            {/* Feedback List */}
            <div className="bg-white rounded-lg shadow-md overflow-hidden mb-6">
              <div className="px-6 py-4 border-b border-gray-200 bg-gray-50">
                <h2 className="text-lg font-semibold text-gray-900">Recent Feedback</h2>
                <p className="text-sm text-gray-600 mt-1">
                  Showing {((currentPage - 1) * itemsPerPage) + 1} to {Math.min(currentPage * itemsPerPage, totalFeedback)} of {totalFeedback} entries
                </p>
              </div>
              
              {feedbackList.length === 0 ? (
                <div className="p-12 text-center">
                  <MessageSquare className="w-16 h-16 text-gray-400 mx-auto mb-4" />
                  <p className="text-gray-600">No feedback available yet</p>
                  <p className="text-sm text-gray-500 mt-2">Feedback will appear here once users submit responses</p>
                </div>
              ) : (
                <div className="divide-y divide-gray-200">
                  {feedbackList.map((feedback) => (
                    <div key={feedback.id} className="p-6 hover:bg-gray-50 transition-colors">
                      {/* Feedback Header */}
                      <div className="flex items-start justify-between mb-4">
                        <div className="flex items-center space-x-3">
                          <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${getRatingColor(feedback.rating)}`}>
                            {getRatingIcon(feedback.rating)}
                            <span className="ml-2">{feedback.rating}/5</span>
                          </span>
                          {feedback.is_correct !== null && (
                            <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium ${
                              feedback.is_correct ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                            }`}>
                              {feedback.is_correct ? (
                                <>
                                  <CheckCircle className="w-3 h-3 mr-1" />
                                  Correct
                                </>
                              ) : (
                                <>
                                  <AlertCircle className="w-3 h-3 mr-1" />
                                  Incorrect
                                </>
                              )}
                            </span>
                          )}
                        </div>
                        <span className="text-sm text-gray-500">{formatDate(feedback.created_at)}</span>
                      </div>

                      {/* Question */}
                      <div className="mb-3">
                        <p className="text-sm font-medium text-gray-700 mb-1">Question:</p>
                        <p className="text-gray-900">{feedback.user_question}</p>
                      </div>

                      {/* Generated Answer */}
                      <div className="mb-3">
                        <p className="text-sm font-medium text-gray-700 mb-1">Generated Answer:</p>
                        <div className="bg-gray-50 rounded p-3">
                          <p className="text-gray-800 text-sm line-clamp-3">{feedback.generated_answer}</p>
                        </div>
                      </div>

                      {/* User Feedback */}
                      {feedback.user_feedback && (
                        <div className="mb-3">
                          <p className="text-sm font-medium text-gray-700 mb-1">User Comment:</p>
                          <p className="text-gray-700 text-sm italic bg-blue-50 rounded p-3">
                            "{feedback.user_feedback}"
                          </p>
                        </div>
                      )}

                      {/* Corrections */}
                      {feedback.corrections && Object.keys(feedback.corrections).length > 0 && (
                        <div>
                          <p className="text-sm font-medium text-gray-700 mb-1">Corrections:</p>
                          <div className="bg-yellow-50 rounded p-3">
                            <pre className="text-xs text-gray-800 whitespace-pre-wrap">
                              {JSON.stringify(feedback.corrections, null, 2)}
                            </pre>
                          </div>
                        </div>
                      )}

                      {/* Feedback ID */}
                      <div className="mt-3 pt-3 border-t border-gray-100">
                        <p className="text-xs text-gray-500">Feedback ID: {feedback.id}</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="bg-white rounded-lg shadow-md p-4">
                <div className="flex items-center justify-between">
                  <button
                    onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                    disabled={currentPage === 1}
                    className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    Previous
                  </button>
                  
                  <div className="flex items-center space-x-2">
                    {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                      let pageNum;
                      if (totalPages <= 5) {
                        pageNum = i + 1;
                      } else if (currentPage <= 3) {
                        pageNum = i + 1;
                      } else if (currentPage >= totalPages - 2) {
                        pageNum = totalPages - 4 + i;
                      } else {
                        pageNum = currentPage - 2 + i;
                      }
                      
                      return (
                        <button
                          key={pageNum}
                          onClick={() => setCurrentPage(pageNum)}
                          className={`w-10 h-10 rounded-lg font-medium transition-colors ${
                            currentPage === pageNum
                              ? 'bg-blue-600 text-white'
                              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                          }`}
                        >
                          {pageNum}
                        </button>
                      );
                    })}
                  </div>

                  <button
                    onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                    disabled={currentPage === totalPages}
                    className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}

export default Feedback;
