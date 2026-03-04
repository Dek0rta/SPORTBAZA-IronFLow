import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { MapPin, Calendar, Trophy, Users, QrCode, ChevronRight } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { useTelegram } from '../hooks/useTelegram'
import { BottomSheet } from '../components/BottomSheet'
import { mockTournaments, mockMyRegistrations, STATUS_CONFIG } from '../data/mock'
import type { MyRegistration } from '../data/mock'

export function Competitions() {
  const { haptic } = useTelegram()
  const [tab, setTab]           = useState<'upcoming' | 'mine'>('upcoming')
  const [selected, setSelected] = useState<MyRegistration | null>(null)

  return (
    <div className="h-full overflow-y-auto overscroll-contain">
      <div className="px-4 pt-6 pb-8">

        <h1 className="text-white text-2xl font-bold mb-4">Соревнования</h1>

        {/* Tab switcher */}
        <div className="grid grid-cols-2 gap-1 bg-white/5 rounded-2xl p-1 mb-5">
          {(['upcoming', 'mine'] as const).map(id => (
            <button
              key={id}
              onClick={() => { haptic.impact('light'); setTab(id) }}
              className={`py-2.5 rounded-xl text-sm font-semibold transition-all ${
                tab === id ? 'bg-neon-green text-black' : 'text-gray-400'
              }`}
            >
              {id === 'upcoming' ? 'Предстоящие' : 'Мои заявки'}
            </button>
          ))}
        </div>

        <AnimatePresence mode="wait">

          {/* ── Upcoming tournaments ──────────────────────────── */}
          {tab === 'upcoming' && (
            <motion.div
              key="upcoming"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
              transition={{ duration: 0.2 }}
              className="space-y-4"
            >
              {mockTournaments.map((t, i) => (
                <motion.div
                  key={t.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.06 }}
                  className="glass-card space-y-3"
                >
                  <div className="flex items-start justify-between gap-2">
                    <h3 className="text-white font-bold text-sm leading-tight flex-1">{t.name}</h3>
                    <span className="text-neon-green font-black text-sm shrink-0">{t.prize}</span>
                  </div>

                  <div className="space-y-1.5">
                    <InfoRow icon={Calendar} text={t.date} />
                    <InfoRow icon={MapPin}   text={t.location} />
                    <InfoRow icon={Trophy}   text={t.discipline} />
                    <InfoRow
                      icon={Users}
                      text={`Осталось мест: ${t.slotsLeft} из ${t.slotsTotal}`}
                      accent={t.slotsLeft <= 5}
                    />
                  </div>

                  <button
                    onClick={() => haptic.impact('light')}
                    className="w-full h-10 bg-white/5 border border-white/10 rounded-xl text-white text-sm font-semibold flex items-center justify-center gap-2 active:scale-95 transition-transform"
                  >
                    Подробнее <ChevronRight size={14} />
                  </button>
                </motion.div>
              ))}
            </motion.div>
          )}

          {/* ── My registrations ─────────────────────────────── */}
          {tab === 'mine' && (
            <motion.div
              key="mine"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.2 }}
              className="space-y-4"
            >
              {mockMyRegistrations.length === 0 ? (
                <div className="text-center py-16">
                  <Trophy size={48} className="mx-auto mb-3 text-gray-700" />
                  <p className="text-gray-500">Нет активных заявок</p>
                </div>
              ) : (
                mockMyRegistrations.map((reg, i) => {
                  const sc = STATUS_CONFIG[reg.status]
                  return (
                    <motion.button
                      key={reg.id}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: i * 0.06 }}
                      onClick={() => { haptic.impact('light'); setSelected(reg) }}
                      className="w-full glass-card text-left space-y-3 active:scale-[0.98] transition-transform"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <h3 className="text-white font-bold text-sm leading-tight flex-1">{reg.name}</h3>
                        <span
                          className="text-[11px] font-black px-2.5 py-1 rounded-full shrink-0"
                          style={{ color: sc.color, background: sc.bg }}
                        >
                          {sc.label}
                        </span>
                      </div>

                      <div className="space-y-1.5">
                        <InfoRow icon={Calendar} text={reg.date} />
                        <InfoRow icon={MapPin}   text={reg.location} />
                        <InfoRow icon={Trophy}   text={`Дисциплина: ${reg.discipline}`} />
                        <InfoRow icon={Users}    text={`Весовая категория: ${reg.weightClass}`} />
                      </div>

                      <div className="flex items-center justify-between pt-1 border-t border-white/5">
                        <span className="text-gray-500 text-xs">QR-билет и правила</span>
                        <div className="flex items-center gap-1 text-neon-green text-xs font-semibold">
                          <QrCode size={13} /> Открыть
                        </div>
                      </div>
                    </motion.button>
                  )
                })
              )}
            </motion.div>
          )}

        </AnimatePresence>
      </div>

      {/* ── Registration detail BottomSheet ──────────────────── */}
      <BottomSheet
        isOpen={selected !== null}
        onClose={() => setSelected(null)}
        title={selected?.name}
      >
        {selected && (
          <div className="space-y-5">
            {/* QR */}
            <div className="flex flex-col items-center gap-3">
              <div className="w-52 h-52 bg-white rounded-3xl flex items-center justify-center shadow-[0_0_40px_rgba(57,255,20,0.15)]">
                <QrCode size={128} className="text-black" />
              </div>
              <p className="text-gray-500 text-xs text-center">
                Токен:{' '}
                <span className="text-gray-300 font-mono">{selected.qrToken}</span>
              </p>
            </div>

            {/* Details */}
            <div className="space-y-2">
              <InfoRow icon={Trophy}   text={`Дисциплина: ${selected.discipline}`} />
              <InfoRow icon={Users}    text={`Весовая категория: ${selected.weightClass}`} />
              <InfoRow icon={Calendar} text={selected.date} />
              <InfoRow icon={MapPin}   text={selected.location} />
            </div>

            {/* Rules */}
            <div>
              <p className="text-gray-400 text-xs font-semibold uppercase tracking-widest mb-2">
                Правила ивента
              </p>
              <div className="space-y-2">
                {selected.rules.map((rule, i) => (
                  <div key={i} className="flex items-start gap-2">
                    <span className="text-neon-green font-bold text-sm shrink-0 mt-0.5">·</span>
                    <span className="text-gray-300 text-sm">{rule}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </BottomSheet>
    </div>
  )
}

function InfoRow({
  icon: Icon, text, accent,
}: {
  icon: LucideIcon
  text: string
  accent?: boolean
}) {
  return (
    <div className="flex items-center gap-2 text-xs">
      <Icon size={13} className={accent ? 'text-orange-400 shrink-0' : 'text-gray-500 shrink-0'} />
      <span className={accent ? 'text-orange-400 font-semibold' : 'text-gray-400'}>{text}</span>
    </div>
  )
}
