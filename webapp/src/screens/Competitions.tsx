import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Calendar, Trophy, Users, QrCode, ChevronRight, Trash2, RefreshCw, BarChart2 } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { useTelegram } from '../hooks/useTelegram'
import { BottomSheet } from '../components/BottomSheet'
import { api } from '../services/api'
import type { ApiTournament, MyRegistration, Me, TournamentResults } from '../services/api'

const STATUS_CFG: Record<string, { label: string; color: string; bg: string }> = {
  approved:   { label: 'Одобрена',        color: '#39ff14', bg: 'rgba(57,255,20,0.1)'   },
  registered: { label: 'Зарегистрирован', color: '#3b82f6', bg: 'rgba(59,130,246,0.12)' },
  confirmed:  { label: 'Подтверждена',    color: '#39ff14', bg: 'rgba(57,255,20,0.1)'   },
  pending:    { label: 'Ожидает взноса',  color: '#f97316', bg: 'rgba(249,115,22,0.12)' },
  rejected:   { label: 'Отклонена',       color: '#ef4444', bg: 'rgba(239,68,68,0.12)'  },
}

const TOURNAMENT_STATUS_CFG: Record<string, { label: string; color: string }> = {
  draft:        { label: 'Черновик',      color: '#6b7280' },
  registration: { label: 'Регистрация',   color: '#3b82f6' },
  active:       { label: 'Идёт',          color: '#f97316' },
  finished:     { label: 'Завершён',      color: '#39ff14' },
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

        <h1 className="text-white text-2xl font-bold mb-4">Соревнования</h1>

        {/* Tab switcher */}
        <div className="grid grid-cols-3 gap-1 bg-white/5 rounded-2xl p-1 mb-5">
          {([
            ['upcoming', 'Предстоящие'],
            ['history',  'История'],
            ['mine',     'Мои заявки'],
          ] as const).map(([id, label]) => (
            <button
              key={id}
              onClick={() => { haptic.impact('light'); setTab(id) }}
              className={`py-2 rounded-xl text-xs font-semibold transition-all ${
                tab === id ? 'bg-neon-green text-black' : 'text-gray-400'
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {loading ? (
          <div className="flex justify-center pt-12">
            <RefreshCw size={28} className="text-neon-green animate-spin" />
          </div>
        ) : (
          <AnimatePresence mode="wait">

            {/* ── Upcoming ──────────────────────────────────────── */}
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

            {/* ── History ───────────────────────────────────────── */}
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

            {/* ── My registrations ──────────────────────────────── */}
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
                          <InfoRow icon={Trophy}   text={`Дисциплина: ${reg.discipline}`} />
                          <InfoRow icon={Users}    text={`Весовая: ${reg.weight_class}`} />
                          <InfoRow icon={Calendar} text={`Статус турнира: ${TOURNAMENT_STATUS_CFG[reg.tournament_status]?.label ?? reg.tournament_status}`} />
                        </div>
                        <div className="flex items-center justify-between pt-1 border-t border-white/5">
                          <span className="text-gray-500 text-xs">
                            {reg.checked_in ? '✅ Чек-ин пройден' : 'QR-билет и правила'}
                          </span>
                          <div className="flex items-center gap-1 text-neon-green text-xs font-semibold">
                            <QrCode size={13} /> Открыть
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
      <BottomSheet
        isOpen={selectedT !== null}
        onClose={() => setSelectedT(null)}
        title={selectedT?.name}
      >
        {selectedT && (
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <span className="text-2xl">{selectedT.status_emoji}</span>
              <div>
                <p className="text-white font-bold">{selectedT.name}</p>
                <p className="text-xs font-bold" style={{ color: TOURNAMENT_STATUS_CFG[selectedT.status]?.color ?? '#6b7280' }}>
                  {TOURNAMENT_STATUS_CFG[selectedT.status]?.label ?? selectedT.status} · {selectedT.type_label}
                </p>
              </div>
            </div>
            <div className="space-y-2">
              <InfoRow icon={Trophy}   text={`Формула: ${selectedT.formula_label}`} />
              <InfoRow icon={Users}    text={`Участников: ${selectedT.participants_count}`} />
              {selectedT.description && (
                <InfoRow icon={Calendar} text={selectedT.description} />
              )}
            </div>
            <div
              className="rounded-2xl p-3 text-center text-sm font-bold"
              style={{
                color: TOURNAMENT_STATUS_CFG[selectedT.status]?.color ?? '#6b7280',
                background: 'rgba(255,255,255,0.04)',
                border: `1px solid ${TOURNAMENT_STATUS_CFG[selectedT.status]?.color ?? '#6b7280'}33`,
              }}
            >
              {selectedT.status === 'registration' && '📋 Регистрация открыта — запишись через бота'}
              {selectedT.status === 'active'       && '🔴 Турнир идёт прямо сейчас'}
              {selectedT.status === 'finished'     && '🏆 Турнир завершён'}
              {selectedT.status === 'draft'        && '📝 Турнир готовится'}
            </div>
          </div>
        )}
      </BottomSheet>

      {/* ── Results BottomSheet ───────────────────────────────── */}
      <BottomSheet
        isOpen={results !== null || resultsLoading}
        onClose={() => { setResults(null); setResultsLoading(false) }}
        title={results ? `Результаты: ${results.tournament.name}` : 'Загрузка...'}
      >
        {resultsLoading && (
          <div className="flex justify-center py-8">
            <RefreshCw size={28} className="text-neon-green animate-spin" />
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
                <p className="text-white font-bold text-sm mb-2">{cat.name}</p>
                <div className="space-y-1.5">
                  {cat.participants.map((p, idx) => (
                    <div
                      key={idx}
                      className="rounded-xl px-3 py-2.5 flex items-center gap-3"
                      style={{ background: idx === 0 && !p.bombed_out ? 'rgba(57,255,20,0.08)' : 'rgba(255,255,255,0.04)' }}
                    >
                      <span className="text-sm font-black w-6 text-center shrink-0" style={{ color: idx === 0 ? '#39ff14' : '#6b7280' }}>
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
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </BottomSheet>

      {/* ── Registration BottomSheet ──────────────────────────── */}
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
                {selected.qr_token
                  ? <>Токен: <span className="text-gray-300 font-mono">{selected.qr_token}</span></>
                  : 'QR-код появится после подтверждения заявки'
                }
              </p>
            </div>

            {/* Details */}
            <div className="space-y-2">
              <InfoRow icon={Trophy}   text={`Дисциплина: ${selected.discipline}`} />
              <InfoRow icon={Users}    text={`Весовая категория: ${selected.weight_class}`} />
              <InfoRow icon={Calendar} text={`Статус: ${TOURNAMENT_STATUS_CFG[selected.tournament_status]?.label ?? selected.tournament_status}`} />
            </div>

            {/* Description */}
            {selected.description && (
              <div>
                <p className="text-gray-400 text-xs font-semibold uppercase tracking-widest mb-2">
                  Описание
                </p>
                <p className="text-gray-300 text-sm leading-relaxed">{selected.description}</p>
              </div>
            )}
          </div>
        )}
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
      className="space-y-4"
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
      className="glass-card space-y-3"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <h3 className="text-white font-bold text-sm leading-tight">{t.name}</h3>
          <span className="text-[10px] font-bold" style={{ color: stc?.color ?? '#6b7280' }}>
            {t.status_emoji} {stc?.label ?? t.status} · {t.type_label}
          </span>
        </div>
        <span className="text-neon-green font-black text-xs shrink-0">
          {t.participants_count} уч.
        </span>
      </div>

      <div className="space-y-1.5">
        <InfoRow icon={Trophy}   text={`Формула: ${t.formula_label}`} />
        {t.description && (
          <InfoRow icon={Calendar} text={t.description} />
        )}
      </div>

      <div className="flex gap-2">
        <button
          onClick={onDetail}
          className="flex-1 h-10 bg-white/5 border border-white/10 rounded-xl text-white text-sm font-semibold flex items-center justify-center gap-2 active:scale-95 transition-transform"
        >
          Подробнее <ChevronRight size={14} />
        </button>

        {onResults && t.status === 'finished' && (
          <button
            onClick={onResults}
            className="w-10 h-10 bg-neon-green/10 border border-neon-green/20 rounded-xl flex items-center justify-center shrink-0 active:scale-95 transition-transform"
            title="Результаты"
          >
            <BarChart2 size={16} className="text-neon-green" />
          </button>
        )}

        {isAdmin && onDelete && t.status === 'finished' && (
          <button
            onClick={onDelete}
            disabled={deleting}
            className="w-10 h-10 bg-red-500/10 border border-red-500/20 rounded-xl flex items-center justify-center shrink-0 active:scale-95 transition-transform disabled:opacity-40"
          >
            {deleting
              ? <RefreshCw size={16} className="text-red-400 animate-spin" />
              : <Trash2 size={16} className="text-red-400" />
            }
          </button>
        )}
      </div>
    </motion.div>
  )
}

function InfoRow({ icon: Icon, text, accent }: { icon: LucideIcon; text: string; accent?: boolean }) {
  return (
    <div className="flex items-center gap-2 text-xs">
      <Icon size={13} className={`shrink-0 ${accent ? 'text-orange-400' : 'text-gray-500'}`} />
      <span className={`${accent ? 'text-orange-400 font-semibold' : 'text-gray-400'} line-clamp-1`}>
        {text}
      </span>
    </div>
  )
}

function Empty({ label }: { label: string }) {
  return (
    <div className="text-center py-16">
      <Trophy size={48} className="mx-auto mb-3 text-gray-700" />
      <p className="text-gray-500 text-sm">{label}</p>
    </div>
  )
}
