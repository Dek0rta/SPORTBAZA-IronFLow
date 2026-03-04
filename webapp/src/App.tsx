import { useState, useEffect } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { useTelegram } from './hooks/useTelegram'
import { BottomNav } from './components/BottomNav'
import { Dashboard } from './screens/Dashboard'
import { Workout } from './screens/Workout'
import { Stats } from './screens/Stats'
import type { Tab } from './types'

const TABS: Tab[] = ['dashboard', 'workout', 'stats']

const variants = {
  enter: (dir: number) => ({ x: dir > 0 ? '100%' : '-100%', opacity: 0 }),
  center: { x: 0, opacity: 1 },
  exit: (dir: number) => ({ x: dir < 0 ? '100%' : '-100%', opacity: 0 }),
}

export default function App() {
  const [tab, setTab] = useState<Tab>('dashboard')
  const [direction, setDirection] = useState(0)
  const { tg } = useTelegram()

  useEffect(() => {
    tg?.expand()
    tg?.setHeaderColor('#0f172a')
    tg?.setBackgroundColor('#0f172a')
    tg?.enableClosingConfirmation()
  }, [tg])

  const navigate = (next: Tab) => {
    const dir = TABS.indexOf(next) - TABS.indexOf(tab)
    setDirection(dir)
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
            className="absolute inset-0 overflow-y-auto overscroll-contain"
          >
            {tab === 'dashboard' && <Dashboard onStartWorkout={() => navigate('workout')} />}
            {tab === 'workout' && <Workout />}
            {tab === 'stats' && <Stats />}
          </motion.div>
        </AnimatePresence>
      </div>
      <BottomNav active={tab} onChange={navigate} />
    </div>
  )
}
