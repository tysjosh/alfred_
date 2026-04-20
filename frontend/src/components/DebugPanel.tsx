import type { DecideResponse } from '../types';

interface DebugPanelProps {
  result: DecideResponse | null;
}

const BoolBadge: React.FC<{ value: boolean }> = ({ value }) => (
  <span className={`signal-badge ${value ? 'true' : 'false'}`}>
    {value ? 'true' : 'false'}
  </span>
);

const DebugPanel: React.FC<DebugPanelProps> = ({ result }) => {
  if (!result) {
    return (
      <div className="card">
        <div className="card-title">Debug View</div>
        <div className="placeholder-state">
          <div className="placeholder-icon">🔍</div>
          <div className="placeholder-text">Signal data will appear here</div>
        </div>
      </div>
    );
  }

  const { deterministic: det, llm } = result.signals;
  const missing = det.missing_parameters.length > 0
    ? det.missing_parameters.join(', ')
    : 'none';

  return (
    <div className="card animate-in">
      <div className="card-title">Debug View</div>

      {result.fallback_reason && (
        <div className="fallback-warning" style={{ marginBottom: 16, marginTop: 0 }}>
          <span className="fallback-icon">⚠️</span>
          <span className="fallback-text">{result.fallback_reason}</span>
        </div>
      )}

      {/* Deterministic Signals */}
      <div className="signal-group">
        <div className="signal-group-title">Deterministic Signals</div>
        <div className="signal-row">
          <span className="signal-name">has_recent_conflict</span>
          <BoolBadge value={det.has_recent_conflict} />
        </div>
        <div className="signal-row">
          <span className="signal-name">has_pending_block</span>
          <BoolBadge value={det.has_pending_block} />
        </div>
        <div className="signal-row">
          <span className="signal-name">action_type</span>
          <span className="signal-value">{det.action_type}</span>
        </div>
        <div className="signal-row">
          <span className="signal-name">external_party</span>
          <BoolBadge value={det.external_party} />
        </div>
        <div className="signal-row">
          <span className="signal-name">irreversible</span>
          <BoolBadge value={det.irreversible} />
        </div>
        <div className="signal-row">
          <span className="signal-name">missing_parameters</span>
          <span className="signal-value">{missing}</span>
        </div>
      </div>

      {/* LLM Signals */}
      <div className="signal-group">
        <div className="signal-group-title">LLM-Derived Signals</div>
        <div className="signal-row">
          <span className="signal-name">intent_clarity</span>
          <span className="signal-value">{llm.intent_clarity.toFixed(2)}</span>
        </div>
        <div className="signal-row">
          <span className="signal-name">risk_level</span>
          <span className="signal-value">{llm.risk_level}</span>
        </div>
        <div className="signal-row">
          <span className="signal-name">consistency_with_history</span>
          <BoolBadge value={llm.consistency_with_history} />
        </div>
        <div className="signal-row">
          <span className="signal-name">ambiguity_detected</span>
          <BoolBadge value={llm.ambiguity_detected} />
        </div>
        <div className="signal-row">
          <span className="signal-name">policy_violation</span>
          <BoolBadge value={llm.policy_violation} />
        </div>
      </div>

      {/* Raw LLM Response */}
      <details className="collapsible">
        <summary>Raw LLM Response</summary>
        <pre>{result.raw_llm_response ?? 'N/A'}</pre>
      </details>

      {/* Prompt Text */}
      <details className="collapsible">
        <summary>Prompt Text</summary>
        <pre>{result.prompt_text ?? 'N/A'}</pre>
      </details>
    </div>
  );
};

export default DebugPanel;
