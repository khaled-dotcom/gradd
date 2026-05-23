/**
 * Site-wide ASL fingerspelling display: Latin letter above hand SVG per character.
 */

const SKIP_TAGS = new Set([
  'SCRIPT',
  'STYLE',
  'TEXTAREA',
  'INPUT',
  'SELECT',
  'OPTION',
  'CODE',
  'PRE',
  'SVG',
  'IMG',
  'NOSCRIPT',
]);

const SKIP_SELECTOR =
  '.a11y-widget-root, .a11y-widget-tile, [data-asl-skip], .asl-fingerspell-block';

let active = false;
let observer = null;
let debounceTimer = null;

export function isAslFingerspellActive() {
  return active;
}

function shouldSkipElement(el) {
  if (!el || el.nodeType !== Node.ELEMENT_NODE) return true;
  if (SKIP_TAGS.has(el.tagName)) return true;
  if (el.closest?.(SKIP_SELECTOR)) return true;
  if (el.closest?.('.asl-unit, .asl-processed')) return true;
  if (el.isContentEditable) return true;
  return false;
}

function isLetter(char) {
  return /^[a-zA-Z]$/.test(char);
}

function createAslUnit(char) {
  const upper = char.toUpperCase();
  const lower = char.toLowerCase();
  const unit = document.createElement('span');
  unit.className = 'asl-unit';
  unit.setAttribute('aria-label', upper);

  const latin = document.createElement('span');
  latin.className = 'asl-latin';
  latin.setAttribute('aria-hidden', 'true');
  latin.textContent = upper;
  unit.appendChild(latin);

  const img = document.createElement('img');
  img.className = 'asl-hand';
  img.src = `/asl-fingerspell/${lower}.svg`;
  img.alt = '';
  img.setAttribute('aria-hidden', 'true');
  img.loading = 'lazy';
  img.width = 48;
  img.height = 60;
  unit.appendChild(img);

  return unit;
}

function createPlainChar(char) {
  const span = document.createElement('span');
  span.className = 'asl-plain-char';
  span.textContent = char;
  return span;
}

function createSpace() {
  const span = document.createElement('span');
  span.className = 'asl-space';
  span.setAttribute('aria-hidden', 'true');
  span.textContent = '\u00a0';
  return span;
}

function buildFragmentFromText(text) {
  const fragment = document.createDocumentFragment();
  for (const char of text) {
    if (char === ' ') {
      fragment.appendChild(createSpace());
    } else if (char === '\n') {
      fragment.appendChild(document.createElement('br'));
    } else if (isLetter(char)) {
      fragment.appendChild(createAslUnit(char));
    } else {
      fragment.appendChild(createPlainChar(char));
    }
  }
  return fragment;
}

function processTextNode(textNode) {
  const parent = textNode.parentElement;
  if (!parent || shouldSkipElement(parent)) return;
  if (parent.closest('.asl-processed')) return;

  const text = textNode.nodeValue;
  if (!text || !text.trim()) return;

  const wrapper = document.createElement('span');
  wrapper.className = 'asl-processed';
  wrapper.setAttribute('data-asl-original', text);
  wrapper.appendChild(buildFragmentFromText(text));

  parent.replaceChild(wrapper, textNode);
}

function walkElement(root) {
  if (!root || shouldSkipElement(root)) return;

  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
    acceptNode(node) {
      const parent = node.parentElement;
      if (!parent || shouldSkipElement(parent)) return NodeFilter.FILTER_REJECT;
      if (parent.closest('.asl-processed')) return NodeFilter.FILTER_REJECT;
      if (!node.nodeValue?.trim()) return NodeFilter.FILTER_REJECT;
      return NodeFilter.FILTER_ACCEPT;
    },
  });

  const textNodes = [];
  let current;
  while ((current = walker.nextNode())) {
    textNodes.push(current);
  }

  textNodes.forEach(processTextNode);
}

function getProcessRoot() {
  return document.querySelector('main') || document.getElementById('root') || document.body;
}

function processDocument() {
  if (!active) return;
  const root = getProcessRoot();
  if (root) walkElement(root);
}

function restoreProcessedNodes() {
  document.querySelectorAll('.asl-processed[data-asl-original]').forEach((wrapper) => {
    const original = wrapper.getAttribute('data-asl-original');
    const textNode = document.createTextNode(original ?? '');
    wrapper.parentNode?.replaceChild(textNode, wrapper);
  });
}

function scheduleProcess() {
  if (debounceTimer) clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => {
    debounceTimer = null;
    processDocument();
  }, 300);
}

function startObserver() {
  if (observer) return;
  const root = getProcessRoot();
  if (!root) return;

  observer = new MutationObserver(() => {
    scheduleProcess();
  });

  observer.observe(root, {
    childList: true,
    subtree: true,
    characterData: true,
  });
}

function stopObserver() {
  if (observer) {
    observer.disconnect();
    observer = null;
  }
  if (debounceTimer) {
    clearTimeout(debounceTimer);
    debounceTimer = null;
  }
}

export function enableAslFingerspell() {
  if (active) {
    scheduleProcess();
    return;
  }
  active = true;
  document.documentElement.classList.add('a11y-asl-fingerspell');
  processDocument();
  startObserver();
}

export function disableAslFingerspell() {
  if (!active) return;
  active = false;
  stopObserver();
  restoreProcessedNodes();
  document.documentElement.classList.remove('a11y-asl-fingerspell');
}

export function syncAslFingerspell(enabled) {
  if (enabled) enableAslFingerspell();
  else disableAslFingerspell();
}
