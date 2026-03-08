import type { FC } from 'react'
import { motion } from 'framer-motion'
import { User, Trophy, Swords, Bell } from 'lucide-react'
import { useTelegram } from '../hooks/useTelegram'
import type { Tab } from '../types'

const TABS: { id: Tab; label: string; Icon: FC<{ size: number; className?: string }> }[] = [
  { id: 'profile',       label: 'Профиль',     Icon: User   },
  { id: 'leaderboard',   label: 'Ладдер',      Icon: Trophy },
  { id: 'competitions',  label: 'Турниры',      Icon: Swords },
  { id: 'notifications', label: 'Лента',        Icon: Bell   },
]

interface Props {
  active: Tab
  onChange: (tab: Tab) => void
  unreadCount?: number
}

export function BottomNav({ active, onChange, unreadCount = 0 }: Props) {
  const { haptic } = useTelegram()

  return (
    <nav className="bg-slate-900/90 backdrop-blur-xl border-t border-white/10 pb-safe">
      <div className="flex items-center justify-around h-16 px-2">
        {TABS.map(({ id, label, Icon }) => {
          const isActive = id === active
          const showBadge = id === 'notifications' && unreadCount > 0
          return (
            <button
              key={id}
              onClick={() => { haptic.impact('light'); onChange(id) }}
              className="flex flex-col items-center gap-0.5 flex-1 py-2 relative"
            >
              {isActive && (
                <motion.div
                  layoutId="nav-indicator"
                  className="absolute inset-0 bg-neon-green/10 rounded-xl"
                  transition={{ type: 'spring', bounce: 0.2, duration: 0.4 }}
                />
              )}
              <div className="relative">
                <Icon size={22} className={isActive ? 'text-neon-green' : 'text-gray-500'} />
                {showBadge && (
                  <span className="absolute -top-1.5 -right-1.5 min-w-[16px] h-4 bg-red-500 rounded-full text-[9px] font-black text-white flex items-center justify-center px-0.5">
                    {unreadCount > 9 ? '9+' : unreadCount}
                  </span>
                )}
              </div>
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
