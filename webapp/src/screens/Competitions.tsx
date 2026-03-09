import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Calendar, Trophy, Users, QrCode, ChevronRight, Trash2, RefreshCw, BarChart2, Dumbbell } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { useTelegram } from '../hooks/useTelegram'
import { BottomSheet } from '../components/BottomSheet'
import { api } from '../services/api'
import type { ApiTournament, MyRegistration, Me, TournamentResults } from '../services/api'

// Registration status config
const STATUS_CFG: Record<string, { label: string; color: string; bg: string }> = {
  approved:   { label: 'Одобрена',        color: '#39ff14', bg: 'rgba(57,255,20,0.12)'   },
  registered: { label: 'Зарегистрирован', color: '#3b82f6', bg: 'rgba(59,130,246,0.12)'  },
  confirmed:  { label: 'Подтверждена',    color: '#39ff14', bg: 'rgba(57,255,20,0.12)'   },
  pending:    { label: 'Ожидает взноса',  color: '#f97316', bg: 'rgba(249,115,22,0.14)'  },
  rejected:   { label: 'Отклонена',       color: '#ef4444', bg: 'rgba(239,68,68,0.12)'   },
}

// Tournament status — each has a distinct gradient for the card top strip
const TOURNAMENT_STATUS_CFG: Record<string, {
  label: string; color: string; gradient: string; badgeBg: string
}> = {
  draft:        { label: 'Черновик',    color: '#64748b', gradient: 'linear-gradient(90deg,#334155,#64748b)', badgeBg: 'rgba(100,116,139,0.14)' },
  registration: { label: 'Регистрация', color: '#60a5fa', gradient: 'linear-gradient(90deg,#1d4ed8,#60a5fa)', badgeBg: 'rgba(96,165,250,0.14)'  },
  active:       { label: 'Идёт',        color: '#fb923c', gradient: 'linear-gradient(90deg,#dc2626,#f97316)', badgeBg: 'rgba(249,115,22,0.14)'  },
  finished:     { label: 'Завершён',    color: '#c084fc', gradient: 'linear-gradient(90deg,#7c3aed,#c084fc)', badgeBg: 'rgba(192,132,252,0.14)' },
}

export function Competitions() {
  const { haptic, tg } = useTelegram()
  const [tab, setTab]           = useState<'upcoming' | 'history' | 'mine'>('upcoming')
  const [tournaments, setTournaments] = useState<ApiTournament[]>([])
  const [myRegs, setMyRegs]     = useState<MyRegistration[]>([])
  const [me, setMe]             = useState<Me | null>(null)
  const [loading, setLoading]   = useState(true)
  const [selected, setSelected]             = useState<MyRegistration | null>(null)
  const [selectedT, setSelectedT]           = useState<ApiTournament | null>(null)
  const [results, setResults]               = useState<TournamentResults | null>(null)
  const [resultsLoading, setResultsLoading] = useState(false)
  const [deleting, setDeleting]             = useState<number | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [ts, meData] = await Promise.all([api.tournaments(), api.me()])
      setTournaments(ts)
      setMe(meData)
      if (meData.authenticated) {
        const regs = await api.myRegistrations().catch(() => [])
        setMyRegs(regs)
      }
    } catch {
      // API not configured — empty state
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const upcoming = tournaments.filter(t => t.status === 'registration' || t.status === 'active')
  const history  = tournaments.filter(t => t.status === 'finished')

  const openResults = async (t: ApiTournament) => {
    haptic.impact('light')
    setResultsLoading(true)
    setResults(null)
    try {
      const data = await api.tournamentResults(t.id)
      setResults(data)
    } catch {
      haptic.error()
    } finally {
      setResultsLoading(false)
    }
  }

  const handleDelete = async (id: number) => {
    haptic.impact('medium')
    setDeleting(id)
    try {
      await api.deleteTournament(id)
      setTournaments(prev => prev.filter(t => t.id !== id))
    } catch {
      haptic.error()
    } finally {
      setDeleting(null)
    }
  }

  return (
    <div className="h-full overflow-y-auto overscroll-contain">
      <div className="px-4 pt-6 pb-8">

        <h1 className="gradient-text-orange text-3xl font-black uppercase tracking-tight mb-5">Соревнования</h1>

        {/* Tab switcher */}
        <div className="grid grid-cols-3 gap-1 rounded-2xl p-1 mb-5" style={{ background: 'rgba(255,255,255,0.05)' }}>
          {([
            ['upcoming', 'Предстоящие'],
            ['history',  'История'],
            ['mine',     'Мои заявки'],
          ] as const).map(([id, label]) => (
            <button
              key={id}
              onClick={() => { haptic.impact('light'); setTab(id) }}
              className={`py-2 rounded-xl text-[10px] font-black uppercase tracking-wider transition-all ${
                tab === id ? 'text-black' : 'text-gray-600'
              }`}
              style={tab === id ? {
                background: 'linear-gradient(135deg,#ff4d00,#ff0075)',
                boxShadow: '0 0 20px rgba(255,77,0,0.45)',
              } : {}}
            >
              {label}
            </button>
          ))}
        </div>

        {loading ? (
          <div className="flex justify-center pt-12">
            <RefreshCw size={28} className="text-orange-400 animate-spin" />
          </div>
        ) : (
          <AnimatePresence mode="wait">

            {tab === 'upcoming' && (
              <TabContent key="upcoming">
                {upcoming.length === 0
                  ? <Empty label="Нет активных турниров" />
                  : upcoming.map((t, i) => (
                    <TournamentCard key={t.id} t={t} index={i}
                      onDetail={() => { haptic.impact('light'); setSelectedT(t) }}
                    />
                  ))
                }
              </TabContent>
            )}

            {tab === 'history' && (
              <TabContent key="history">
                {history.length === 0
                  ? <Empty label="История турниров пуста" />
                  : history.map((t, i) => (
                    <TournamentCard key={t.id} t={t} index={i}
                      onDetail={() => { haptic.impact('light'); setSelectedT(t) }}
                      onResults={() => openResults(t)}
                      isAdmin={me?.is_admin ?? false}
                      onDelete={() => handleDelete(t.id)}
                      deleting={deleting === t.id}
                    />
                  ))
                }
              </TabContent>
            )}

            {tab === 'mine' && (
              <TabContent key="mine">
                {myRegs.length === 0
                  ? <Empty label={me?.authenticated ? 'Нет активных заявок' : 'Войди через Telegram'} />
                  : myRegs.map((reg, i) => {
                    const sc = STATUS_CFG[reg.registration_status] ?? STATUS_CFG.registered
                    return (
                      <motion.button
                        key={reg.id}
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: i * 0.06 }}
                        onClick={() => { haptic.impact('light'); setSelected(reg) }}
                        className="w-full text-left active:scale-[0.98] transition-transform rounded-3xl overflow-hidden"
                        style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.09)' }}
                      >
                        {/* Status color strip */}
                        <div className="h-0.5" style={{ background: sc.color }} />
                        <div className="p-4 space-y-3">
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
                            <InfoRow icon={Dumbbell} text={`Дисциплина: ${reg.discipline}`} />
                            <InfoRow icon={Users}    text={`Весовая: ${reg.weight_class}`} />
                          </div>

                          <div className="flex items-center justify-between pt-1 border-t border-white/5">
                            <span className="text-gray-500 text-xs">
                              {reg.checked_in ? '✅ Чек-ин пройден' : 'Покажи QR на входе'}
                            </span>
                            <div className="flex items-center gap-1.5 text-xs font-semibold px-3 py-1 rounded-xl" style={{ color: sc.color, background: `${sc.color}12` }}>
                              <QrCode size={12} /> QR-билет
                            </div>
                          </div>
                        </div>
                      </motion.button>
                    )
                  })
                }
              </TabContent>
            )}

          </AnimatePresence>
        )}
      </div>

      {/* ── Tournament Detail BottomSheet ─────────────────────── */}
      <BottomSheet isOpen={selectedT !== null} onClose={() => setSelectedT(null)} title={selectedT?.name}>
        {selectedT && (() => {
          const stc = TOURNAMENT_STATUS_CFG[selectedT.status]
          return (
            <div className="space-y-4">
              {/* Header */}
              <div className="rounded-2xl p-4 flex items-center gap-4" style={{ background: `${stc?.badgeBg ?? 'rgba(255,255,255,0.05)'}` }}>
                <span className="text-5xl shrink-0 leading-none">{selectedT.status_emoji}</span>
                <div>
                  <p className="text-white font-bold text-base leading-tight">{selectedT.name}</p>
                  <div className="flex items-center gap-2 mt-1.5">
                    {selectedT.status === 'active' && <span className="live-dot" />}
                    <span className="text-sm font-bold" style={{ color: stc?.color ?? '#6b7280' }}>
                      {stc?.label ?? selectedT.status}
                    </span>
                    <span className="text-gray-500 text-xs">· {selectedT.type_label}</span>
                  </div>
                </div>
              </div>

              <div className="space-y-2">
                <InfoRow icon={Trophy}   text={`Формула: ${selectedT.formula_label}`} />
                <InfoRow icon={Users}    text={`Участников: ${selectedT.participants_count}`} />
                {selectedT.tournament_date && (
                  <InfoRow icon={Calendar} text={selectedT.tournament_date} />
                )}
                {selectedT.description && (
                  <InfoRow icon={Calendar} text={selectedT.description} />
                )}
              </div>

              <div
                className="rounded-2xl p-3 text-center text-sm font-bold"
                style={{
                  color: stc?.color ?? '#6b7280',
                  background: stc?.badgeBg ?? 'rgba(255,255,255,0.04)',
                  border: `1px solid ${stc?.color ?? '#6b7280'}2a`,
                }}
              >
                {selectedT.status === 'registration' && '📋 Регистрация открыта — запишись через бота'}
                {selectedT.status === 'active'       && '🔴 Турнир идёт прямо сейчас'}
                {selectedT.status === 'finished'     && '🏆 Турнир завершён'}
                {selectedT.status === 'draft'        && '📝 Турнир готовится'}
              </div>
            </div>
          )
        })()}
      </BottomSheet>

      {/* ── Results BottomSheet ───────────────────────────────── */}
      <BottomSheet
        isOpen={results !== null || resultsLoading}
        onClose={() => { setResults(null); setResultsLoading(false) }}
        title={results ? `Результаты: ${results.tournament.name}` : 'Загрузка...'}
      >
        {resultsLoading && (
          <div className="flex justify-center py-8">
            <RefreshCw size={28} className="text-purple-400 animate-spin" />
          </div>
        )}
        {results && (
          <div className="space-y-6">
            <p className="text-gray-500 text-xs text-center">
              Формула: <span className="text-gray-300 font-semibold">{results.tournament.formula_label}</span>
              {results.tournament.date && <> · 📅 {results.tournament.date}</>}
            </p>
            {results.categories.length === 0 && (
              <p className="text-gray-500 text-sm text-center py-4">Нет результатов</p>
            )}
            {results.categories.map(cat => (
              <div key={cat.name}>
                <p className="text-white font-bold text-sm mb-2 flex items-center gap-2">
                  <span className="w-1 h-4 rounded-full inline-block bg-purple-400" />
                  {cat.name}
                </p>
                <div className="space-y-1.5">
                  {cat.participants.map((p, idx) => {
                    const placeColors = ['#fbbf24', '#94a3b8', '#f59e0b']
                    const placeColor = idx < 3 && !p.bombed_out ? placeColors[idx] : '#6b7280'
                    return (
                      <div
                        key={idx}
                        className="rounded-2xl px-3 py-2.5 flex items-center gap-3"
                        style={{
                          background: idx === 0 && !p.bombed_out
                            ? 'rgba(251,191,36,0.07)'
                            : 'rgba(255,255,255,0.04)',
                          border: idx === 0 && !p.bombed_out
                            ? '1px solid rgba(251,191,36,0.2)'
                            : '1px solid transparent',
                        }}
                      >
                        <span className="text-sm font-black w-6 text-center shrink-0" style={{ color: placeColor }}>
                          {p.bombed_out ? '—' : `#${p.place}`}
                        </span>
                        <div className="flex-1 min-w-0">
                          <p className="text-white text-sm font-semibold truncate">{p.name}</p>
                          <p className="text-gray-500 text-[10px]">{p.bodyweight} кг</p>
                        </div>
                        <div className="text-right shrink-0">
                          {p.bombed_out
                            ? <p className="text-red-400 text-xs font-semibold">Бомб-аут</p>
                            : <>
                              <p className="text-white font-black text-sm">{p.total} кг</p>
                              {p.score !== null && (
                                <p className="text-gray-500 text-[10px]">{results.tournament.formula_label}: {p.score}</p>
                              )}
                            </>
                          }
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            ))}
          </div>
        )}
      </BottomSheet>

      {/* ── Registration BottomSheet ──────────────────────────── */}
      <BottomSheet isOpen={selected !== null} onClose={() => setSelected(null)} title={selected?.name}>
        {selected && (() => {
          const sc = STATUS_CFG[selected.registration_status] ?? STATUS_CFG.registered
          return (
            <div className="space-y-5">
              {/* QR */}
              <div className="flex flex-col items-center gap-3">
                {selected.qr_token ? (
                  <div
                    className="w-52 h-52 bg-white rounded-3xl flex items-center justify-center overflow-hidden"
                    style={{ boxShadow: '0 0 40px rgba(57,255,20,0.2)' }}
                  >
                    <img
                      src={`https://api.qrserver.com/v1/create-qr-code/?size=192x192&data=${encodeURIComponent(selected.qr_token)}&margin=4`}
                      alt="QR чекин"
                      width={192}
                      height={192}
                      className="rounded-2xl"
                    />
                  </div>
                ) : (
                  <div className="w-52 h-52 bg-white/5 border border-white/10 rounded-3xl flex items-center justify-center">
                    <QrCode size={64} className="text-gray-700" />
                  </div>
                )}
                <p className="text-gray-500 text-xs text-center">
                  {selected.qr_token
                    ? 'Покажи организатору для чекина'
                    : 'QR-код появится после подтверждения заявки'
                  }
                </p>
              </div>

              {/* Status badge */}
              <div className="rounded-2xl p-3 text-center font-bold text-sm"
                style={{ color: sc.color, background: sc.bg }}>
                {sc.label}
              </div>

              {/* Details */}
              <div className="space-y-2">
                <InfoRow icon={Dumbbell} text={`Дисциплина: ${selected.discipline}`} />
                <InfoRow icon={Users}    text={`Весовая категория: ${selected.weight_class}`} />
              </div>

              {selected.description && (
                <div>
                  <p className="text-gray-400 text-xs font-semibold uppercase tracking-widest mb-2">Описание</p>
                  <p className="text-gray-300 text-sm leading-relaxed">{selected.description}</p>
                </div>
              )}
            </div>
          )
        })()}
      </BottomSheet>
    </div>
  )
}

// ── Sub-components ──────────────────────────────────────────────────────────

function TabContent({ children }: { children: React.ReactNode }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.2 }}
      className="space-y-3"
    >
      {children}
    </motion.div>
  )
}

function TournamentCard({
  t, index, onDetail, onResults, isAdmin, onDelete, deleting,
}: {
  t: ApiTournament
  index: number
  onDetail: () => void
  onResults?: () => void
  isAdmin?: boolean
  onDelete?: () => void
  deleting?: boolean
}) {
  const stc = TOURNAMENT_STATUS_CFG[t.status]

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.06 }}
      className="rounded-3xl overflow-hidden"
      style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.09)' }}
    >
      {/* Gradient top strip colored by tournament status */}
      <div className="h-0.5" style={{ background: stc?.gradient ?? 'rgba(255,255,255,0.2)' }} />

      <div className="p-4 space-y-3">
        {/* Header row: emoji + title + participants badge */}
        <div className="flex items-start gap-3">
          <span className="text-4xl shrink-0 leading-none mt-0.5">{t.status_emoji}</span>
          <div className="flex-1 min-w-0">
            <h3 className="text-white font-bold text-sm leading-tight">{t.name}</h3>
            <div className="flex items-center gap-2 mt-1.5 flex-wrap">
              {/* Status badge */}
              <span
                className="inline-flex items-center gap-1.5 text-[11px] font-black px-2 py-0.5 rounded-full"
                style={{ color: stc?.color ?? '#6b7280', background: stc?.badgeBg ?? 'rgba(255,255,255,0.08)' }}
              >
                {t.status === 'active' && <span className="live-dot" />}
                {stc?.label ?? t.status}
              </span>
              {/* Type badge */}
              <span className="text-[11px] font-semibold text-gray-400 px-2 py-0.5 rounded-full" style={{ background: 'rgba(255,255,255,0.07)' }}>
                {t.type_label}
              </span>
            </div>
          </div>
          {/* Participants */}
          <div className="flex items-center gap-1 px-2 py-1 rounded-xl shrink-0" style={{ background: 'rgba(255,255,255,0.07)' }}>
            <Users size={11} className="text-gray-500" />
            <span className="text-gray-300 text-xs font-bold">{t.participants_count}</span>
          </div>
        </div>

        {/* Info rows */}
        <div className="space-y-1.5">
          <InfoRow icon={Trophy}   text={`Формула: ${t.formula_label}`} />
          {t.tournament_date
            ? <InfoRow icon={Calendar} text={t.tournament_date} accent />
            : t.description && <InfoRow icon={Calendar} text={t.description} />
          }
        </div>

        {/* Action buttons */}
        <div className="flex gap-2 pt-1">
          <button
            onClick={onDetail}
            className="flex-1 h-10 rounded-2xl font-semibold text-sm flex items-center justify-center gap-1.5 active:scale-95 transition-transform text-white"
            style={{ background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.1)' }}
          >
            Подробнее <ChevronRight size={14} />
          </button>

          {onResults && t.status === 'finished' && (
            <button
              onClick={onResults}
              className="w-10 h-10 rounded-2xl flex items-center justify-center shrink-0 active:scale-95 transition-transform"
              style={{ background: 'rgba(192,132,252,0.12)', border: '1px solid rgba(192,132,252,0.25)' }}
              title="Результаты"
            >
              <BarChart2 size={16} style={{ color: '#c084fc' }} />
            </button>
          )}

          {isAdmin && onDelete && t.status === 'finished' && (
            <button
              onClick={onDelete}
              disabled={deleting}
              className="w-10 h-10 rounded-2xl flex items-center justify-center shrink-0 active:scale-95 transition-transform disabled:opacity-40"
              style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.2)' }}
            >
              {deleting
                ? <RefreshCw size={16} className="text-red-400 animate-spin" />
                : <Trash2 size={16} className="text-red-400" />
              }
            </button>
          )}
        </div>
      </div>
    </motion.div>
  )
}

function InfoRow({ icon: Icon, text, accent }: { icon: LucideIcon; text: string; accent?: boolean }) {
  return (
    <div className="flex items-center gap-2 text-xs">
      <Icon size={13} className="shrink-0" style={{ color: accent ? '#fb923c' : '#4b5563' }} />
      <span className="line-clamp-1" style={{ color: accent ? '#fdba74' : '#9ca3af' }}>
        {text}
      </span>
    </div>
  )
}

function Empty({ label }: { label: string }) {
  return (
    <div className="text-center py-16">
      <div className="w-16 h-16 rounded-3xl mx-auto mb-4 flex items-center justify-center" style={{ background: 'rgba(249,115,22,0.1)' }}>
        <Trophy size={28} className="text-orange-400 opacity-60" />
      </div>
      <p className="text-gray-500 text-sm">{label}</p>
    </div>
  )
}
