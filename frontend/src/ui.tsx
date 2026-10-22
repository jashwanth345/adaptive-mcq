import { useId, useState, type InputHTMLAttributes, type ReactNode } from 'react';
import { ApiError, errorMessage } from './api';

export function Icon({ name, size = 20 }: { name: 'grid' | 'book' | 'chart' | 'user' | 'arrow' | 'check' | 'logout' | 'shield' | 'spark' | 'menu' | 'layers'; size?: number }) {
  const paths = {
    grid: 'M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z',
    book: 'M12 5c-3-2-7-2-10-1v15c3-1 7-1 10 1 3-2 7-2 10-1V4c-3-1-7-1-10 1v15',
    chart: 'M4 3v17h17 M9 16v-5 M14 16V7 M19 16V4', user: 'M16 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0 M4 21v-3a6 6 0 0 1 6-6h4a6 6 0 0 1 6 6v3',
    arrow: 'M4 12h16 M14 6l6 6-6 6', check: 'm5 12 4 4L19 6', logout: 'M9 4H4v16h5 M10 12h11 m-5-5 5 5-5 5',
    shield: 'm12 3 8 3v6c0 4-5 8-8 9-3-1-8-5-8-9V6z m-4 9 3 3 5-6', spark: 'm12 2 3 7 7 3-7 3-3 7-3-7-7-3 7-3z',
    menu: 'M4 6h16 M4 12h16 M4 18h16', layers: 'm12 3 10 5-10 5L2 8z M2 12l10 5 10-5 M2 16l10 5 10-5',
  };
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={paths[name]} /></svg>;
}
export function Brand({ light = false }: { light?: boolean }) {
  return <div className={`brand ${light ? 'brand-light' : ''}`}><img src="/mark.svg" width="40" height="40" alt="" /><span>Adaptive<span className="brand-mcq">MCQ</span></span></div>;
}
export function Field({ label, hint, ...props }: InputHTMLAttributes<HTMLInputElement> & { label: string; hint?: string }) {
  const id = useId();
  return <div className="field"><label htmlFor={id}>{label}</label><input id={id} aria-describedby={hint ? `${id}-hint` : undefined} {...props} />{hint && <small id={`${id}-hint`}>{hint}</small>}</div>;
}
export function PasswordField({ label = 'Password', hint, ...props }: Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> & { label?: string; hint?: string }) {
  const [visible, setVisible] = useState(false); const id = useId();
  return <div className="field"><label htmlFor={id}>{label}</label><div className="password-wrap"><input id={id} type={visible ? 'text' : 'password'} aria-describedby={hint ? `${id}-hint` : undefined} {...props} /><button type="button" onClick={() => setVisible(!visible)} aria-label={`${visible ? 'Hide' : 'Show'} ${label.toLowerCase()}`} aria-pressed={visible}>{visible ? 'Hide' : 'Show'}</button></div>{hint && <small id={`${id}-hint`}>{hint}</small>}</div>;
}
export function ErrorNotice({ error }: { error: unknown }) {
  if (!error) return null;
  return <div className="notice error" role="alert"><span>{errorMessage(error)}</span>{error instanceof ApiError && error.requestId && <details><summary>Support details</summary><small>Request: {error.requestId}</small></details>}</div>;
}
export function Badge({ children, tone = 'muted' }: { children: ReactNode; tone?: 'muted' | 'green' | 'purple' }) { return <span className={`badge ${tone}`}>{children}</span>; }
