import { useEffect } from 'react';
import { isEditableTarget } from '../utils/accessibility';

/**
 * Global keyboard shortcuts for the accessibility widget.
 * Uses Alt+Shift+* to avoid conflicting with browser Alt+* menus on Windows.
 */
export function useAccessibilityShortcuts(handlers, enabled = true) {
  useEffect(() => {
    if (!enabled || !handlers) return undefined;

    const onKeyDown = (e) => {
      if (!e.altKey || !e.shiftKey || e.ctrlKey || e.metaKey) return;
      if (isEditableTarget(e.target)) return;

      const key = e.key.length === 1 ? e.key.toLowerCase() : e.key;

      const map = {
        o: handlers.togglePanel,
        '1': handlers.signLangVideo,
        '2': handlers.toggleSignFont,
        '3': handlers.textToSpeech,
        '4': handlers.openSpeechToText,
        c: handlers.toggleContrast,
        f: handlers.adjustFontSize,
        m: handlers.toggleLargeCursor,
        l: handlers.toggleLineHeight,
        s: handlers.toggleLetterSpacing,
        r: handlers.toggleReadableFont,
      };

      const action = map[key];
      if (action) {
        e.preventDefault();
        action();
      }
    };

    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [handlers, enabled]);
}
