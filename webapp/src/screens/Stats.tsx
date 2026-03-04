import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { TrendingUp, Award } from 'lucide-react'
import { mockStatsData } from '../data/mock'
import { useTelegram } from '../hooks/useTelegram'

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
    </div>
  )
}

export function Stats() {
  const { haptic } = useTelegram()
  const [active, setActive] = useState<Lift>('squat')

  const activeLift = LIFTS.find((l) => l.id === active)!
  const data = mockStatsData[active]
  const max = Math.max(...data.map((d) => d.weight))
  const latest = data[data.length - 1].weight
  const prev = data[data.length - 2].weight
  const delta = latest - prev

  return (
    <div className="px-4 pt-6 pb-8 space-y-5">
      <h1 className="text-white text-2xl font-bold">Статистика</h1>

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
                ? { backgroundColor: color, color: '#000', borderColor: 'transparent' }
                : { backgroundColor: 'rgba(255,255,255,0.05)', borderColor: 'rgba(255,255,255,0.1)', color: '#9ca3af' }
            }
          >
            {label}
          </motion.button>
        ))}
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-3 gap-3">
        <StatCard label="Максимум" value={`${max} кг`} />
        <StatCard label="Текущий" value={`${latest} кг`} />
        <StatCard
          label="Прирост"
          value={`${delta > 0 ? '+' : ''}${delta} кг`}
          accent={delta > 0 ? '#39ff14' : '#f97316'}
        />
      </div>

      {/* Chart */}
      <div className="glass-card pb-2">
        <div className="flex items-center gap-2 mb-4">
          <TrendingUp size={15} style={{ color: activeLift.color }} />
          <span className="text-white text-sm font-semibold">{activeLift.label} — прогресс</span>
        </div>
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
      </div>

      {/* Personal records */}
      <div>
        <p className="text-gray-400 text-xs font-semibold uppercase tracking-widest mb-3 flex items-center gap-2">
          <Award size={13} /> Личные рекорды
        </p>
        <div className="space-y-2">
          {LIFTS.map(({ id, label, color }) => {
            const pr = Math.max(...mockStatsData[id].map((d) => d.weight))
            return (
              <div key={id} className="glass-card flex items-center justify-between py-3">
                <span className="text-gray-300 text-sm">{label}</span>
                <span className="font-black text-base" style={{ color }}>
                  {pr} кг
                </span>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

function StatCard({ label, value, accent }: { label: string; value: string; accent?: string }) {
  return (
    <div className="glass-card py-3 text-center">
      <p className="text-gray-400 text-[10px] uppercase tracking-wide mb-1">{label}</p>
      <p className="font-black text-base" style={{ color: accent ?? '#fff' }}>
        {value}
      </p>
    </div>
  )
}
