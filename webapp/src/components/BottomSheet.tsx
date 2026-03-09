import { ReactNode } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

interface Props {
  isOpen: boolean
  onClose: () => void
  title?: string
  children: ReactNode
}

export function BottomSheet({ isOpen, onClose, title, children }: Props) {
  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            className="fixed inset-0 bg-black/60 z-40 backdrop-blur-sm"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />
          <motion.div
            className="fixed bottom-0 left-0 right-0 z-50 rounded-t-3xl border-t border-white/10 px-5 pt-4 pb-10"
            style={{ background: 'linear-gradient(180deg, #111827 0%, #0c1220 100%)' }}
            initial={{ y: '100%' }}
            animate={{ y: 0 }}
            exit={{ y: '100%' }}
            transition={{ type: 'spring', damping: 30, stiffness: 300 }}
          >
            {/* Gradient drag handle */}
            <div
              className="w-12 h-1.5 rounded-full mx-auto mb-4"
              style={{ background: 'linear-gradient(90deg, rgba(168,85,247,0.7), rgba(57,255,20,0.6))' }}
            />
            {title && (
              <h3 className="text-white font-semibold text-lg mb-4">{title}</h3>
            )}
            {children}
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
