import { useState } from 'react'
import axios from 'axios'

const API = "/api/v1"

// Фиксированный станок для MVP (потом будет dropdown из /equipment)
const EQUIPMENT_ID = '11111111-1111-1111-1111-111111111111'

const REASONS = [
  'Переналадка',
  'Ожидание материала',
  'Поломка',
  'Отсутствие оператора',
  'Плановое ТО',
  'Обед / перерыв',
]

const emptyDowntime = () => ({ reason: REASONS[0], minutes: '', planned: false })

const s = {
  wrap: {
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'flex-start',
    justifyContent: 'center',
    padding: '32px 16px',
  },
  card: {
    background: 'var(--surface)',
    border: '1px solid var(--border)',
    borderRadius: 12,
    padding: '28px 32px',
    width: '100%',
    maxWidth: 600,
  },
  header: {
    marginBottom: 28,
    borderBottom: '1px solid var(--border)',
    paddingBottom: 16,
  },
  title: { fontSize: 18, fontWeight: 600, color: 'var(--text)' },
  sub:   { fontSize: 12, color: 'var(--muted)', marginTop: 4 },
  section: { marginBottom: 24 },
  label: {
    display: 'block',
    fontSize: 12,
    fontWeight: 500,
    color: 'var(--muted)',
    marginBottom: 6,
    textTransform: 'uppercase',
    letterSpacing: '.04em',
  },
  row2: { display: 'grid', gridTemplateColumns: '1fr', gap: 12 },
  row3: { display: 'grid', gridTemplateColumns: '1fr 1fr 80px', gap: 8, alignItems: 'end' },
  dtHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 10,
  },
  addBtn: {
    background: 'transparent',
    border: '1px solid var(--border)',
    color: 'var(--muted)',
    padding: '4px 12px',
    fontSize: 12,
  },
  removeBtn: {
    background: 'transparent',
    border: '1px solid var(--border)',
    color: 'var(--danger)',
    padding: '8px 12px',
    fontSize: 13,
    width: '100%',
  },
  checkRow: { display: 'flex', alignItems: 'center', gap: 8, marginTop: 6 },
  submitBtn: {
    background: 'var(--accent)',
    color: '#fff',
    width: '100%',
    padding: '12px',
    fontSize: 15,
    fontWeight: 600,
    marginTop: 8,
  },
  result: {
    marginTop: 24,
    background: 'var(--bg)',
    border: '1px solid var(--border)',
    borderRadius: 8,
    padding: 20,
  },
  oeeGrid: {
    display: 'grid',
    gridTemplateColumns: "repeat(2, 1fr)",
    gap: 12,
    marginBottom: 16,
  },
  metric: {
    background: 'var(--surface)',
    border: '1px solid var(--border)',
    borderRadius: 8,
    padding: '12px 10px',
    textAlign: 'center',
  },
  metricVal: { fontSize: 22, fontWeight: 600 },
  metricLbl: { fontSize: 11, color: 'var(--muted)', marginTop: 2 },
  paretoRow: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    marginBottom: 8,
  },
  bar: {
    height: 6,
    borderRadius: 3,
    background: 'var(--accent)',
    transition: 'width .4s',
  },
  error: {
    background: '#450a0a',
    border: '1px solid var(--danger)',
    borderRadius: 8,
    padding: '12px 16px',
    marginTop: 16,
    fontSize: 13,
    color: '#fca5a5',
  },
}

function oeeColor(pct) {
  if (pct >= 85) return 'var(--ok)'
  if (pct >= 65) return 'var(--warn)'
  return 'var(--danger)'
}

export default function ShiftForm() {
  const now = new Date()
  const pad = n => String(n).padStart(2, '0')
  const fmt = d => `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`

  const [form, setForm] = useState({
    shift_start: fmt(new Date(now.getTime() - 12 * 3600000)),
    shift_end:   fmt(now),
    planned_production_time_min: 660,
    total_parts_produced: '',
    good_parts: '',
    notes: '',
  })
  const [downtimes, setDowntimes] = useState([emptyDowntime()])
  const [loading, setLoading] = useState(false)
  const [result, setResult]   = useState(null)
  const [error, setError]     = useState(null)

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const setDt = (i, k, v) =>
    setDowntimes(ds => ds.map((d, idx) => idx === i ? { ...d, [k]: v } : d))

  const submit = async () => {
    setLoading(true); setError(null); setResult(null)
    try {
      const { data } = await axios.post(`${API}/shifts/`, {
        equipment_id: EQUIPMENT_ID,
        shift_start:  form.shift_start + ':00',
        shift_end:    form.shift_end + ':00',
        planned_production_time_min: Number(form.planned_production_time_min),
        total_parts_produced: Number(form.total_parts_produced),
        good_parts:   Number(form.good_parts),
        notes:        form.notes || null,
        downtime_events: downtimes
          .filter(d => d.minutes)
          .map(d => ({ reason: d.reason, minutes: Number(d.minutes), planned: d.planned })),
      })
      setResult(data)
    } catch (e) {
      setError(e.response?.data?.detail || e.message)
    } finally {
      setLoading(false)
    }
  }

  const maxDt = result
    ? Math.max(...result.oee_summary.downtime_pareto.map(([, m]) => m), 1)
    : 1

  return (
    <div style={s.wrap}>
      <div style={s.card}>

        <div style={s.header}>
          <div style={s.title}>Ввод смены</div>
          <div style={s.sub}>Станок ЧПУ-1 · Цех №2</div>
        </div>

        {/* Время смены */}
        <div style={s.section}>
          <div style={s.row2}>
            <div>
              <label style={s.label}>Начало смены</label>
              <input type="datetime-local" value={form.shift_start}
                onChange={e => set('shift_start', e.target.value)} />
            </div>
            <div>
              <label style={s.label}>Конец смены</label>
              <input type="datetime-local" value={form.shift_end}
                onChange={e => set('shift_end', e.target.value)} />
            </div>
          </div>
        </div>

        {/* Выпуск */}
        <div style={s.section}>
          <div style={s.row3}>
            <div>
              <label style={s.label}>Плановое время (мин)</label>
              <input type="number" value={form.planned_production_time_min}
                onChange={e => set('planned_production_time_min', e.target.value)} />
            </div>
            <div>
              <label style={s.label}>Всего деталей</label>
              <input type="number" value={form.total_parts_produced} placeholder="480"
                onChange={e => set('total_parts_produced', e.target.value)} />
            </div>
            <div>
              <label style={s.label}>Годных</label>
              <input type="number" value={form.good_parts} placeholder="461"
                onChange={e => set('good_parts', e.target.value)} />
            </div>
          </div>
        </div>

        {/* Простои */}
        <div style={s.section}>
          <div style={s.dtHeader}>
            <label style={{ ...s.label, margin: 0 }}>Простои</label>
            <button style={s.addBtn} onClick={() => setDowntimes(ds => [...ds, emptyDowntime()])}>
              + Добавить
            </button>
          </div>
          {downtimes.map((dt, i) => (
            <div key={i} style={{ marginBottom: 12 }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 80px 36px', gap: 8, alignItems: 'end' }}>
                <div>
                  <select value={dt.reason} onChange={e => setDt(i, 'reason', e.target.value)}>
                    {REASONS.map(r => <option key={r}>{r}</option>)}
                  </select>
                </div>
                <div>
                  <label style={s.label}>Мин</label>
                  <input type="number" value={dt.minutes} placeholder="30"
                    onChange={e => setDt(i, 'minutes', e.target.value)} />
                </div>
                <button style={s.removeBtn}
                  onClick={() => setDowntimes(ds => ds.filter((_, idx) => idx !== i))}>
                  ✕
                </button>
              </div>
              <div style={s.checkRow}>
                <input type="checkbox" id={`p${i}`} checked={dt.planned}
                  onChange={e => setDt(i, 'planned', e.target.checked)}
                  style={{ width: 'auto' }} />
                <label htmlFor={`p${i}`} style={{ fontSize: 12, color: 'var(--muted)' }}>
                  Плановый
                </label>
              </div>
            </div>
          ))}
        </div>

        {/* Примечание */}
        <div style={s.section}>
          <label style={s.label}>Примечание</label>
          <textarea rows={2} value={form.notes} placeholder="Необязательно"
            onChange={e => set('notes', e.target.value)} />
        </div>

        <button style={s.submitBtn} onClick={submit} disabled={loading}>
          {loading ? 'Отправка...' : 'Записать смену'}
        </button>

        {/* Ошибка */}
        {error && <div style={s.error}>⚠ {JSON.stringify(error)}</div>}

        {/* Результат OEE */}
        {result && (
          <div style={s.result}>
            <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 14, color: 'var(--muted)' }}>
              РЕЗУЛЬТАТ OEE
            </div>
            <div style={s.oeeGrid}>
              {[
                ['OEE', result.oee_summary.oee_pct],
                ['Доступность', result.oee_summary.availability_pct],
                ['Производит.', result.oee_summary.performance_pct],
                ['Качество', result.oee_summary.quality_pct],
              ].map(([lbl, val]) => (
                <div key={lbl} style={s.metric}>
                  <div style={{ ...s.metricVal, color: oeeColor(val) }}>{val}%</div>
                  <div style={s.metricLbl}>{lbl}</div>
                </div>
              ))}
            </div>

            {result.oee_summary.downtime_pareto.length > 0 && (
              <>
                <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 10 }}>
                  ПАРЕТО ПОТЕРЬ
                </div>
                {result.oee_summary.downtime_pareto.map(([reason, min]) => (
                  <div key={reason} style={s.paretoRow}>
                    <div style={{ minWidth: 160, fontSize: 13 }}>{reason}</div>
                    <div style={{ flex: 1, background: 'var(--border)', borderRadius: 3, height: 6 }}>
                      <div style={{ ...s.bar, width: `${(min / maxDt) * 100}%` }} />
                    </div>
                    <div style={{ minWidth: 50, textAlign: 'right', fontSize: 12, color: 'var(--muted)' }}>
                      {min} мин
                    </div>
                  </div>
                ))}
              </>
            )}

            <div style={{ marginTop: 16, fontSize: 12, color: 'var(--muted)', display: 'flex', gap: 20 }}>
              <span>Время работы: {result.oee_summary.actual_run_time_min} мин</span>
              <span>Простои: {result.oee_summary.total_downtime_min} мин</span>
              <span>Брак: {result.oee_summary.defect_parts} шт</span>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}