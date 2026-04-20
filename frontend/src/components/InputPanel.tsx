import { useState } from 'react';
import type { DecideRequest, ConversationTurn } from '../types';
import scenarios from '../scenarios';

const ACTION_TYPES = [
  'email_external',
  'financial_transfer',
  'schedule_meeting',
  'delete_permanent',
  'reminder_self',
  'calendar_event',
];

const ACTION_LABELS: Record<string, string> = {
  email_external: '📧 Email External',
  financial_transfer: '💸 Financial Transfer',
  schedule_meeting: '📅 Schedule Meeting',
  delete_permanent: '🗑️ Delete Permanent',
  reminder_self: '🔔 Self Reminder',
  calendar_event: '📆 Calendar Event',
};

interface InputPanelProps {
  onSubmit: (request: DecideRequest) => Promise<void>;
  error: string | null;
  loading: boolean;
}

interface HistoryEntry {
  role: 'user' | 'assistant';
  content: string;
}

const InputPanel: React.FC<InputPanelProps> = ({ onSubmit, error, loading }) => {
  const [description, setDescription] = useState('');
  const [actionType, setActionType] = useState(ACTION_TYPES[0]);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [newRole, setNewRole] = useState<'user' | 'assistant'>('user');
  const [newContent, setNewContent] = useState('');
  const [selectedScenario, setSelectedScenario] = useState('');
  const [actionParams, setActionParams] = useState<Record<string, unknown>>({});

  const handleScenarioChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const idx = e.target.value;
    setSelectedScenario(idx);
    if (idx === '') return;
    const scenario = scenarios[Number(idx)];
    setActionType(scenario.action.type);
    setDescription(scenario.action.description);
    setActionParams(scenario.action.parameters);
    setHistory(
      scenario.conversationHistory.map((turn) => ({
        role: turn.role as 'user' | 'assistant',
        content: turn.content,
      }))
    );
  };

  const addTurn = () => {
    const trimmed = newContent.trim();
    if (!trimmed) return;
    setHistory((prev) => [...prev, { role: newRole, content: trimmed }]);
    setNewContent('');
  };

  const removeTurn = (index: number) => {
    setHistory((prev) => prev.filter((_, i) => i !== index));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const conversationHistory: ConversationTurn[] = history.map((entry) => ({
      role: entry.role,
      content: entry.content,
      timestamp: new Date().toISOString(),
    }));
    const request: DecideRequest = {
      action: { type: actionType, description, parameters: actionParams },
      conversation_history: conversationHistory,
    };
    await onSubmit(request);
  };

  return (
    <form onSubmit={handleSubmit} className="card">
      <div className="card-title">Configure Action</div>

      {/* Scenario Selector */}
      <div className="form-group">
        <label className="form-label" htmlFor="scenario-select">Quick Load Scenario</label>
        <select
          id="scenario-select"
          value={selectedScenario}
          onChange={handleScenarioChange}
          className="form-select scenario-select"
        >
          <option value="">Choose a preset scenario…</option>
          {scenarios.map((s, idx) => (
            <option key={idx} value={idx}>
              {s.name}
            </option>
          ))}
        </select>
      </div>

      {/* Action Type */}
      <div className="form-group">
        <label className="form-label" htmlFor="action-type">Action Type</label>
        <select
          id="action-type"
          value={actionType}
          onChange={(e) => setActionType(e.target.value)}
          className="form-select"
        >
          {ACTION_TYPES.map((t) => (
            <option key={t} value={t}>{ACTION_LABELS[t] || t}</option>
          ))}
        </select>
      </div>

      {/* Action Description */}
      <div className="form-group">
        <label className="form-label" htmlFor="action-description">Description</label>
        <textarea
          id="action-description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="What should the action do?"
          rows={3}
          className="form-textarea"
          required
        />
      </div>

      {/* Conversation History */}
      <div className="history-section">
        <div className="history-label">Conversation History</div>

        {history.length === 0 ? (
          <div className="history-empty">No conversation turns yet</div>
        ) : (
          <div className="history-turns">
            {history.map((entry, idx) => (
              <div key={idx} className="history-turn">
                <span className={`history-role ${entry.role}`}>{entry.role}</span>
                <span className="history-content">{entry.content}</span>
                <button
                  type="button"
                  onClick={() => removeTurn(idx)}
                  className="history-remove"
                  aria-label={`Remove turn ${idx + 1}`}
                >✕</button>
              </div>
            ))}
          </div>
        )}

        <div className="history-add">
          <select
            value={newRole}
            onChange={(e) => setNewRole(e.target.value as 'user' | 'assistant')}
            className="form-select"
            aria-label="Role"
          >
            <option value="user">user</option>
            <option value="assistant">assistant</option>
          </select>
          <input
            type="text"
            value={newContent}
            onChange={(e) => setNewContent(e.target.value)}
            placeholder="Type a message…"
            className="form-input"
            aria-label="Message content"
            onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addTurn(); } }}
          />
          <button type="button" onClick={addTurn} className="btn-add-turn">+ Add</button>
        </div>
      </div>

      {/* Error */}
      {error && <div role="alert" className="error-alert">{error}</div>}

      {/* Submit */}
      <button
        type="submit"
        disabled={loading || !description.trim()}
        className={`btn-primary ${loading ? 'loading loading-pulse' : ''}`}
      >
        {loading ? 'Evaluating…' : 'Evaluate Action'}
      </button>
    </form>
  );
};

export default InputPanel;
