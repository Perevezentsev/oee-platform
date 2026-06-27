import { useState } from 'react'
import ShiftForm from './ShiftForm'
import Dashboard from './Dashboard'

const s = {
  nav: {
    display: 'flex',
    gap: 4,
    padding: '12px 16px',
    borderBottom: '1px solid var(--border)',
    background: 'var(--surface)',
    position: 'sticky',
    top: 0,
    zIndex: 10,
  },
  btn: (active) => ({
    background: active ? 'var(--accent)' : 'transparent',
    color: active ? '#fff' : 'var(--muted)',
    border: 'none',
    borderRadius: 6,
    padding: '6px 16px',
    fontSize: 13,
    fontWeight: active ? 600 : 400,
    cursor: 'pointer',
  }),
}

export default function App() {
  const [page, setPage] = useState('dashboard')

  return (
    <>
      <nav style={s.nav}>
        <button style={s.btn(page === 'dashboard')} onClick={() => setPage('dashboard')}>
          Дашборд
        </button>
        <button style={s.btn(page === 'form')} onClick={() => setPage('form')}>
          Ввод смены
        </button>
      </nav>
      {page === 'dashboard' ? <Dashboard /> : <ShiftForm />}
    </>
  )
}