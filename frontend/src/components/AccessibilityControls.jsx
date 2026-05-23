import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Accessibility,
  RotateCcw,
  X,
  Hand,
  Heart,
  Volume2,
  Mic,
  Contrast,
  Type,
  MousePointer2,
  AlignVerticalJustifyCenter,
  ArrowLeftRight,
  CaseSensitive,
} from 'lucide-react';
import toast from 'react-hot-toast';
import AccessibilitySpeechPanel from './AccessibilitySpeechPanel';
import { useAccessibilityShortcuts } from '../hooks/useAccessibilityShortcuts';
import {
  loadA11ySettings,
  saveA11ySettings,
  applyA11ySettings,
  resetA11ySettings,
  applyA11yProfile,
  speakSelectionOrFocus,
  A11Y_PROFILES,
  trapFocus,
  announceToScreenReader,
} from '../utils/accessibility';

const FEATURES = [
  { id: 'signLangVideo', label: 'Sign Lang Video', shortcut: '1', Icon: Hand, toggle: false },
  { id: 'signFont', label: 'ASL Fingerspell', shortcut: '2', Icon: Heart, key: 'signFont' },
  { id: 'tts', label: 'Text to Speech', shortcut: '3', Icon: Volume2, toggle: false },
  { id: 'stt', label: 'Speech to Text', shortcut: '4', Icon: Mic, toggle: false },
  { id: 'contrast', label: 'Color Contrast', shortcut: 'C', Icon: Contrast, key: 'highContrast' },
  { id: 'fontSize', label: 'Font Size', shortcut: 'F', Icon: Type, toggle: false },
  { id: 'cursor', label: 'Large Cursor', shortcut: 'M', Icon: MousePointer2, key: 'largeCursor' },
  { id: 'lineHeight', label: 'Line Height', shortcut: 'L', Icon: AlignVerticalJustifyCenter, key: 'lineHeight' },
  { id: 'letterSpacing', label: 'Letter Spacing', shortcut: 'S', Icon: ArrowLeftRight, key: 'letterSpacing' },
  { id: 'readable', label: 'Readable Text', shortcut: 'R', Icon: CaseSensitive, key: 'readableFont' },
];

const AccessibilityControls = () => {
  const navigate = useNavigate();
  const [settings, setSettings] = useState(loadA11ySettings);
  const [showPanel, setShowPanel] = useState(false);
  const [showStt, setShowStt] = useState(false);
  const [profile, setProfile] = useState('none');
  const panelRef = useRef(null);

  useEffect(() => {
    applyA11ySettings(settings);
  }, [settings]);

  useEffect(() => {
    if (!showPanel || !panelRef.current) return undefined;
    return trapFocus(panelRef.current);
  }, [showPanel]);

  const updateSettings = useCallback((patch) => {
    setSettings((prev) => {
      const next = { ...prev, ...patch };
      saveA11ySettings(next);
      applyA11ySettings(next);
      return next;
    });
    setProfile('none');
  }, []);

  const toggleBool = useCallback(
    (key) => {
      updateSettings({ [key]: !settings[key] });
    },
    [settings, updateSettings]
  );

  const handleReset = useCallback(() => {
    const defaults = resetA11ySettings();
    setSettings(defaults);
    setProfile('none');
    announceToScreenReader('Accessibility settings reset');
  }, []);

  const handleProfileChange = (e) => {
    const id = e.target.value;
    setProfile(id);
    if (id === 'hearing') {
      toast('Tip: Use Sign Lang Video for sign language support', { icon: '👋' });
    }
    const next = applyA11yProfile(id);
    setSettings(next);
  };

  const adjustFontSize = useCallback(() => {
    const next = settings.fontSize >= 28 ? 16 : settings.fontSize + 2;
    updateSettings({ fontSize: next });
    announceToScreenReader(`Font size ${next} pixels`);
  }, [settings.fontSize, updateSettings]);

  const shortcutHandlers = useMemo(
    () => ({
      togglePanel: () => setShowPanel((p) => !p),
      signLangVideo: () => {
        setShowPanel(false);
        navigate('/sign-language');
      },
      toggleSignFont: () => {
        if (!settings.signFont) {
          toast('ASL fingerspelling view on — toggle again to restore normal text', {
            duration: 4000,
          });
        }
        toggleBool('signFont');
      },
      textToSpeech: () => {
        if (!speakSelectionOrFocus()) {
          toast.error('Select text on the page or focus an element to read aloud.');
        }
      },
      openSpeechToText: () => setShowStt(true),
      toggleContrast: () => toggleBool('highContrast'),
      adjustFontSize,
      toggleLargeCursor: () => toggleBool('largeCursor'),
      toggleLineHeight: () => toggleBool('lineHeight'),
      toggleLetterSpacing: () => toggleBool('letterSpacing'),
      toggleReadableFont: () => toggleBool('readableFont'),
    }),
    [navigate, toggleBool, adjustFontSize, settings.signFont]
  );

  useAccessibilityShortcuts(shortcutHandlers, true);

  const handleFeatureClick = (feature) => {
    switch (feature.id) {
      case 'signLangVideo':
        setShowPanel(false);
        navigate('/sign-language');
        break;
      case 'signFont': {
        const turningOn = !settings.signFont;
        if (turningOn) {
          toast('ASL fingerspelling view on — toggle again to restore normal text', {
            duration: 4000,
          });
        }
        toggleBool('signFont');
        break;
      }
      case 'tts':
        if (!speakSelectionOrFocus()) {
          toast.error('Select text on the page or focus an element to read aloud.');
        }
        break;
      case 'stt':
        setShowStt(true);
        break;
      case 'contrast':
        toggleBool('highContrast');
        break;
      case 'fontSize':
        adjustFontSize();
        break;
      case 'cursor':
        toggleBool('largeCursor');
        break;
      case 'lineHeight':
        toggleBool('lineHeight');
        break;
      case 'letterSpacing':
        toggleBool('letterSpacing');
        break;
      case 'readable':
        toggleBool('readableFont');
        break;
      default:
        break;
    }
  };

  const isFeatureActive = (feature) => {
    if (feature.key) return Boolean(settings[feature.key]);
    if (feature.id === 'fontSize') return settings.fontSize !== 16;
    return false;
  };

  return (
    <>
      <button
        type="button"
        onClick={() => setShowPanel((p) => !p)}
        className="a11y-widget-root fixed bottom-4 right-4 z-50 flex h-14 w-14 items-center justify-center rounded-full bg-accent text-white shadow-lg transition-all hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2"
        aria-label="Open EmpowerWork accessibility widget"
        aria-expanded={showPanel}
        title="Accessibility (Alt+Shift+O)"
        data-asl-skip
      >
        <Accessibility className="h-7 w-7" aria-hidden />
      </button>

      {showPanel && (
        <div
          ref={panelRef}
          className="a11y-widget-root fixed bottom-24 right-4 z-50 flex max-h-[85vh] w-[min(100vw-2rem,22rem)] flex-col overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-2xl"
          role="dialog"
          aria-labelledby="a11y-widget-title"
          aria-modal="true"
          data-asl-skip
        >
          <div className="flex items-center justify-between border-b border-gray-100 bg-gradient-to-r from-teal-50 to-white px-4 py-3">
            <h2 id="a11y-widget-title" className="text-sm font-bold text-gray-900">
              EmpowerWork Accessibility
              <span className="mt-0.5 block text-[10px] font-normal text-gray-500">
                Alt+Shift+O
              </span>
            </h2>
            <div className="flex gap-1">
              <button
                type="button"
                onClick={handleReset}
                className="rounded-lg bg-accent p-2 text-white hover:bg-primary-700 focus:ring-2 focus:ring-accent"
                aria-label="Reset accessibility settings"
                title="Reset"
              >
                <RotateCcw className="h-4 w-4" />
              </button>
              <button
                type="button"
                onClick={() => setShowPanel(false)}
                className="rounded-lg bg-accent p-2 text-white hover:bg-primary-700 focus:ring-2 focus:ring-accent"
                aria-label="Close accessibility widget"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          </div>

          <div className="border-b border-gray-100 px-4 py-3">
            <label htmlFor="a11y-profile" className="mb-1 block text-xs font-semibold text-gray-600">
              Accessibility Profiles
            </label>
            <select
              id="a11y-profile"
              value={profile}
              onChange={handleProfileChange}
              className="input-field text-sm"
            >
              {Object.entries(A11Y_PROFILES).map(([id, { label }]) => (
                <option key={id} value={id}>
                  {label}
                </option>
              ))}
            </select>
          </div>

          <div className="overflow-y-auto px-3 py-3">
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-2">
              {FEATURES.map((feature) => {
                const active = isFeatureActive(feature);
                const Icon = feature.Icon;
                return (
                  <button
                    key={feature.id}
                    type="button"
                    onClick={() => handleFeatureClick(feature)}
                    className={`a11y-widget-tile relative min-h-[5.5rem] ${
                      active ? 'a11y-widget-tile-active' : ''
                    }`}
                    aria-pressed={feature.key ? active : undefined}
                    aria-label={`${feature.label}, shortcut Alt Shift ${feature.shortcut}`}
                  >
                    <span className="a11y-shortcut-badge" aria-hidden>
                      {feature.shortcut}
                    </span>
                    <Icon className="mb-1 h-7 w-7 text-gray-800" aria-hidden />
                    <span className="text-xs font-medium leading-tight text-gray-800">
                      {feature.label}
                    </span>
                    {feature.id === 'fontSize' && (
                      <span className="mt-0.5 text-[10px] text-gray-500">{settings.fontSize}px</span>
                    )}
                  </button>
                );
              })}
            </div>
          </div>

          <div className="border-t border-gray-100 bg-gray-50 px-4 py-2 text-center">
            <p className="text-[10px] font-semibold uppercase tracking-wide text-accent">
              EmpowerWork Accessibility Widget
            </p>
            <p className="text-[10px] text-gray-500">
              Shortcuts use Alt+Shift+key
            </p>
          </div>
        </div>
      )}

      <AccessibilitySpeechPanel open={showStt} onClose={() => setShowStt(false)} />
    </>
  );
};

export default AccessibilityControls;
