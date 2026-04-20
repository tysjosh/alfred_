import { useState } from 'react';
import axios from 'axios';
import InputPanel from './components/InputPanel';
import DecisionPanel from './components/DecisionPanel';
import DebugPanel from './components/DebugPanel';
import SettingsPanel from './components/SettingsPanel';
import type { DecideRequest, DecideResponse } from './types';
import './App.css';

function App() {
  const [result, setResult] = useState<DecideResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [apiKey, setApiKey] = useState(() => localStorage.getItem('openai_api_key') || '');
  const [model, setModel] = useState(() => localStorage.getItem('openai_model') || 'gpt-4o-mini');

  const handleApiKeyChange = (key: string) => {
    setApiKey(key);
    if (key) localStorage.setItem('openai_api_key', key);
    else localStorage.removeItem('openai_api_key');
  };

  const handleModelChange = (m: string) => {
    setModel(m);
    localStorage.setItem('openai_model', m);
  };

  const handleSubmit = async (request: DecideRequest): Promise<void> => {
    setError(null);
    setResult(null);
    setLoading(true);
    try {
      const payload: DecideRequest = {
        ...request,
        openai_api_key: apiKey || null,
        openai_model: model || null,
      };
      const response = await axios.post<DecideResponse>(
        '/api/decide',
        payload,
      );
      setResult(response.data);
    } catch (err: unknown) {
      if (axios.isAxiosError(err)) {
        const detail = err.response?.data?.detail;
        setError(typeof detail === 'string' ? detail : err.message);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('An unexpected error occurred');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1><span>CADE</span> — Contextual Action Decision Engine</h1>
        <p className="app-subtitle">Hybrid rule-based + LLM reasoning for safe action execution</p>
      </header>
      <main className="app-layout">
        <div className="app-left">
          <SettingsPanel
            apiKey={apiKey}
            model={model}
            onApiKeyChange={handleApiKeyChange}
            onModelChange={handleModelChange}
          />
          <InputPanel onSubmit={handleSubmit} error={error} loading={loading} />
        </div>
        <div className="app-right">
          <DecisionPanel result={result} loading={loading} />
          <DebugPanel result={result} />
        </div>
      </main>
    </div>
  );
}

export default App;
