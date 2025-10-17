import React, { useState, useEffect } from 'react';
import { 
  Activity, 
  TrendingUp, 
  Database, 
  Clock, 
  CheckCircle, 
  AlertCircle,
  RefreshCw,
  Play,
  BarChart3,
  Brain
} from 'lucide-react';

function Admin() {
  const [schedulerStatus, setSchedulerStatus] = useState(null);
  const [learningHistory, setLearningHistory] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [triggeringCycle, setTriggeringCycle] = useState(false);

  useEffect(() => {
    loadAllData();
    // Auto-refresh every 30 seconds
    const interval = setInterval(loadAllData, 30000);
    return () => clearInterval(interval);
  }, []);

  const loadAllData = async () => {
    await Promise.all([
      loadSchedulerStatus(),
      loadLearningHistory(),
      loadMetrics()
    ]);
  };

  const loadSchedulerStatus = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/learning/status');
      const data = await response.json();
      setSchedulerStatus(data);
      setError(null);
    } catch (err) {
      console.error('Error loading scheduler status:', err);
      setError('Failed to load scheduler status');
    }
  };

  const loadLearningHistory = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/learning/history?limit=10');
      const data = await response.json();
      setLearningHistory(data.cycles || []);
    } catch (err) {
      console.error('Error loading learning history:', err);
    }
  };

  const loadMetrics = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/learning/metrics');
      const data = await response.json();
      setMetrics(data.metrics);
    } catch (err) {
      console.error('Error loading metrics:', err);
    }
  };

  const handleManualTrigger = async () => {
    if (!window.confirm('Trigger a learning cycle now? This will analyze recent feedback and optimize the system.')) {
      return;
    }

    setTriggeringCycle(true);
    try {
      const response = await fetch('http://localhost:8000/api/v1/learning/cycle', {
        method: 'POST'
      });
      const data = await response.json();
      
      if (data.success) {
        alert('✅ Learning cycle completed successfully!');
        loadAllData();
      } else {
        alert('❌ Learning cycle failed: ' + (data.error || 'Unknown error'));
      }
    } catch (err) {
      alert('❌ Failed to trigger learning cycle: ' + err.message);
    } finally {
      setTriggeringCycle(false);
    }
  };

  const handleRefresh = () => {
    setLoading(true);
    loadAllData().finally(() => setLoading(false));
  };

  return (
    <div className="max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-3">
          <Brain className="w-8 h-8 text-purple-600" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Learning System Admin</h1>
            <p className="text-gray-600">Monitor the Human-in-the-Loop learning system</p>
          </div>
        </div>
        <button
          onClick={handleRefresh}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-3">
          <AlertCircle className="w-5 h-5 text-red-600" />
          <span className="text-red-800">{error}</span>
        </div>
      )}

      {/* Scheduler Status Card */}
      <div className="bg-white rounded-lg shadow-md p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <Activity className="w-6 h-6 text-green-600" />
            <h2 className="text-xl font-semibold">Scheduler Status</h2>
          </div>
          {schedulerStatus?.scheduler?.is_running && (
            <span className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm font-medium">
              Running
            </span>
          )}
        </div>

        {schedulerStatus ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 bg-gray-50 rounded-lg">
              <div className="text-sm text-gray-600 mb-1">Feedback Collected</div>
              <div className="text-2xl font-bold text-gray-900">
                {schedulerStatus.feedback_count_since_last_cycle || 0}
                <span className="text-sm font-normal text-gray-500"> / 100</span>
              </div>
              <div className="mt-2 h-2 bg-gray-200 rounded-full overflow-hidden">
                <div 
                  className="h-full bg-blue-600 transition-all"
                  style={{ width: `${Math.min((schedulerStatus.feedback_count_since_last_cycle || 0), 100)}%` }}
                />
              </div>
            </div>

            <div className="p-4 bg-gray-50 rounded-lg">
              <div className="text-sm text-gray-600 mb-1">Last Cycle</div>
              <div className="text-lg font-semibold text-gray-900">
                {schedulerStatus.scheduler?.last_cycle 
                  ? new Date(schedulerStatus.scheduler.last_cycle).toLocaleString()
                  : 'Never'}
              </div>
            </div>

            <div className="p-4 bg-gray-50 rounded-lg">
              <div className="text-sm text-gray-600 mb-1">Active Jobs</div>
              <div className="text-2xl font-bold text-gray-900">
                {schedulerStatus.scheduler?.active_jobs?.length || 0}
              </div>
              <div className="text-xs text-gray-500 mt-1">
                {schedulerStatus.scheduler?.active_jobs?.map(job => job.name).join(', ')}
              </div>
            </div>
          </div>
        ) : (
          <div className="text-gray-500 text-center py-8">Loading scheduler status...</div>
        )}

        <div className="mt-4 pt-4 border-t">
          <button
            onClick={handleManualTrigger}
            disabled={triggeringCycle}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Play className={`w-4 h-4 ${triggeringCycle ? 'animate-pulse' : ''}`} />
            {triggeringCycle ? 'Running Learning Cycle...' : 'Trigger Learning Cycle Now'}
          </button>
        </div>
      </div>

      {/* Metrics Card */}
      {metrics && (
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <div className="flex items-center gap-3 mb-4">
            <TrendingUp className="w-6 h-6 text-blue-600" />
            <h2 className="text-xl font-semibold">System Improvement Metrics</h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 bg-blue-50 rounded-lg">
              <div className="text-sm text-gray-600 mb-1">Total Learning Cycles</div>
              <div className="text-3xl font-bold text-blue-900">{metrics.total_cycles || 0}</div>
            </div>

            <div className="p-4 bg-green-50 rounded-lg">
              <div className="text-sm text-gray-600 mb-1">Average Rating</div>
              <div className="text-3xl font-bold text-green-900">
                {metrics.average_rating?.latest?.toFixed(2) || 'N/A'}
              </div>
              <div className="text-xs text-gray-600 mt-1">
                First: {metrics.average_rating?.first?.toFixed(2) || 'N/A'}
                {metrics.average_rating?.latest > metrics.average_rating?.first && (
                  <span className="ml-1 text-green-600">↑</span>
                )}
              </div>
            </div>

            <div className="p-4 bg-purple-50 rounded-lg">
              <div className="text-sm text-gray-600 mb-1">Accuracy Rate</div>
              <div className="text-3xl font-bold text-purple-900">
                {metrics.accuracy_rate?.latest 
                  ? `${(metrics.accuracy_rate.latest * 100).toFixed(1)}%` 
                  : 'N/A'}
              </div>
              <div className="text-xs text-gray-600 mt-1">
                First: {metrics.accuracy_rate?.first 
                  ? `${(metrics.accuracy_rate.first * 100).toFixed(1)}%` 
                  : 'N/A'}
                {metrics.accuracy_rate?.latest > metrics.accuracy_rate?.first && (
                  <span className="ml-1 text-purple-600">↑</span>
                )}
              </div>
            </div>
          </div>

          {/* Trend Chart */}
          {metrics.average_rating?.trend && (
            <div className="mt-6">
              <div className="text-sm font-medium text-gray-700 mb-3">Rating Trend</div>
              <div className="flex items-end gap-2 h-24">
                {metrics.average_rating.trend.map((value, index) => (
                  <div key={index} className="flex-1 flex flex-col items-center">
                    <div 
                      className="w-full bg-blue-500 rounded-t transition-all hover:bg-blue-600"
                      style={{ height: `${(value / 5) * 100}%` }}
                      title={`Cycle ${index + 1}: ${value.toFixed(2)}`}
                    />
                    <div className="text-xs text-gray-500 mt-1">{index + 1}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Learning History */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="flex items-center gap-3 mb-4">
          <Clock className="w-6 h-6 text-orange-600" />
          <h2 className="text-xl font-semibold">Learning Cycle History</h2>
        </div>

        {learningHistory.length > 0 ? (
          <div className="space-y-3">
            {learningHistory.map((cycle, index) => (
              <div 
                key={cycle.id || index}
                className="p-4 border border-gray-200 rounded-lg hover:border-blue-300 transition-colors"
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-3">
                    {cycle.optimization_success ? (
                      <CheckCircle className="w-5 h-5 text-green-600" />
                    ) : (
                      <AlertCircle className="w-5 h-5 text-yellow-600" />
                    )}
                    <div>
                      <div className="font-semibold text-gray-900">
                        {cycle.trigger_type === 'daily_scheduled' && '🌙 Daily Scheduled'}
                        {cycle.trigger_type === 'feedback_count_100' && '📊 Feedback Threshold'}
                        {cycle.trigger_type === 'manual' && '🔧 Manual Trigger'}
                      </div>
                      <div className="text-sm text-gray-500">
                        {new Date(cycle.completed_at).toLocaleString()}
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-sm text-gray-600">
                      {cycle.feedback_count} feedback items
                    </div>
                    <div className="text-xs text-gray-500">
                      Avg Rating: {cycle.average_rating?.toFixed(2) || 'N/A'}
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-4 gap-3 mt-3 pt-3 border-t border-gray-100">
                  <div className="text-center">
                    <div className="text-xs text-gray-600">Accuracy</div>
                    <div className="font-semibold text-sm">
                      {cycle.accuracy_rate 
                        ? `${(cycle.accuracy_rate * 100).toFixed(0)}%` 
                        : 'N/A'}
                    </div>
                  </div>
                  <div className="text-center">
                    <div className="text-xs text-gray-600">Suggestions</div>
                    <div className="font-semibold text-sm">{cycle.suggestions_count || 0}</div>
                  </div>
                  <div className="text-center">
                    <div className="text-xs text-gray-600">Training Examples</div>
                    <div className="font-semibold text-sm">{cycle.training_examples || 0}</div>
                  </div>
                  <div className="text-center">
                    <div className="text-xs text-gray-600">Optimization</div>
                    <div className={`font-semibold text-sm ${
                      cycle.optimization_success ? 'text-green-600' : 'text-yellow-600'
                    }`}>
                      {cycle.optimization_success ? '✓ Success' : '- Skipped'}
                    </div>
                  </div>
                </div>

                {cycle.optimization_score && (
                  <div className="mt-2 text-xs text-gray-500">
                    Optimization Score: {(cycle.optimization_score * 100).toFixed(1)}%
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-12 text-gray-500">
            <Database className="w-12 h-12 mx-auto mb-3 text-gray-300" />
            <p>No learning cycles have run yet.</p>
            <p className="text-sm mt-1">Trigger one manually or wait for automatic execution.</p>
          </div>
        )}
      </div>

      {/* Tips Section */}
      <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
        <h3 className="font-semibold text-blue-900 mb-2">💡 How the Learning System Works</h3>
        <ul className="text-sm text-blue-800 space-y-1">
          <li>• <strong>Daily at 2 AM:</strong> Automatic learning cycle runs to optimize the system</li>
          <li>• <strong>Every 100 feedback:</strong> Automatic trigger when feedback threshold is reached</li>
          <li>• <strong>Manual trigger:</strong> Click the button above to run a cycle immediately</li>
          <li>• <strong>Low ratings (≤2):</strong> Immediately analyzed and stored for review</li>
          <li>• <strong>High ratings (≥4):</strong> Used as training examples for DSPy optimization</li>
        </ul>
      </div>
    </div>
  );
}

export default Admin;
