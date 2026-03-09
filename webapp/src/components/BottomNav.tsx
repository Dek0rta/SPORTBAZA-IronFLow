import { motion } from 'framer-motion'
import { User, Trophy, Swords, Bell } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { useTelegram } from '../hooks/useTelegram'
import type { Tab } from '../types'

const TABS: { id: Tab; label: string; Icon: LucideIcon }[] = [
  { id: 'profile',       label: 'ПРОФИЛЬ', Icon: User   },
  { id: 'leaderboard',   label: 'ЛАДДЕР',  Icon: Trophy },
  { id: 'competitions',  label: 'ТУРНИРЫ', Icon: Swords },
  { id: 'notifications', label: 'ЛЕНТА',   Icon: Bell   },
]

/** LYFESTYLE accent per tab */
const TAB_COLOR: Record<Tab, string> = {
  profile:       '#c8ff00',   // acid
  leaderboard:   '#ff0075',   // magenta
  competitions:  '#ff4d00',   // voltage
  notifications: '#00f0e0',   // ice
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
        background: 'rgba(7,7,9,0.97)',
        backdropFilter: 'blur(24px)',
        borderTop: '1px solid rgba(255,255,255,0.08)',
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
                animate={{ scale: isActive ? 1.05 : 0.88 }}
                transition={{ type: 'spring', bounce: 0.35, duration: 0.25 }}
                className="relative w-12 h-8 flex items-center justify-center rounded-xl transition-all duration-200"
                style={isActive
                  ? {
                      background: `${color}22`,
                      boxShadow:  `0 0 24px ${color}60, 0 0 48px ${color}22`,
                      border:     `1px solid ${color}40`,
                    }
                  : { border: '1px solid transparent' }
                }
              >
                <Icon
                  size={20}
                  style={{ color: isActive ? color : '#374151' }}
                />
                {showBadge && (
                  <span
                    className="absolute -top-1 -right-0.5 min-w-[16px] h-4 rounded-full text-[9px] font-black text-black flex items-center justify-center px-0.5"
                    style={{
                      background: '#ff0075',
                      boxShadow: '0 0 10px rgba(255,0,117,0.7)',
                    }}
                  >
                    {unreadCount > 9 ? '9+' : unreadCount}
                  </span>
                )}
              </motion.div>

              <span
                className="text-[9px] font-black tracking-widest transition-colors duration-200"
                style={{ color: isActive ? color : '#374151' }}
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
