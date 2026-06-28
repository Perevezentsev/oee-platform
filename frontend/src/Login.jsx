import { useState } from 'react'
import axios from 'axios'

const s = {
  wrap: {
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '16px',
  },
  card: {
    background: 'var(--surface)',
    border: '1px solid var(--border)',
    borderRadius: 12,
    padding: '32px 28px',
    width: '100%',
    maxWidth: 360,
  },
  logo: {
    fontSize: 24,
    fontWeight: 700,
    color: 'var(--accent)',
    marginBottom: 4,
  },
  sub: {
    fontSize: 13,
    color: 'var(--muted)',
    marginBottom: 28,
  },
  label: {
    display: 'block',
    fontSize: 12,
    fontWeight: 500,
    color: 'var(--muted)',
    marginBottom: 6,
    textTransform: 'uppercase',
    letterSpacing: '.04em',
  },
  field: { marginBottom: 16 },
  btn: {
    background: 'var(--accent)',
    color: '#fff',
    width: '100%',
    padding: '12px',
    fontSize: 15,
    fontWeight: 600,
    marginTop: 8,
    borderRadius: 8,
    border: 'none',
    cursor: 'pointer',
  },
  error: {
    background: '#450a0a',
    border: '1px solid var(--danger)',
    borderRadius: 8,
    padding: '10px 14px',
    marginTop: 14,
    fontSize: 13,
    color: '#fca5a5',
  },
}

export default function Login({ onLogin }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const submit = async () => {
    setLoading(true)
    setError(null)
    try {
      const form = new FormData()
      form.append('username', email)
      form.append('password', password)
      const { data } = await axios.post('/api/v1/auth/login', form)
      localStorage.setItem('token', data.access_token)
      onLogin(data.access_token)
    } catch (e) {
      setError(e.response?.data?.detail || 'Ошибка входа')
    } finally {
      setLoading(false)
    }
  }

  const onKey = e => e.key === 'Enter' && submit()

  return (
    <div style={s.wrap}>
      <div style={s.card}>
        <div style={s.logo}>Monitix</div>
        <div style={s.sub}>Мониторинг производства</div>

        <div style={s.field}>
          <label style={s.label}>Email</label>
          <input
            type="email"
            value={email}
            placeholder="admin@monitix.ru"
            onChange={e => setEmail(e.target.value)}
            onKeyDown={onKey}
            autoComplete="email"
          />
        </div>

        <div style={s.field}>
          <label style={s.label}>Пароль</label>
          <input
            type="password"
            value={password}
            placeholder="••••••••"
            onChange={e => setPassword(e.target.value)}
            onKeyDown={onKey}
            autoComplete="current-password"
          />
        </div>

        <button style={s.btn} onClick={submit} disabled={loading}>
          {loading ? 'Вход...' : 'Войти'}
        </button>

        {error && <div style={s.error}>{error}</div>}
      </div>
    </div>
  )
}