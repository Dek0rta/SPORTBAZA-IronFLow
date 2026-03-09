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
            className="fixed inset-0 z-40"
            style={{ background: 'rgba(0,0,0,0.75)', backdropFilter: 'blur(6px)' }}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />
          <motion.div
            className="fixed bottom-0 left-0 right-0 z-50 rounded-t-3xl px-5 pt-4 pb-10"
            style={{
              background: 'linear-gradient(180deg, #0e0e12 0%, #070709 100%)',
              borderTop: '1px solid rgba(255,255,255,0.09)',
            }}
            initial={{ y: '100%' }}
            animate={{ y: 0 }}
            exit={{ y: '100%' }}
            transition={{ type: 'spring', damping: 30, stiffness: 300 }}
          >
            {/* LYFESTYLE rainbow drag handle */}
            <div
              className="w-14 h-1.5 rounded-full mx-auto mb-5"
              style={{
                background: 'linear-gradient(90deg, #9f00ff, #ff0075, #ff4d00, #c8ff00)',
                boxShadow:  '0 0 12px rgba(200,255,0,0.3)',
              }}
            />
            {title && (
              <h3 className="text-white font-black text-lg mb-4 uppercase tracking-wider">{title}</h3>
            )}
            {children}
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
