import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import { Brain, MessageSquare, Settings } from 'lucide-react';
import Home from './Home';
import Feedback from './Feedback';
import Admin from './Admin';
import './App.css';

function Navigation() {
  const location = useLocation();
  
  const isActive = (path) => {
    return location.pathname === path;
  };

  return (
    <header className="bg-white shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            <Brain className="w-8 h-8 text-blue-600 mr-3" />
            <h1 className="text-2xl font-bold text-gray-900">Math Agent</h1>
            <span className="ml-3 text-sm text-gray-500">AI-Powered Mathematical Assistant</span>
          </div>
          
          <nav className="flex space-x-4">
            <Link
              to="/"
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                isActive('/')
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-700 hover:bg-gray-100'
              }`}
            >
              <span className="flex items-center">
                <Brain className="w-4 h-4 mr-2" />
                Ask Question
              </span>
            </Link>
            <Link
              to="/feedback"
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                isActive('/feedback')
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-700 hover:bg-gray-100'
              }`}
            >
              <span className="flex items-center">
                <MessageSquare className="w-4 h-4 mr-2" />
                Feedback
              </span>
            </Link>
            <Link
              to="/admin"
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                isActive('/admin')
                  ? 'bg-purple-600 text-white'
                  : 'text-gray-700 hover:bg-gray-100'
              }`}
            >
              <span className="flex items-center">
                <Settings className="w-4 h-4 mr-2" />
                Admin
              </span>
            </Link>
          </nav>
        </div>
      </div>
    </header>
  );
}

function App() {
  return (
    <Router>
      <div className="min-h-screen flex flex-col">
        <Navigation />
        
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/feedback" element={<Feedback />} />
          <Route path="/admin" element={<Admin />} />
        </Routes>

        {/* Footer */}
        <footer className="bg-white border-t mt-auto">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
            <p className="text-center text-sm text-gray-500">
              Math Agent - Powered by LangGraph, Supabase, Tavily & DSPy
            </p>
          </div>
        </footer>
      </div>
    </Router>
  );
}

export default App;
