import { motion } from 'framer-motion'
import { LayoutDashboard, Dumbbell, BarChart2 } from 'lucide-react'
import { useTelegram } from '../hooks/useTelegram'
import type { Tab } from '../types'

const tabs: { id: Tab; label: string; Icon: React.FC<{ size: number; className?: string }> }[] = [
  { id: 'dashboard', label: 'Главная',    Icon: LayoutDashboard },
  { id: 'workout',   label: 'Тренировка', Icon: Dumbbell },
  { id: 'stats',     label: 'Статистика', Icon: BarChart2 },
]

interface Props {
  active: Tab
  onChange: (tab: Tab) => void
}

export function BottomNav({ active, onChange }: Props) {
  const { haptic } = useTelegram()

  return (
    <nav className="bg-slate-900/90 backdrop-blur-xl border-t border-white/10 pb-safe">
      <div className="flex items-center justify-around h-16 px-4">
        {tabs.map(({ id, label, Icon }) => {
          const isActive = id === active
          return (
            <button
              key={id}
              onClick={() => {
                haptic.impact('light')
                onChange(id)
              }}
              className="flex flex-col items-center gap-0.5 flex-1 py-2 relative"
            >
              {isActive && (
                <motion.div
                  layoutId="nav-indicator"
                  className="absolute inset-0 bg-neon-green/10 rounded-xl"
                  transition={{ type: 'spring', bounce: 0.2, duration: 0.4 }}
                />
              )}
              <Icon
                size={22}
                className={isActive ? 'text-neon-green' : 'text-gray-500'}
              />
              <span className={`text-[10px] font-medium ${isActive ? 'text-neon-green' : 'text-gray-500'}`}>
                {label}
              </span>
            </button>
          )
        })}
      </div>
    </nav>
  )
}
