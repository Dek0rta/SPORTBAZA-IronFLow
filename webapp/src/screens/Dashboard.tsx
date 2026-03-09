import { motion } from 'framer-motion'
import { Play, Zap, Calendar, TrendingUp } from 'lucide-react'
import { useTelegram } from '../hooks/useTelegram'
import { RingProgress } from '../components/RingProgress'
import { mockWeeklyActivity, mockLastWorkout } from '../data/mock'

const item = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0, transition: { ease: 'easeOut', duration: 0.4 } },
}
const container = {
  animate: { transition: { staggerChildren: 0.08 } },
}

interface Props {
  onStartWorkout: () => void
}

export function Dashboard({ onStartWorkout }: Props) {
  const { user, haptic } = useTelegram()
  const { goal, completed, calories, caloriesGoal } = mockWeeklyActivity
  const activityPct = Math.round((completed / goal) * 100)
  const calPct = Math.round((calories / caloriesGoal) * 100)

  return (
    <div className="px-4 pt-6 pb-8">
      <motion.div
        variants={container}
        initial="initial"
        animate="animate"
        className="space-y-5"
      >
        {/* Header */}
        <motion.div variants={item} className="flex items-center justify-between">
          <div>
            <p className="text-gray-400 text-sm">Привет 👋</p>
            <h1 className="gradient-text-green text-2xl font-bold mt-0.5">
              {user.first_name}
            </h1>
          </div>
          <div className="w-12 h-12 rounded-full bg-gradient-to-br from-neon-green to-emerald-600 flex items-center justify-center shadow-[0_0_20px_rgba(57,255,20,0.3)]">
            <span className="text-black font-black text-xl">
              {user.first_name[0].toUpperCase()}
            </span>
          </div>
        </motion.div>

        {/* Activity rings */}
        <motion.div variants={item} className="glass-card flex items-center justify-around py-5">
          <RingProgress
            value={activityPct}
            label={`${completed}/${goal}`}
            sublabel={'Трен.\nнедели'}
            color="#39ff14"
            size={120}
          />
          <RingProgress
            value={calPct}
            label={calories.toLocaleString()}
            sublabel={'Ккал'}
            color="#f97316"
            size={105}
            strokeWidth={10}
          />
          <div className="flex flex-col gap-4">
            <Stat label="Объём" value={`${(mockLastWorkout.totalVolume / 1000).toFixed(1)}т`} />
            <Stat label="Сеты"  value={String(mockLastWorkout.sets)} />
            <Stat label="Мин."  value={String(mockLastWorkout.duration)} />
          </div>
        </motion.div>

        {/* Last workout */}
        <motion.div variants={item}>
          <p className="text-gray-400 text-xs font-semibold uppercase tracking-widest mb-3">
            Последняя тренировка
          </p>
          <div className="glass-card space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-gray-400 text-sm">
                <Calendar size={14} />
                {mockLastWorkout.date}
              </div>
              <div className="flex items-center gap-1 text-neon-green text-sm font-semibold">
                <TrendingUp size={14} />
                +5%
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              {mockLastWorkout.exercises.map((ex) => (
                <span
                  key={ex}
                  className="px-3 py-1 rounded-full bg-white/5 border border-white/10 text-gray-300 text-xs"
                >
                  {ex}
                </span>
              ))}
            </div>
            <div className="flex items-center gap-1 text-white/50 text-xs pt-1 border-t border-white/5">
              <Zap size={12} className="text-orange-400" />
              Объём:
              <span className="text-white font-semibold ml-1">
                {mockLastWorkout.totalVolume.toLocaleString()} кг
              </span>
              <span className="mx-2">·</span>
              <span>{mockLastWorkout.duration} мин</span>
            </div>
          </div>
        </motion.div>

        {/* CTA */}
        <motion.div variants={item}>
          <button
            onClick={() => {
              haptic.impact('medium')
              onStartWorkout()
            }}
            className="w-full h-16 bg-neon-green text-black rounded-2xl font-black text-lg flex items-center justify-center gap-3 glow-pulse active:scale-95 transition-transform"
          >
            <Play size={24} fill="black" />
            Начать тренировку
          </button>
        </motion.div>
      </motion.div>
    </div>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="text-center">
      <p className="text-white font-bold text-base leading-none">{value}</p>
      <p className="text-gray-500 text-xs mt-0.5">{label}</p>
    </div>
  )
}
