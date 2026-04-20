import { useState } from 'react';

const MODELS = [
  { value: 'gpt-4o-mini', label: 'GPT-4o Mini' },
  { value: 'gpt-4o', label: 'GPT-4o' },
  { value: 'gpt-4-turbo', label: 'GPT-4 Turbo' },
  { value: 'gpt-3.5-turbo', label: 'GPT-3.5 Turbo' },
  { value: 'o3-mini', label: 'o3-mini' },
];

interface SettingsPanelProps {
  apiKey: string;
  model: string;
  onApiKeyChange: (key: string) => void;
  onModelChange: (model: string) => void;
}

const SettingsPanel: React.FC<SettingsPanelProps> = ({
  apiKey,
  model,
  onApiKeyChange,
  onModelChange,
}) => {
  const [open, setOpen] = useState(!apiKey);
  const [showKey, setShowKey] = useState(false);

  return (
    <div className="card settings-card" style={{ marginBottom: 16 }}>
      <button
        type="button"
        className="settings-toggle"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
      >
        <span className="settings-toggle-left">
          <span className="settings-icon">⚙️</span>
          <span className="settings-toggle-title">LLM Settings</span>
          {!open && apiKey && (
            <span className="settings-status connected">Connected</span>
          )}
          {!open && !apiKey && (
            <span className="settings-status disconnected">No API Key</span>
          )}
        </span>
        <span className={`settings-chevron ${open ? 'open' : ''}`}>▸</span>
      </button>

      {open && (
        <div className="settings-body animate-in">
          {/* API Key */}
          <div className="form-group">
            <label className="form-label" htmlFor="api-key">OpenAI API Key</label>
            <div className="api-key-row">
              <input
                id="api-key"
                type={showKey ? 'text' : 'password'}
                value={apiKey}
                onChange={(e) => onApiKeyChange(e.target.value)}
                placeholder="sk-..."
                className="form-input"
                autoComplete="off"
                spellCheck={false}
              />
              <button
                type="button"
                className="btn-toggle-vis"
                onClick={() => setShowKey(!showKey)}
                aria-label={showKey ? 'Hide API key' : 'Show API key'}
              >
                {showKey ? '🙈' : '👁️'}
              </button>
            </div>
            <span className="form-hint">
              Stored in browser localStorage. Never sent to our servers — only to OpenAI directly via the backend.
            </span>
          </div>

          {/* Model */}
          <div className="form-group">
            <label className="form-label" htmlFor="model-select">Model</label>
            <select
              id="model-select"
              value={model}
              onChange={(e) => onModelChange(e.target.value)}
              className="form-select"
            >
              {MODELS.map((m) => (
                <option key={m.value} value={m.value}>{m.label}</option>
              ))}
            </select>
          </div>
        </div>
      )}
    </div>
  );
};

export default SettingsPanel;
