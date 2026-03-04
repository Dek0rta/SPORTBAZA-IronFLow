import { useState, useEffect } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { useTelegram } from './hooks/useTelegram'
import { BottomNav } from './components/BottomNav'
import { Profile } from './screens/Profile'
import { Leaderboard } from './screens/Leaderboard'
import { Competitions } from './screens/Competitions'
import type { Tab } from './types'

const TABS: Tab[] = ['profile', 'leaderboard', 'competitions']

const variants = {
  enter: (dir: number) => ({ x: dir > 0 ? '100%' : '-100%', opacity: 0 }),
  center: { x: 0, opacity: 1 },
  exit:  (dir: number) => ({ x: dir < 0 ? '100%' : '-100%', opacity: 0 }),
}

export default function App() {
  const [tab, setTab]           = useState<Tab>('profile')
  const [direction, setDirection] = useState(0)
  const { tg } = useTelegram()

  useEffect(() => {
    tg?.expand()
    tg?.setHeaderColor('#0f172a')
    tg?.setBackgroundColor('#0f172a')
    tg?.enableClosingConfirmation()
  }, [tg])

  const navigate = (next: Tab) => {
    setDirection(TABS.indexOf(next) - TABS.indexOf(tab))
    setTab(next)
  }

  return (
    <div className="bg-slate-950 h-screen flex flex-col overflow-hidden font-sans">
      <div className="flex-1 relative overflow-hidden">
        <AnimatePresence custom={direction} mode="wait">
          <motion.div
            key={tab}
            custom={direction}
            variants={variants}
            initial="enter"
            animate="center"
            exit="exit"
            transition={{ type: 'tween', ease: 'easeInOut', duration: 0.22 }}
            className="absolute inset-0"
          >
            {tab === 'profile'      && <Profile />}
            {tab === 'leaderboard'  && <Leaderboard />}
            {tab === 'competitions' && <Competitions />}
          </motion.div>
        </AnimatePresence>
      </div>
      <BottomNav active={tab} onChange={navigate} />
    </div>
  )
}
