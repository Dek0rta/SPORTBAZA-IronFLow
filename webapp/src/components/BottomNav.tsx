import { motion } from 'framer-motion'
import { User, Trophy, Swords, Bell } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { useTelegram } from '../hooks/useTelegram'
import type { Tab } from '../types'

const TABS: { id: Tab; label: string; Icon: LucideIcon }[] = [
  { id: 'profile',       label: 'Профиль', Icon: User   },
  { id: 'leaderboard',   label: 'Ладдер',  Icon: Trophy },
  { id: 'competitions',  label: 'Турниры', Icon: Swords },
  { id: 'notifications', label: 'Лента',   Icon: Bell   },
]

/** Each tab has its own accent color */
const TAB_COLOR: Record<Tab, string> = {
  profile:       '#39ff14',
  leaderboard:   '#fbbf24',
  competitions:  '#f97316',
  notifications: '#3b82f6',
}

interface Props {
  active: Tab
  onChange: (tab: Tab) => void
  unreadCount?: number
}

export function BottomNav({ active, onChange, unreadCount = 0 }: Props) {
  const { haptic } = useTelegram()

  return (
    <nav
      className="shrink-0 pb-safe"
      style={{
        background: 'rgba(10,15,30,0.97)',
        backdropFilter: 'blur(24px)',
        borderTop: '1px solid rgba(255,255,255,0.07)',
      }}
    >
      <div className="flex items-center justify-around h-16 px-1">
        {TABS.map(({ id, label, Icon }) => {
          const isActive  = id === active
          const color     = TAB_COLOR[id]
          const showBadge = id === 'notifications' && unreadCount > 0

          return (
            <button
              key={id}
              onClick={() => { haptic.impact('light'); onChange(id) }}
              className="flex flex-col items-center gap-0.5 flex-1 py-1.5"
            >
              <motion.div
                animate={{ scale: isActive ? 1 : 0.88 }}
                transition={{ type: 'spring', bounce: 0.35, duration: 0.25 }}
                className="relative w-12 h-8 flex items-center justify-center rounded-xl transition-all duration-200"
                style={isActive
                  ? { background: `${color}28`, boxShadow: `0 0 22px ${color}55, 0 0 44px ${color}20` }
                  : {}
                }
              >
                <Icon
                  size={21}
                  style={{ color: isActive ? color : '#4b5563' }}
                />
                {showBadge && (
                  <span
                    className="absolute -top-1 -right-0.5 min-w-[16px] h-4 rounded-full text-[9px] font-black text-white flex items-center justify-center px-0.5"
                    style={{ background: '#ef4444', boxShadow: '0 0 8px rgba(239,68,68,0.5)' }}
                  >
                    {unreadCount > 9 ? '9+' : unreadCount}
                  </span>
                )}
              </motion.div>

              <span
                className={`text-[10px] transition-colors duration-200 ${isActive ? 'font-black' : 'font-semibold'}`}
                style={{ color: isActive ? color : '#4b5563' }}
              >
                {label}
              </span>
            </button>
          )
        })}
      </div>
    </nav>
  )
}
