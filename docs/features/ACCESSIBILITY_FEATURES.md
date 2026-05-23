# ♿ Website Accessibility Features

## ✅ Accessibility Enhancements Implemented

The website has been enhanced with comprehensive accessibility features to make it easy for people with disabilities to use.

## 🎯 Key Features

### 1. **EmpowerWork Accessibility Widget** (Daem-style grid)

- **Floating button**: Bottom-right, opens the widget (`Alt+Shift+O`)
- **Icon grid**: 10 feature tiles with keyboard shortcut badges
- **Accessibility Profiles**: Vision, Hearing, Motor, Cognitive presets
- **Reset / Close**: Header actions; settings persist in `localStorage` (`empowerwork_a11y_settings`)

| Feature | Shortcut | Action |
|---------|----------|--------|
| Sign Lang Video | Alt+Shift+1 | Navigate to `/sign-language` |
| ASL Fingerspell | Alt+Shift+2 | Site-wide letter + hand display (see below) |
| Text to Speech | Alt+Shift+3 | Read selected text or focused element |
| Speech to Text | Alt+Shift+4 | Open global STT panel (Groq via API) |
| Color Contrast | Alt+Shift+C | Toggle high contrast |
| Font Size | Alt+Shift+F | Cycle 16px → 28px |
| Large Cursor | Alt+Shift+M | Toggle large cursor |
| Line Height | Alt+Shift+L | Toggle increased line height |
| Letter Spacing | Alt+Shift+S | Toggle letter spacing |
| Readable Text | Alt+Shift+R | Toggle Atkinson Hyperlegible font |

**Profiles:**

- **Vision** — high contrast, larger font (20px), line height
- **Hearing** — tip to use Sign Lang Video
- **Motor** — large cursor, reduced motion
- **Cognitive** — readable font, letter spacing, line height, reduced motion

**Files:** `frontend/src/components/AccessibilityControls.jsx`, `AccessibilitySpeechPanel.jsx`, `frontend/src/hooks/useAccessibilityShortcuts.js`, `frontend/src/utils/accessibility.js`, `frontend/src/utils/aslFingerspell.js`

#### ASL Fingerspell mode (Sign Lang Font tile)

When **ASL Fingerspell** is enabled:

- Text inside `<main>` is transformed so each **English letter (A–Z)** shows as a **Latin letter on top** and an **ASL hand SVG below** (NTI-style fingerspelling).
- Hand glyphs live in `frontend/public/asl-fingerspell/` (see `ATTRIBUTION.md`):
  - **11 letters** (A, C, E, I, L, M, N, O, S, T, U) cropped from the NTI banner (`source/nti-banner.png`).
  - **15 letters** (B, D, F, G, H, J, K, P, Q, R, V, W, X, Y, Z) from Wikimedia Commons ASL line-art (`Sign language *.svg`), processed to match banner ink and size.
- Regenerate assets: `pip install pillow` then `python frontend/scripts/generate_asl_svgs.py`.
- Toggle off restores original text without reloading the page.
- **Not processed:** accessibility widget, form inputs, `code` blocks, nav/footer outside `main`.
- **Numbers and punctuation** stay as normal characters (no hand image).
- **Arabic and other scripts** are unchanged.
- A **MutationObserver** re-applies the view when React updates page content.
- Optional **Gallaudet** web font is loaded as a fallback layer via CSS.

### 2. **Keyboard Navigation**
- **Tab Navigation**: All interactive elements accessible via keyboard
- **Focus Indicators**: Clear visual focus rings on all focusable elements
- **Skip Links**: "Skip to main content" link for screen reader users
- **ESC Key**: Close modals with Escape key
- **Enter/Space**: Activate buttons and links

### 3. **Screen Reader Support**
- **ARIA Labels**: All buttons, links, and form fields have descriptive labels
- **ARIA Roles**: Proper semantic roles (dialog, navigation, main, etc.)
- **ARIA Descriptions**: Additional context for complex elements
- **Alt Text**: All images have descriptive alt text
- **Hidden Text**: Screen reader-only text for context

### 4. **Visual Accessibility**
- **High Contrast Mode**: Enhanced borders and contrast
- **Focus Rings**: 2-3px focus rings on all interactive elements
- **Color Contrast**: WCAG AA compliant color combinations
- **Font Size**: Adjustable from 12px to 28px (widget)
- **Reduced Motion**: Respects prefers-reduced-motion preference

### 5. **Form Accessibility**
- **Label Association**: All inputs properly labeled with `htmlFor` and `id`
- **Required Fields**: Clearly marked with asterisk and `aria-required`
- **Error Messages**: Descriptive error messages with `aria-describedby`
- **Autocomplete**: Proper `autocomplete` attributes
- **Field Descriptions**: Helpful descriptions for screen readers

### 6. **Semantic HTML**
- **Proper Headings**: Logical heading hierarchy (h1, h2, h3)
- **Landmarks**: Navigation, main, footer landmarks
- **Lists**: Proper list markup for navigation and content
- **Buttons vs Links**: Correct use of `<button>` and `<a>` elements

### 7. **Modal Accessibility**
- **Focus Trap**: Focus stays within modal when open
- **ESC to Close**: Escape key closes modals
- **ARIA Modal**: Proper `role="dialog"` and `aria-modal`
- **Focus Management**: Focus moves to first element when opened
- **Backdrop Click**: Click outside to close (with confirmation)

### 8. **Image Accessibility**
- **Alt Text**: All images have descriptive alt text
- **Decorative Images**: Marked with `aria-hidden="true"`
- **Icon Labels**: Icons have text labels or aria-labels

## 🎨 Visual Enhancements

### Focus Styles
```css
*:focus-visible {
  outline: 2px solid accent color;
  outline-offset: 2px;
}
```

### High Contrast Mode
- Enhanced borders on all elements
- Stronger contrast ratios
- Clearer visual hierarchy

### Reduced Motion
- Respects `prefers-reduced-motion` media query
- Disables animations when enabled
- Smooth transitions become instant

## 📱 Responsive Design

- **Mobile Friendly**: Works on all screen sizes
- **Touch Targets**: Minimum 44x44px touch targets
- **Readable Text**: Minimum 16px base font size
- **Zoom Support**: Supports up to 200% zoom

## 🔧 How to Use Accessibility Features

### For Users

1. **Access Accessibility Widget**:
   - Click the accessibility icon in the bottom-right corner, or press `Alt+Shift+O`
   - Choose a profile or tap feature tiles
   - Use `Reset` to restore defaults

2. **Keyboard Navigation**:
   - Press `Tab` to move between elements
   - Press `Enter` or `Space` to activate buttons
   - Press `ESC` to close modals

3. **Screen Reader Users**:
   - Use "Skip to main content" link at top
   - Navigate with screen reader shortcuts
   - All elements have proper labels

### For Developers

1. **Add ARIA Labels**:
   ```jsx
   <button aria-label="Close modal">×</button>
   ```

2. **Associate Labels**:
   ```jsx
   <label htmlFor="email">Email</label>
   <input id="email" aria-required="true" />
   ```

3. **Use Semantic HTML**:
   ```jsx
   <nav>, <main>, <footer>, <article>, <section>
   ```

4. **Focus Management**:
   ```jsx
   useEffect(() => {
     element.focus();
   }, []);
   ```

## 📊 WCAG Compliance

### Level AA Compliance
- ✅ **Color Contrast**: 4.5:1 for normal text, 3:1 for large text
- ✅ **Keyboard Accessible**: All functionality via keyboard
- ✅ **Focus Indicators**: Visible focus on all interactive elements
- ✅ **Labels**: All form inputs have labels
- ✅ **Error Identification**: Clear error messages
- ✅ **Navigation**: Consistent navigation structure

### Level AAA (Partial)
- ✅ **Font Size**: Adjustable up to 200%
- ✅ **No Timing**: No time limits on content
- ✅ **Motion**: Can disable animations

## 🎯 Disability-Specific Features

### For Visual Impairments
- Screen reader support
- High contrast mode
- Font size adjustment
- Keyboard navigation
- Focus indicators

### For Motor Impairments
- Large touch targets
- Keyboard-only navigation
- Voice control support
- Reduced motion option

### For Cognitive Disabilities
- Clear navigation
- Simple language
- Consistent layout
- Error prevention
- Helpful descriptions

### For Hearing Impairments
- Visual indicators
- Text alternatives
- No audio-only content
- Caption support ready

## 🔄 Continuous Improvement

### Future Enhancements
- [ ] Voice navigation support
- [x] Sign language video page (`/sign-language`)
- [x] ASL fingerspell site-wide display (letter + hand per character)
- [ ] Customizable color schemes beyond high contrast
- [x] Text-to-speech (browser + widget)
- [x] Speech-to-text (widget panel + chat)
- [ ] Gesture navigation
- [ ] Eye tracking support

## 📝 Testing Checklist

- [x] Keyboard navigation works
- [x] Screen reader compatible
- [x] Focus indicators visible
- [x] Color contrast sufficient
- [x] Forms accessible
- [x] Modals accessible
- [x] Images have alt text
- [x] Semantic HTML used
- [x] ARIA labels present
- [x] Mobile responsive

## ✅ Summary

The website is now highly accessible with:
- ✅ EmpowerWork accessibility widget (grid + shortcuts + profiles)
- ✅ Full keyboard navigation
- ✅ Screen reader support
- ✅ High contrast mode
- ✅ Font size adjustment
- ✅ Reduced motion option
- ✅ Proper ARIA labels
- ✅ Focus management
- ✅ Semantic HTML
- ✅ WCAG AA compliance

Users with disabilities can now easily navigate and use all features of the website!

