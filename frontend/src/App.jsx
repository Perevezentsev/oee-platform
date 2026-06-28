import { useState } from 'react'
import ShiftForm from './ShiftForm'
import Dashboard from './Dashboard'
import Login from './Login'

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
    alignItems: 'center',
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
  logoutBtn: {
    marginLeft: 'auto',
    background: 'transparent',
    border: '1px solid var(--border)',
    color: 'var(--muted)',
    borderRadius: 6,
    padding: '4px 12px',
    fontSize: 12,
    cursor: 'pointer',
  },
}

export default function App() {
  const [token, setToken] = useState(localStorage.getItem('token'))
  const [page, setPage] = useState('dashboard')

  const handleLogin = (t) => setToken(t)

  const handleLogout = () => {
    localStorage.removeItem('token')
    setToken(null)
  }

  if (!token) return <Login onLogin={handleLogin} />

  return (
    <>
      <nav style={s.nav}>
        <button style={s.btn(page === 'dashboard')} onClick={() => setPage('dashboard')}>
          Дашборд
        </button>
        <button style={s.btn(page === 'form')} onClick={() => setPage('form')}>
          Ввод смены
        </button>
        <button style={s.logoutBtn} onClick={handleLogout}>
          Выйти
        </button>
      </nav>
      {page === 'dashboard' ? <Dashboard token={token} /> : <ShiftForm token={token} />}
    </>
  )
}