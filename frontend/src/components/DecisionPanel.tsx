import type { DecideResponse, DecisionOutcome } from '../types';

interface DecisionPanelProps {
  result: DecideResponse | null;
  loading?: boolean;
}

const OUTCOME_CLASS: Record<DecisionOutcome, string> = {
  EXECUTE_SILENTLY: 'execute-silently',
  EXECUTE_AND_NOTIFY: 'execute-and-notify',
  CONFIRM_BEFORE_EXECUTING: 'confirm-before-executing',
  ASK_CLARIFYING_QUESTION: 'ask-clarifying-question',
  REFUSE: 'refuse',
};

const OUTCOME_ICON: Record<DecisionOutcome, string> = {
  EXECUTE_SILENTLY: '✓',
  EXECUTE_AND_NOTIFY: '🔔',
  CONFIRM_BEFORE_EXECUTING: '⚡',
  ASK_CLARIFYING_QUESTION: '❓',
  REFUSE: '✕',
};

const OUTCOME_COLOR: Record<DecisionOutcome, string> = {
  EXECUTE_SILENTLY: 'var(--green)',
  EXECUTE_AND_NOTIFY: 'var(--yellow)',
  CONFIRM_BEFORE_EXECUTING: 'var(--orange)',
  ASK_CLARIFYING_QUESTION: 'var(--blue)',
  REFUSE: 'var(--red)',
};

const DecisionPanel: React.FC<DecisionPanelProps> = ({ result, loading }) => {
  if (!result) {
    return (
      <div className="card">
        <div className="card-title">Decision</div>
        <div className="placeholder-state">
          <div className="placeholder-icon">{loading ? '⏳' : '🎯'}</div>
          <div className="placeholder-text">
            {loading ? 'Analyzing action…' : 'Submit an action to see the decision'}
          </div>
        </div>
      </div>
    );
  }

  const cls = OUTCOME_CLASS[result.decision];
  const icon = OUTCOME_ICON[result.decision];
  const color = OUTCOME_COLOR[result.decision];
  const pct = Math.round(result.confidence_score * 100);

  return (
    <div className="card animate-in">
      <div className="card-title">Decision</div>

      <div className={`outcome-badge ${cls}`}>
        <span>{icon}</span>
        {result.decision.replace(/_/g, ' ')}
      </div>

      {/* Confidence */}
      <div className="gauge-section">
        <div className="gauge-header">
          <span className="gauge-label">Confidence</span>
          <span className="gauge-value" style={{ color }}>{pct}%</span>
        </div>
        <div className="gauge-track">
          <div className="gauge-fill" style={{ width: `${pct}%`, background: color }} />
        </div>
      </div>

      {/* Explanation */}
      <div className="explanation-section">
        <div className="explanation-label">Explanation</div>
        <p className="explanation-text">{result.explanation}</p>
      </div>

      {/* Why Not Others */}
      <div className="explanation-section">
        <div className="explanation-label">Why Not Other Decisions</div>
        <p className="explanation-text">{result.why_not_others}</p>
      </div>

      {/* Fallback */}
      {result.fallback_reason && (
        <div className="fallback-warning">
          <span className="fallback-icon">⚠️</span>
          <span className="fallback-text">{result.fallback_reason}</span>
        </div>
      )}
    </div>
  );
};

export default DecisionPanel;
