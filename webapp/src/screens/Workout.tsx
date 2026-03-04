import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Plus, CheckCircle, ChevronRight } from 'lucide-react'
import { useTelegram } from '../hooks/useTelegram'
import { BottomSheet } from '../components/BottomSheet'
import { mockExercises } from '../data/mock'

interface WorkoutSet {
  weight: string
  reps: string
}

interface WorkoutEntry {
  exerciseId: number
  sets: WorkoutSet[]
}

export function Workout() {
  const { haptic, tg } = useTelegram()
  const [entries, setEntries] = useState<WorkoutEntry[]>([])
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [weight, setWeight] = useState('')
  const [reps, setReps] = useState('')
  const [done, setDone] = useState(false)

  const selectedEx = mockExercises.find((e) => e.id === selectedId)
  const totalSets = entries.reduce((s, e) => s + e.sets.length, 0)

  const addSet = () => {
    if (!selectedId || !weight || !reps) return
    haptic.impact('light')
    setEntries((prev) => {
      const existing = prev.find((e) => e.exerciseId === selectedId)
      if (existing) {
        return prev.map((e) =>
          e.exerciseId === selectedId
            ? { ...e, sets: [...e.sets, { weight, reps }] }
            : e,
        )
      }
      return [...prev, { exerciseId: selectedId, sets: [{ weight, reps }] }]
    })
    setWeight('')
    setReps('')
  }

  const finishWorkout = () => {
    haptic.success()
    tg?.HapticFeedback?.notificationOccurred('success')
    setDone(true)
    setEntries([])
    setTimeout(() => setDone(false), 3500)
  }

  return (
    <div className="px-4 pt-6 pb-8">
      <div className="flex items-center justify-between mb-5">
        <h1 className="text-white text-2xl font-bold">Тренировка</h1>
        {totalSets > 0 && (
          <span className="text-neon-green text-sm font-semibold bg-neon-green/10 px-3 py-1 rounded-full">
            {totalSets} подх.
          </span>
        )}
      </div>

      {/* Success banner */}
      <AnimatePresence>
        {done && (
          <motion.div
            initial={{ opacity: 0, y: -16 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -16 }}
            className="mb-4 p-4 bg-neon-green/15 border border-neon-green/30 rounded-2xl flex items-center gap-3"
          >
            <CheckCircle size={22} className="text-neon-green shrink-0" />
            <div>
              <p className="text-white font-semibold">Тренировка завершена!</p>
              <p className="text-gray-400 text-sm">Результаты сохранены</p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Exercise list */}
      <div className="space-y-3">
        {mockExercises.map((ex, i) => {
          const entry = entries.find((e) => e.exerciseId === ex.id)
          return (
            <motion.button
              key={ex.id}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.05 }}
              onClick={() => {
                haptic.impact('light')
                setSelectedId(ex.id)
              }}
              className="w-full glass-card flex items-center justify-between active:scale-[0.98] transition-transform text-left"
            >
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-xl bg-white/5 flex items-center justify-center text-2xl shrink-0">
                  {ex.icon}
                </div>
                <div>
                  <p className="text-white font-semibold text-sm">{ex.name}</p>
                  <p className="text-gray-500 text-xs">
                    {ex.category} · Макс: {ex.maxWeight} кг
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                {entry && (
                  <span className="text-neon-green text-xs font-black bg-neon-green/10 px-2 py-0.5 rounded-full">
                    {entry.sets.length}×
                  </span>
                )}
                <ChevronRight size={18} className="text-gray-600" />
              </div>
            </motion.button>
          )
        })}
      </div>

      {/* Finish button */}
      {totalSets > 0 && (
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mt-6">
          <button
            onClick={finishWorkout}
            className="w-full h-14 bg-gradient-to-r from-orange-500 to-orange-400 text-white rounded-2xl font-black text-base flex items-center justify-center gap-2 shadow-[0_0_25px_rgba(249,115,22,0.3)] active:scale-95 transition-transform"
          >
            <CheckCircle size={20} />
            Завершить тренировку
          </button>
        </motion.div>
      )}

      {/* Bottom Sheet */}
      <BottomSheet
        isOpen={selectedId !== null}
        onClose={() => { setSelectedId(null); setWeight(''); setReps('') }}
        title={selectedEx ? `${selectedEx.icon} ${selectedEx.name}` : undefined}
      >
        {selectedEx && (
          <div className="space-y-4">
            {/* Previous sets */}
            {entries.find((e) => e.exerciseId === selectedEx.id)?.sets.map((s, i) => (
              <div key={i} className="flex items-center gap-3 py-2 border-b border-white/5 text-sm">
                <span className="text-gray-500 w-16">Подход {i + 1}</span>
                <span className="text-white font-semibold">{s.weight} кг</span>
                <span className="text-gray-500">×</span>
                <span className="text-white font-semibold">{s.reps} повт.</span>
              </div>
            ))}

            {/* Inputs */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-gray-400 text-xs mb-1.5 block">Вес (кг)</label>
                <input
                  type="number"
                  inputMode="decimal"
                  value={weight}
                  onChange={(e) => setWeight(e.target.value)}
                  placeholder={String(selectedEx.maxWeight)}
                  className="w-full h-12 bg-white/5 border border-white/10 rounded-xl text-white text-center text-lg font-semibold focus:outline-none focus:border-neon-green/60 transition-colors"
                />
              </div>
              <div>
                <label className="text-gray-400 text-xs mb-1.5 block">Повторения</label>
                <input
                  type="number"
                  inputMode="numeric"
                  value={reps}
                  onChange={(e) => setReps(e.target.value)}
                  placeholder="5"
                  className="w-full h-12 bg-white/5 border border-white/10 rounded-xl text-white text-center text-lg font-semibold focus:outline-none focus:border-neon-green/60 transition-colors"
                />
              </div>
            </div>

            <button
              onClick={addSet}
              disabled={!weight || !reps}
              className="w-full h-12 bg-neon-green text-black rounded-xl font-bold flex items-center justify-center gap-2 disabled:opacity-40 disabled:pointer-events-none active:scale-95 transition-transform shadow-[0_0_20px_rgba(57,255,20,0.2)]"
            >
              <Plus size={18} />
              Добавить подход
            </button>
          </div>
        )}
      </BottomSheet>
    </div>
  )
}
