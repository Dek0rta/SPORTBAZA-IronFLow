import { useState, useEffect, useCallback } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { useTelegram } from './hooks/useTelegram'
import { BottomNav } from './components/BottomNav'
import { Profile } from './screens/Profile'
import { Leaderboard } from './screens/Leaderboard'
import { Competitions } from './screens/Competitions'
import { Notifications } from './screens/Notifications'
import { api } from './services/api'
import type { Tab } from './types'

const TABS: Tab[] = ['profile', 'leaderboard', 'competitions', 'notifications']

const variants = {
  enter:  (dir: number) => ({ x: dir > 0 ? '100%' : '-100%', opacity: 0 }),
  center: { x: 0, opacity: 1 },
  exit:   (dir: number) => ({ x: dir < 0 ? '100%' : '-100%', opacity: 0 }),
}

export default function App() {
  const [tab, setTab]                 = useState<Tab>('profile')
  const [direction, setDirection]     = useState(0)
  const [unreadCount, setUnreadCount] = useState(0)
  const { tg } = useTelegram()

  useEffect(() => {
    tg?.expand()
    tg?.setHeaderColor('#0f172a')
    tg?.setBackgroundColor('#0f172a')
    tg?.enableClosingConfirmation()
  }, [tg])

  useEffect(() => {
    api.notifications()
      .then(ns => setUnreadCount(ns.filter(n => !n.read).length))
      .catch(() => {})
  }, [])

  const handleUnreadChange = useCallback((count: number) => setUnreadCount(count), [])

  const navigate = (next: Tab) => {
    setDirection(TABS.indexOf(next) - TABS.indexOf(tab))
    setTab(next)
  }

  return (
    <div className="bg-slate-950 h-screen flex flex-col overflow-hidden font-sans relative">

      {/* Atmospheric depth blobs — fixed behind all content */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none select-none" style={{ zIndex: 0 }}>
        <div className="animate-float-slow" style={{
          position: 'absolute', top: '-8%', left: '22%',
          width: '500px', height: '500px', borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(168,85,247,0.13) 0%, transparent 65%)',
        }} />
        <div className="animate-float-slow-r" style={{
          position: 'absolute', bottom: '12%', right: '-18%',
          width: '400px', height: '400px', borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(59,130,246,0.1) 0%, transparent 65%)',
        }} />
        <div className="animate-float-slow-d" style={{
          position: 'absolute', top: '48%', left: '-10%',
          width: '280px', height: '280px', borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(57,255,20,0.07) 0%, transparent 65%)',
        }} />
        <div className="animate-float-slow-r" style={{
          animationDelay: '-4s',
          position: 'absolute', bottom: '-8%', left: '45%',
          width: '340px', height: '340px', borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(249,115,22,0.07) 0%, transparent 65%)',
        }} />
      </div>

      <div className="flex-1 relative overflow-hidden" style={{ zIndex: 1 }}>
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
            {tab === 'profile'       && <Profile />}
            {tab === 'leaderboard'   && <Leaderboard />}
            {tab === 'competitions'  && <Competitions />}
            {tab === 'notifications' && <Notifications onUnreadChange={handleUnreadChange} />}
          </motion.div>
        </AnimatePresence>
      </div>

      <div style={{ zIndex: 1 }}>
        <BottomNav active={tab} onChange={navigate} unreadCount={unreadCount} />
      </div>
    </div>
  )
}
