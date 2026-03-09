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
    tg?.setHeaderColor('#070709')
    tg?.setBackgroundColor('#070709')
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
    <div
      className="h-screen flex flex-col overflow-hidden font-sans relative"
      style={{ background: '#070709' }}
    >
      {/* ── LYFESTYLE neon glow blobs ─────────────────────────────────────── */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none select-none" style={{ zIndex: 0 }}>
        {/* UV / purple — top center */}
        <div className="animate-float-slow" style={{
          position: 'absolute', top: '-12%', left: '18%',
          width: '520px', height: '520px', borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(159,0,255,0.18) 0%, transparent 65%)',
        }} />
        {/* Magenta — right */}
        <div className="animate-float-slow-r" style={{
          position: 'absolute', bottom: '10%', right: '-20%',
          width: '440px', height: '440px', borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(255,0,117,0.15) 0%, transparent 65%)',
        }} />
        {/* Acid / yellow-green — left */}
        <div className="animate-float-slow-d" style={{
          position: 'absolute', top: '42%', left: '-14%',
          width: '300px', height: '300px', borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(200,255,0,0.1) 0%, transparent 65%)',
        }} />
        {/* Voltage / orange — bottom */}
        <div className="animate-float-slow-r" style={{
          animationDelay: '-5s',
          position: 'absolute', bottom: '-10%', left: '48%',
          width: '360px', height: '360px', borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(255,77,0,0.1) 0%, transparent 65%)',
        }} />
      </div>

      {/* ── Grain + scanlines overlays ──────────────────────────────────── */}
      <div className="grain-layer" />
      <div className="scanlines-layer" />

      {/* ── Screens ─────────────────────────────────────────────────────── */}
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

      <div style={{ zIndex: 201 }}>
        <BottomNav active={tab} onChange={navigate} unreadCount={unreadCount} />
      </div>
    </div>
  )
}
