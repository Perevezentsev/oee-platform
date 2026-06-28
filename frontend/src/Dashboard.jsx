import { useState, useEffect } from 'react'
import axios from 'axios'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine
} from 'recharts'

const API = "/api/v1"
const EQUIPMENT_ID = '11111111-1111-1111-1111-111111111111'

const s = {
  wrap: {
    minHeight: '100vh',
    padding: '24px 16px',
    maxWidth: 900,
    margin: '0 auto',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 24
  },
  title: { fontSize: 20, fontWeight: 600 },
  sub: { fontSize: 12, color: 'var(--muted)', marginTop: 2 },
  section: { marginBottom: 28 },
  sectionTitle: {
    fontSize: 11,
    fontWeight: 600,
    color: 'var(--muted)',
    textTransform: 'uppercase',
    letterSpacing: '.06em',
    marginBottom: 12,
  },
  metricsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(2, 1fr)',
    gap: 12,
  },
  metricCard: {
    background: 'var(--surface)',
    border: '1px solid var(--border)',
    borderRadius: 10,
    padding: '16px 14px',
    textAlign: 'center',
  },
  metricVal: { fontSize: 28, fontWeight: 600, lineHeight: 1 },
  metricLbl: { fontSize: 11, color: 'var(--muted)', marginTop: 6 },
  chartCard: {
    background: 'var(--surface)',
    border: '1px solid var(--border)',
    borderRadius: 10,
    padding: '20px 16px',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    fontSize: 13,
  },
  th: {
    textAlign: 'left',
    fontSize: 11,
    color: 'var(--muted)',
    fontWeight: 500,
    padding: '0 12px 10px 0',
    textTransform: 'uppercase',
    letterSpacing: '.04em',
  },
  td: {
    padding: '10px 12px 10px 0',
    borderTop: '1px solid var(--border)',
    color: 'var(--text)',
  },
  paretoRow: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    marginBottom: 10,
  },
  loading: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    height: '60vh',
    color: 'var(--muted)',
    fontSize: 14,
  },
}

function oeeColor(pct) {
  if (pct >= 85) return 'var(--ok)'
  if (pct >= 65) return 'var(--warn)'
  return 'var(--danger)'
}

function fmt(iso) {
  const d = new Date(iso)
  return `${String(d.getDate()).padStart(2,'0')}.${String(d.getMonth()+1).padStart(2,'0')} ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`
}

function fmtDate(iso) {
  const [y, m, d] = iso.split('-')
  return `${d}.${m}`
}

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 6, padding: '8px 12px', fontSize: 12 }}>
      <div style={{ color: 'var(--muted)', marginBottom: 4 }}>{label}</div>
      <div style={{ color: oeeColor(payload[0].value), fontWeight: 600 }}>OEE: {payload[0].value}%</div>
    </div>
  )
}

export default function Dashboard(props) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  useEffect(() => {
    axios.get(`${API}/dashboard/${EQUIPMENT_ID}`, { headers: { Authorization: `Bearer ${props.token}` } })
      .then(r => setData(r.data))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])
  if (loading) return <div style={s.loading}>Загрузка данных...</div>
  if (error)   return <div style={s.loading}>Ошибка: {error}</div>
  if (!data)   return <div style={s.loading}>Нет данных</div>

  const maxPareto = data.pareto[0]?.minutes || 1

  return (
    <div style={s.wrap}>

      {/* Заголовок */}
      <div style={s.header}>
        <div>
          <div style={s.title}>Monitix</div>
          <div style={s.sub}>{data.equipment_name} · последние 30 дней</div>
        </div>
        <div style={{ fontSize: 12, color: 'var(--muted)' }}>
          {new Date().toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' })}
        </div>
      </div>

      {/* Метрики */}
      {data.today && (
        <div style={s.section}>
          <div style={s.sectionTitle}>Последняя смена</div>
          <div style={s.metricsGrid}>
            {[
              ['OEE',          data.today.oee_pct],
              ['Доступность',  data.today.availability_pct],
              ['Производит.',  data.today.performance_pct],
              ['Качество',     data.today.quality_pct],
            ].map(([lbl, val]) => (
              <div key={lbl} style={s.metricCard}>
                <div style={{ ...s.metricVal, color: oeeColor(val) }}>{val}%</div>
                <div style={s.metricLbl}>{lbl}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Тренд OEE */}
      {data.trend.length > 0 && (
        <div style={s.section}>
          <div style={s.sectionTitle}>Тренд OEE за 30 дней</div>
          <div style={s.chartCard}>
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={data.trend} margin={{ top: 5, right: 10, bottom: 5, left: -20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis
                  dataKey="date"
                  tickFormatter={fmtDate}
                  tick={{ fontSize: 11, fill: 'var(--muted)' }}
                  tickLine={false}
                />
                <YAxis
                  domain={[0, 100]}
                  tick={{ fontSize: 11, fill: 'var(--muted)' }}
                  tickLine={false}
                  axisLine={false}
                />
                <Tooltip content={<CustomTooltip />} />
                <ReferenceLine y={85} stroke="var(--ok)" strokeDasharray="4 4" label={{ value: '85%', fontSize: 10, fill: 'var(--ok)' }} />
                <ReferenceLine y={65} stroke="var(--warn)" strokeDasharray="4 4" label={{ value: '65%', fontSize: 10, fill: 'var(--warn)' }} />
                <Line
                  type="monotone"
                  dataKey="oee_pct"
                  stroke="var(--accent)"
                  strokeWidth={2}
                  dot={{ fill: 'var(--accent)', r: 3 }}
                  activeDot={{ r: 5 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Парето потерь */}
      {data.pareto.length > 0 && (
        <div style={s.section}>
          <div style={s.sectionTitle}>Парето потерь за 30 дней</div>
          <div style={s.chartCard}>
            {data.pareto.map(({ reason, minutes }) => (
              <div key={reason} style={s.paretoRow}>
                <div style={{ minWidth: 180, fontSize: 13 }}>{reason}</div>
                <div style={{ flex: 1, background: 'var(--border)', borderRadius: 3, height: 8 }}>
                  <div style={{
                    height: '100%',
                    borderRadius: 3,
                    background: 'var(--accent)',
                    width: `${(minutes / maxPareto) * 100}%`,
                    transition: 'width .4s',
                  }} />
                </div>
                <div style={{ minWidth: 60, textAlign: 'right', fontSize: 12, color: 'var(--muted)' }}>
                  {minutes} мин
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Последние смены */}
      {data.recent_shifts.length > 0 && (
        <div style={s.section}>
          <div style={s.sectionTitle}>Последние смены</div>
          <div style={s.chartCard}>
            <table style={s.table}>
              <thead>
                <tr>
                  <th style={s.th}>Смена</th>
                  <th style={s.th}>OEE</th>
                  <th style={s.th}>Деталей</th>
                  <th style={s.th}>Брак</th>
                  <th style={s.th}>Простои</th>
                </tr>
              </thead>
              <tbody>
                {data.recent_shifts.map(shift => (
                  <tr key={shift.id}>
                    <td style={s.td}>{fmt(shift.shift_start)}</td>
                    <td style={{ ...s.td, fontWeight: 600, color: oeeColor(shift.oee_pct) }}>
                      {shift.oee_pct}%
                    </td>
                    <td style={s.td}>{shift.total_parts}</td>
                    <td style={{ ...s.td, color: shift.defect_parts > 0 ? 'var(--danger)' : 'var(--muted)' }}>
                      {shift.defect_parts}
                    </td>
                    <td style={{ ...s.td, color: shift.downtime_min > 60 ? 'var(--warn)' : 'var(--text)' }}>
                      {shift.downtime_min} мин
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

    </div>
  )
}