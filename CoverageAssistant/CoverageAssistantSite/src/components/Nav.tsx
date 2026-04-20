type View = 'library' | 'editor'

interface NavProps {
  activeView: View
  onViewChange: (view: View) => void
}

export function Nav({ activeView, onViewChange }: NavProps) {
  return (
    <nav className="nav">
      <div className="nav-inner">
        <div className="nav-brand">
          <svg
            className="nav-brand-icon"
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <path d="M12 2L2 7l10 5 10-5-10-5z" />
            <path d="M2 17l10 5 10-5" />
            <path d="M2 12l10 5 10-5" />
          </svg>
          Coverage Assistant
        </div>

        <div className="nav-tabs">
          <button
            className={`nav-tab${activeView === 'library' ? ' nav-tab--active' : ''}`}
            onClick={() => onViewChange('library')}
          >
            Report Library
          </button>
          <button
            className={`nav-tab${activeView === 'editor' ? ' nav-tab--active' : ''}`}
            onClick={() => onViewChange('editor')}
          >
            Draft Analysis
          </button>
        </div>
      </div>
    </nav>
  )
}
