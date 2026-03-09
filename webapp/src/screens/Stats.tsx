import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'
import { TrendingUp, Award, RefreshCw } from 'lucide-react'
import { useTelegram } from '../hooks/useTelegram'
import { api } from '../services/api'
import { mockStatsData } from '../data/mock'
import type { StatPoint } from '../services/api'

type Lift = 'squat' | 'bench' | 'deadlift'

const LIFTS: { id: Lift; label: string; color: string }[] = [
  { id: 'squat',    label: 'Приседания', color: '#39ff14' },
  { id: 'bench',    label: 'Жим лёжа',  color: '#f97316' },
  { id: 'deadlift', label: 'Становая',  color: '#a855f7' },
]

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-slate-800 border border-white/10 rounded-xl px-3 py-2 shadow-xl">
      <p className="text-gray-400 text-xs mb-0.5">{label}</p>
      <p className="text-white font-bold text-sm">{payload[0].value} кг</p>
      {payload[0].payload?.tournament && (
        <p className="text-gray-500 text-[10px] mt-0.5">{payload[0].payload.tournament}</p>
      )}
    </div>
  )
}

export function Stats() {
  const { haptic } = useTelegram()
  const [active, setActive]   = useState<Lift>('squat')
  const [stats, setStats]     = useState<Record<Lift, StatPoint[]>>(mockStatsData)
  const [loading, setLoading] = useState(true)
  const [hasData, setHasData] = useState(false)

  useEffect(() => {
    api.myStats()
      .then(data => {
        const anyData = data.squat.length > 0 || data.bench.length > 0 || data.deadlift.length > 0
        if (anyData) {
          setStats(data)
          setHasData(true)
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const activeLift = LIFTS.find(l => l.id === active)!
  const data = stats[active]

  const max    = data.length > 0 ? Math.max(...data.map(d => d.weight)) : 0
  const latest = data.length > 0 ? data[data.length - 1].weight : 0
  const prev   = data.length > 1 ? data[data.length - 2].weight : latest
  const delta  = latest - prev

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <RefreshCw size={28} className="text-neon-green animate-spin" />
      </div>
    )
  }

  return (
    <div className="h-full overflow-y-auto overscroll-contain">
      <div className="px-4 pt-6 pb-8 space-y-5">
        <h1 className="gradient-text-purple text-3xl font-black uppercase tracking-tight">Статистика</h1>

        {!hasData && (
          <div className="glass-card text-center py-6 text-gray-500 text-sm">
            Примерные данные — участвуй в турнирах чтобы увидеть свой прогресс
          </div>
        )}

        {/* Lift selector */}
        <div className="grid grid-cols-3 gap-2">
          {LIFTS.map(({ id, label, color }) => (
            <motion.button
              key={id}
              whileTap={{ scale: 0.95 }}
              onClick={() => { haptic.impact('light'); setActive(id) }}
              className="py-3 rounded-xl text-xs font-bold border transition-all"
              style={
                active === id
                  ? { background: color, color: '#000', borderColor: 'transparent', boxShadow: `0 0 20px ${color}60, 0 0 40px ${color}22` }
                  : { backgroundColor: 'rgba(255,255,255,0.05)', borderColor: 'rgba(255,255,255,0.1)', color: '#9ca3af' }
              }
            >
              {label}
            </motion.button>
          ))}
        </div>

        {/* Stat cards */}
        <div className="grid grid-cols-3 gap-3">
          <StatCard label="Максимум" value={max ? `${max} кг` : '—'} />
          <StatCard label="Текущий"  value={latest ? `${latest} кг` : '—'} />
          <StatCard
            label="Прирост"
            value={data.length > 1 ? `${delta > 0 ? '+' : ''}${delta} кг` : '—'}
            accent={delta > 0 ? '#39ff14' : delta < 0 ? '#f97316' : undefined}
          />
        </div>

        {/* Chart */}
        <div className="glass-card pb-2">
          <div className="flex items-center gap-2 mb-4">
            <TrendingUp size={15} style={{ color: activeLift.color }} />
            <span className="text-white text-sm font-semibold">{activeLift.label} — прогресс</span>
          </div>
          {data.length < 2 ? (
            <div className="h-[200px] flex items-center justify-center text-gray-600 text-sm">
              Нужно минимум 2 турнира
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={data} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis
                  dataKey="date"
                  tick={{ fill: '#6b7280', fontSize: 10 }}
                  axisLine={{ stroke: 'rgba(255,255,255,0.08)' }}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fill: '#6b7280', fontSize: 10 }}
                  axisLine={{ stroke: 'rgba(255,255,255,0.08)' }}
                  tickLine={false}
                  domain={['dataMin - 10', 'dataMax + 10']}
                />
                <Tooltip content={<CustomTooltip />} cursor={{ stroke: 'rgba(255,255,255,0.1)' }} />
                <Line
                  type="monotone"
                  dataKey="weight"
                  stroke={activeLift.color}
                  strokeWidth={2.5}
                  dot={{ fill: activeLift.color, r: 4, strokeWidth: 0 }}
                  activeDot={{ r: 6, strokeWidth: 0, fill: activeLift.color }}
                />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Personal records */}
        <div>
          <p className="text-gray-400 text-xs font-semibold uppercase tracking-widest mb-3 flex items-center gap-2">
            <Award size={13} /> Личные рекорды
          </p>
          <div className="space-y-2">
            {LIFTS.map(({ id, label, color }) => {
              const pr = stats[id].length > 0 ? Math.max(...stats[id].map(d => d.weight)) : null
              return (
                <div key={id} className="glass-card flex items-center justify-between py-3">
                  <span className="text-gray-300 text-sm">{label}</span>
                  <span className="font-black text-base" style={{ color }}>
                    {pr ? `${pr} кг` : '—'}
                  </span>
                </div>
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}

function StatCard({ label, value, accent }: { label: string; value: string; accent?: string }) {
  return (
    <div
      className="glass-card py-3 text-center"
      style={accent ? {
        borderColor: `${accent}35`,
        background: `${accent}0a`,
        boxShadow: `0 0 16px ${accent}18`,
      } : {}}
    >
      <p className="text-gray-400 text-[10px] uppercase tracking-wide mb-1">{label}</p>
      <p className="font-black text-base" style={{ color: accent ?? '#fff' }}>{value}</p>
    </div>
  )
}
