import { Link } from 'react-router-dom';
import { Icon } from './ui';

export function QuickActions({ teacher = false }: { teacher?: boolean }) {
  const actions = teacher ? [
    ['/materials', 'Upload study material', 'book'], ['/drafts', 'Create question drafts', 'spark'],
    ['/assessments', 'Manage classroom tests', 'shield'], ['/analytics/teacher', 'View class performance', 'chart'],
  ] : [
    ['/join-assessment', 'Enter a reference code', 'book'], ['/drafts', 'Create practice questions', 'spark'],
    ['/learning', 'Continue learning', 'layers'], ['/analytics/student', 'View my performance', 'chart'],
  ];
  return <section className="quick-actions" aria-label="Quick actions"><div><span className="eyebrow">Start here</span><h2>What would you like to do?</h2></div><div className="quick-action-grid">{actions.map(([to, label, icon], i) => <Link to={to} key={to} className={`quick-action quick-${i}`}><Icon name={icon as 'book' | 'spark' | 'shield' | 'chart' | 'layers'} /><span>{label}</span><Icon name="arrow" size={16} /></Link>)}</div></section>;
}
