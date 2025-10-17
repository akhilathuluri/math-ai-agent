import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'https://math-ai-agent.onrender.com';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const askQuestion = async (question) => {
  try {
    const response = await api.post('/api/v1/ask', { question });
    return response.data;
  } catch (error) {
    throw error.response?.data || { error: 'Failed to get answer' };
  }
};

export const submitFeedback = async (feedbackData) => {
  try {
    const response = await api.post('/api/v1/feedback', feedbackData);
    return response.data;
  } catch (error) {
    throw error.response?.data || { error: 'Failed to submit feedback' };
  }
};

export const getStatistics = async () => {
  try {
    const response = await api.get('/api/v1/stats');
    return response.data;
  } catch (error) {
    throw error.response?.data || { error: 'Failed to get statistics' };
  }
};

export const searchKnowledgeBase = async (query, k = 5) => {
  try {
    const response = await api.get('/api/v1/knowledge-base/search', {
      params: { query, k },
    });
    return response.data;
  } catch (error) {
    throw error.response?.data || { error: 'Failed to search knowledge base' };
  }
};

export const getAllFeedback = async (limit = 100, offset = 0) => {
  try {
    const response = await api.get('/api/v1/feedback/all', {
      params: { limit, offset },
    });
    return response.data;
  } catch (error) {
    throw error.response?.data || { error: 'Failed to get feedback' };
  }
};

export default api;

