/**
 * EmpowerWork accessibility settings and DOM helpers
 */

import { syncAslFingerspell } from './aslFingerspell';

export const A11Y_STORAGE_KEY = 'empowerwork_a11y_settings';

export const DEFAULT_A11Y_SETTINGS = {
  fontSize: 16,
  highContrast: false,
  reducedMotion: false,
  largeCursor: false,
  lineHeight: false,
  letterSpacing: false,
  readableFont: false,
  signFont: false,
};

export const A11Y_PROFILES = {
  none: { label: 'Default', settings: {} },
  vision: {
    label: 'Vision',
    settings: {
      highContrast: true,
      fontSize: 20,
      lineHeight: true,
      largeCursor: false,
      letterSpacing: false,
      readableFont: false,
      signFont: false,
      reducedMotion: false,
    },
  },
  hearing: {
    label: 'Hearing',
    settings: {
      reducedMotion: false,
    },
  },
  motor: {
    label: 'Motor',
    settings: {
      largeCursor: true,
      reducedMotion: true,
    },
  },
  cognitive: {
    label: 'Cognitive',
    settings: {
      readableFont: true,
      letterSpacing: true,
      reducedMotion: true,
      lineHeight: true,
    },
  },
};

const LEGACY_FONT_KEY = 'accessibility_fontSize';
const LEGACY_CONTRAST_KEY = 'accessibility_highContrast';
const LEGACY_MOTION_KEY = 'accessibility_reducedMotion';

function migrateLegacySettings() {
  const stored = localStorage.getItem(A11Y_STORAGE_KEY);
  if (stored) return null;

  const legacyFont = localStorage.getItem(LEGACY_FONT_KEY);
  const legacyContrast = localStorage.getItem(LEGACY_CONTRAST_KEY);
  const legacyMotion = localStorage.getItem(LEGACY_MOTION_KEY);
  if (!legacyFont && !legacyContrast && !legacyMotion) return null;

  return {
    ...DEFAULT_A11Y_SETTINGS,
    fontSize: legacyFont ? parseInt(legacyFont, 10) : 16,
    highContrast: legacyContrast === 'true',
    reducedMotion: legacyMotion === 'true',
  };
}

export function loadA11ySettings() {
  const migrated = migrateLegacySettings();
  if (migrated) {
    saveA11ySettings(migrated);
    return migrated;
  }

  try {
    const raw = localStorage.getItem(A11Y_STORAGE_KEY);
    if (!raw) return { ...DEFAULT_A11Y_SETTINGS };
    return { ...DEFAULT_A11Y_SETTINGS, ...JSON.parse(raw) };
  } catch {
    return { ...DEFAULT_A11Y_SETTINGS };
  }
}

export function saveA11ySettings(settings) {
  localStorage.setItem(A11Y_STORAGE_KEY, JSON.stringify(settings));
  localStorage.setItem(LEGACY_FONT_KEY, String(settings.fontSize));
  localStorage.setItem(LEGACY_CONTRAST_KEY, String(settings.highContrast));
  localStorage.setItem(LEGACY_MOTION_KEY, String(settings.reducedMotion));
}

export function applyA11ySettings(settings) {
  const root = document.documentElement;
  const size = Math.min(28, Math.max(12, settings.fontSize || 16));
  root.style.fontSize = `${size}px`;

  root.classList.toggle('high-contrast', settings.highContrast);
  root.classList.toggle('reduce-motion', settings.reducedMotion);
  root.classList.toggle('a11y-large-cursor', settings.largeCursor);
  root.classList.toggle('a11y-line-height', settings.lineHeight);
  root.classList.toggle('a11y-letter-spacing', settings.letterSpacing);
  root.classList.toggle('a11y-readable-font', settings.readableFont);
  root.classList.toggle('a11y-sign-font', settings.signFont);
  syncAslFingerspell(settings.signFont);
}

export function resetA11ySettings() {
  const defaults = { ...DEFAULT_A11Y_SETTINGS };
  saveA11ySettings(defaults);
  applyA11ySettings(defaults);
  return defaults;
}

export function applyA11yProfile(profileId) {
  const profile = A11Y_PROFILES[profileId];
  if (!profile || profileId === 'none') {
    return resetA11ySettings();
  }
  const current = loadA11ySettings();
  const next = { ...current, ...profile.settings };
  saveA11ySettings(next);
  applyA11ySettings(next);
  return next;
}

export function speakText(text, lang = 'en-US') {
  if (typeof window === 'undefined' || !window.speechSynthesis || !text?.trim()) {
    return false;
  }
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text.trim());
  utterance.lang = lang;
  window.speechSynthesis.speak(utterance);
  return true;
}

export function getTextToSpeak() {
  const selection = window.getSelection?.()?.toString()?.trim();
  if (selection) return selection;

  const active = document.activeElement;
  if (!active) return '';

  if (active.getAttribute('aria-label')) {
    return active.getAttribute('aria-label');
  }
  if (active.title) return active.title;
  if (active.alt) return active.alt;
  return active.textContent?.trim() || '';
}

export function speakSelectionOrFocus() {
  return speakText(getTextToSpeak());
}

export function isEditableTarget(target) {
  if (!target) return false;
  const tag = target.tagName?.toLowerCase();
  if (tag === 'input' || tag === 'textarea' || tag === 'select') return true;
  if (target.isContentEditable) return true;
  return false;
}

/**
 * Announce message to screen readers
 */
export const announceToScreenReader = (message, priority = 'polite') => {
  const announcement = document.createElement('div');
  announcement.setAttribute('role', 'status');
  announcement.setAttribute('aria-live', priority);
  announcement.setAttribute('aria-atomic', 'true');
  announcement.className = 'sr-only';
  announcement.textContent = message;

  document.body.appendChild(announcement);

  setTimeout(() => {
    document.body.removeChild(announcement);
  }, 1000);
};

/**
 * Trap focus within an element (for modals)
 */
export const trapFocus = (element) => {
  const focusableElements = element.querySelectorAll(
    'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])'
  );

  const firstElement = focusableElements[0];
  const lastElement = focusableElements[focusableElements.length - 1];

  const handleTab = (e) => {
    if (e.key !== 'Tab') return;

    if (e.shiftKey) {
      if (document.activeElement === firstElement) {
        e.preventDefault();
        lastElement.focus();
      }
    } else if (document.activeElement === lastElement) {
      e.preventDefault();
      firstElement.focus();
    }
  };

  element.addEventListener('keydown', handleTab);

  return () => {
    element.removeEventListener('keydown', handleTab);
  };
};

export const prefersReducedMotion = () => {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
};

export const smoothScrollTo = (element, behavior = 'smooth') => {
  const shouldReduceMotion = prefersReducedMotion();
  element.scrollIntoView({
    behavior: shouldReduceMotion ? 'auto' : behavior,
    block: 'start',
  });
};

export const getAccessibleLabel = (fieldName, required = false) => {
  return required ? `${fieldName} (required)` : fieldName;
};

export const formatErrorMessage = (fieldName, error) => {
  return `${fieldName}: ${error}`;
};
