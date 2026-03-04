interface Props {
  value: number
  size?: number
  strokeWidth?: number
  color?: string
  label?: string
  sublabel?: string
}

export function RingProgress({
  value,
  size = 130,
  strokeWidth = 12,
  color = '#39ff14',
  label,
  sublabel,
}: Props) {
  const r = (size - strokeWidth) / 2
  const circumference = 2 * Math.PI * r
  const offset = circumference - (Math.min(100, Math.max(0, value)) / 100) * circumference

  return (
    <div
      className="relative flex items-center justify-center"
      style={{ width: size, height: size }}
    >
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="rgba(255,255,255,0.08)"
          strokeWidth={strokeWidth}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          style={{ transition: 'stroke-dashoffset 1.2s ease' }}
        />
      </svg>
      <div className="absolute flex flex-col items-center text-center px-2">
        {label && (
          <span className="text-white font-black text-xl leading-none">{label}</span>
        )}
        {sublabel && (
          <span className="text-gray-400 text-[10px] mt-1 leading-tight whitespace-pre-line">
            {sublabel}
          </span>
        )}
      </div>
    </div>
  )
}
