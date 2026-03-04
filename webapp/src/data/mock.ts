export const mockWeeklyActivity = {
  goal: 5,
  completed: 3,
  calories: 1840,
  caloriesGoal: 2500,
}

export const mockLastWorkout = {
  date: '28 февраля 2026',
  exercises: ['Приседания', 'Жим лёжа', 'Становая тяга'],
  totalVolume: 8450,
  duration: 75,
  sets: 18,
}

export const mockExercises = [
  { id: 1, name: 'Приседания',   icon: '🏋️', category: 'Ноги',   maxWeight: 180 },
  { id: 2, name: 'Жим лёжа',    icon: '💪', category: 'Грудь',  maxWeight: 130 },
  { id: 3, name: 'Становая тяга',icon: '⚡', category: 'Спина',  maxWeight: 220 },
  { id: 4, name: 'Жим стоя',    icon: '🔝', category: 'Плечи',  maxWeight: 85  },
  { id: 5, name: 'Подтягивания', icon: '🎯', category: 'Спина',  maxWeight: 30  },
  { id: 6, name: 'Тяга штанги', icon: '🔱', category: 'Спина',  maxWeight: 110 },
]

const makeProgressData = (start: number, steps: number[]) =>
  steps.map((_, i) => {
    const d = new Date('2026-01-01')
    d.setDate(d.getDate() + i * 7)
    const date = `${String(d.getDate()).padStart(2, '0')}.${String(d.getMonth() + 1).padStart(2, '0')}`
    const weight = start + steps.slice(0, i + 1).reduce((a, b) => a + b, 0)
    return { date, weight }
  })

export const mockStatsData = {
  squat:    makeProgressData(140, [0, 5, 5, 5,   5,   0, 5, 5]),
  bench:    makeProgressData(100, [0, 2.5, 0, 2.5, 5, 0, 2.5, 2.5]),
  deadlift: makeProgressData(180, [0, 10,  0, 10,  5,  5, 5,   5]),
}
