import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Bell, CheckCheck, RefreshCw } from 'lucide-react'
import { useTelegram } from '../hooks/useTelegram'
import { api } from '../services/api'
import type { AppNotification } from '../services/api'

const TYPE_CFG: Record<string, { icon: string; color: string }> = {
  confirmed:           { icon: '✅', color: '#39ff14' },
  tournament_started:  { icon: '🚀', color: '#f97316' },
  tournament_finished: { icon: '🏆', color: '#a855f7' },
  record:              { icon: '🏅', color: '#fbbf24' },
  announcement:        { icon: '📢', color: '#3b82f6' },
}

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const m = Math.floor(diff / 60000)
  if (m < 1) return 'только что'
  if (m < 60) return `${m} мин назад`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h} ч назад`
  const d = Math.floor(h / 24)
  return `${d} д назад`
}

interface Props {
  onUnreadChange: (count: number) => void
}

export function Notifications({ onUnreadChange }: Props) {
  const { haptic } = useTelegram()
  const [notifications, setNotifications] = useState<AppNotification[]>([])
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    try {
      const data = await api.notifications()
      setNotifications(data)
      onUnreadChange(data.filter(n => !n.read).length)
    } catch {
      setNotifications([])
    } finally {
      setLoading(false)
    }
  }, [onUnreadChange])

  useEffect(() => { load() }, [load])

  const markAllRead = async () => {
    haptic.impact('light')
    try {
      await api.markNotificationsRead()
      setNotifications(prev => prev.map(n => ({ ...n, read: true })))
      onUnreadChange(0)
    } catch { /* silent */ }
  }

  const unreadCount = notifications.filter(n => !n.read).length

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Header */}
      <div className="shrink-0 px-4 pt-6 pb-3 flex items-center justify-between">
        <h1 className="gradient-text-blue text-2xl font-bold">Уведомления</h1>
        {unreadCount > 0 && (
          <button
            onClick={markAllRead}
            className="flex items-center gap-1.5 text-xs text-neon-green font-semibold active:opacity-70"
          >
            <CheckCheck size={14} />
            Прочитать все
          </button>
        )}
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto overscroll-contain px-4 pb-4 space-y-2">
        {loading ? (
          <div className="flex justify-center pt-12">
            <RefreshCw size={28} className="text-neon-green animate-spin" />
          </div>
        ) : notifications.length === 0 ? (
          <div className="text-center pt-16">
            <Bell size={48} className="mx-auto mb-3 text-gray-700" />
            <p className="text-gray-500 text-sm">Нет уведомлений</p>
          </div>
        ) : (
          <AnimatePresence>
            {notifications.map((n, i) => {
              const cfg = TYPE_CFG[n.type] ?? { icon: '🔔', color: '#6b7280' }
              return (
                <motion.div
                  key={n.id}
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.04 }}
                  className="rounded-2xl border transition-all relative overflow-hidden"
                  style={{
                    background: n.read ? 'rgba(255,255,255,0.025)' : `${cfg.color}10`,
                    borderColor: n.read ? 'rgba(255,255,255,0.06)' : `${cfg.color}48`,
                    boxShadow: n.read ? 'none' : `0 0 18px ${cfg.color}14`,
                  }}
                >
                  {/* Left accent stripe */}
                  <div
                    className="absolute left-0 top-0 bottom-0 w-1 rounded-l-full"
                    style={{ background: n.read ? 'rgba(255,255,255,0.06)' : cfg.color }}
                  />
                  <div className="p-4 pl-5 flex gap-3">
                    <span className="text-2xl shrink-0 mt-0.5">{cfg.icon}</span>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-2 mb-1">
                        <p className="text-white font-semibold text-sm">{n.title}</p>
                        {!n.read && (
                          <span
                            className="w-2 h-2 rounded-full shrink-0"
                            style={{ background: cfg.color, boxShadow: `0 0 6px ${cfg.color}` }}
                          />
                        )}
                      </div>
                      <p className="text-gray-400 text-xs leading-relaxed">{n.body}</p>
                      <p className="text-gray-600 text-[10px] mt-1.5">{relativeTime(n.created_at)}</p>
                    </div>
                  </div>
                </motion.div>
              )
            })}
          </AnimatePresence>
        )}
      </div>
    </div>
  )
}
