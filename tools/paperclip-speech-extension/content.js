(function () {
  'use strict';

  function isPaperclipPage() {
    if (document.querySelector('meta[name="apple-mobile-web-app-title"][content="Paperclip"]')) return true;
    if (document.title === 'Paperclip') return true;
    return false;
  }

  function waitForPaperclip(timeoutMs) {
    return new Promise((resolve) => {
      if (isPaperclipPage()) { resolve(true); return; }
      let done = false;
      const finish = (ok) => { if (done) return; done = true; obs.disconnect(); clearTimeout(t); resolve(ok); };
      const obs = new MutationObserver(() => { if (isPaperclipPage()) finish(true); });
      obs.observe(document.documentElement, { childList: true, subtree: true });
      const t = setTimeout(() => finish(false), timeoutMs);
    });
  }

  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) {
    console.warn('[Paperclip Speech] Web Speech API not available in this browser.');
    return;
  }

  waitForPaperclip(3000).then((isPaperclip) => {
    if (!isPaperclip) {
      console.debug('[Paperclip Speech] not a Paperclip page (no marker), skipping.');
      return;
    }
    main();
  });

  const ATTR_ATTACHED = 'data-pcs-attached';
  const INPUT_SELECTORS = [
    'textarea',
    'input[type="text"]',
    'input[type="search"]',
    'input:not([type])',
    '[contenteditable="true"]',
    '[contenteditable=""]'
  ].join(',');

  function isVisible(el) {
    if (!el || !el.isConnected) return false;
    const rect = el.getBoundingClientRect();
    if (rect.width < 40 || rect.height < 18) return false;
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden' || cs.opacity === '0') return false;
    return true;
  }

  function looksLikeMessageInput(el) {
    if (el.disabled || el.readOnly) return false;
    if (el.type === 'password' || el.type === 'hidden') return false;
    if (el.tagName === 'INPUT') {
      const rect = el.getBoundingClientRect();
      if (rect.width < 120) return false;
    }
    return isVisible(el);
  }

  function setNativeValue(el, value) {
    const tag = el.tagName;
    if (tag === 'TEXTAREA' || tag === 'INPUT') {
      const proto = tag === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
      const desc = Object.getOwnPropertyDescriptor(proto, 'value');
      if (desc && desc.set) {
        desc.set.call(el, value);
      } else {
        el.value = value;
      }
      el.dispatchEvent(new Event('input', { bubbles: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
      return;
    }
    // contenteditable
    el.focus();
    if (document.execCommand) {
      try {
        document.execCommand('insertText', false, value);
        return;
      } catch (_) { /* fall through */ }
    }
    el.textContent = (el.textContent || '') + value;
    el.dispatchEvent(new InputEvent('input', { bubbles: true, data: value, inputType: 'insertText' }));
  }

  // Spoken punctuation → symbol, with correct spacing.
  // Each entry: [spoken phrase, symbol, attachBefore]
  // attachBefore=true  → strip any space before the symbol (it glues to the preceding word)
  // attachBefore=false → keep/add a space before the symbol
  const PUNCT_MAP = [
    ['comma',              ',',   true ],
    ['period',             '.',   true ],
    ['full stop',          '.',   true ],
    ['question mark',      '?',   true ],
    ['exclamation mark',   '!',   true ],
    ['exclamation point',  '!',   true ],
    ['semicolon',          ';',   true ],
    ['colon',              ':',   true ],
    ['ellipsis',           '…',   true ],
    ['dot dot dot',        '…',   true ],
    ['hyphen',             '-',   true ],
    ['apostrophe',         "'",   true ],
    ['percent sign',       '%',   true ],
    ['close parenthesis',  ')',   true ],
    ['close paren',        ')',   true ],
    ['end parenthesis',    ')',   true ],
    ['close bracket',      ']',   true ],
    ['close brace',        '}',   true ],
    ['close quote',        '"',   true ],
    ['end quote',          '"',   true ],
    ['new paragraph',      '\n\n', false],
    ['new line',           '\n',   false],
    ['newline',            '\n',   false],
    ['line break',         '\n',   false],
    ['open parenthesis',   '(',   false],
    ['open paren',         '(',   false],
    ['open bracket',       '[',   false],
    ['open brace',         '{',   false],
    ['open quote',         '"',   false],
    ['at sign',            '@',   false],
    ['hashtag',            '#',   false],
    ['hash',               '#',   false],
    ['pound sign',         '#',   false],
    ['dollar sign',        '$',   false],
    ['ampersand',          '&',   false],
    ['asterisk',           '*',   false],
    ['plus sign',          '+',   false],
    ['equals sign',        '=',   false],
    ['less than',          '<',   false],
    ['greater than',       '>',   false],
    ['underscore',         '_',   false],
    ['pipe',               '|',   false],
    ['tilde',              '~',   false],
    ['caret',              '^',   false],
    ['forward slash',      '/',   false],
    ['slash',              '/',   false],
    ['backslash',          '\\',  false],
    ['dash',               '—',   false],
  ];

  // Sort longest phrase first so multi-word phrases match before single words.
  const _punctSorted = PUNCT_MAP.slice().sort((a, b) => b[0].length - a[0].length);
  const _punctPattern = new RegExp(
    '(?:\\s*)(' + _punctSorted.map(([w]) => w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|') + ')(?=\\s|$)',
    'gi'
  );

  function normalizeTranscript(text) {
    const replaced = text.replace(_punctPattern, (match, word) => {
      const entry = _punctSorted.find(([w]) => w.toLowerCase() === word.toLowerCase());
      if (!entry) return match;
      const [, symbol, attachBefore] = entry;
      if (attachBefore) {
        // No space before, one space after (handled by the word following)
        return symbol;
      } else {
        // Space before (unless at the start of the string)
        return ' ' + symbol;
      }
    });
    // Ensure a single space follows terminal punctuation when a letter immediately follows.
    return replaced
      .replace(/([,\.!?;:…])([A-Za-z])/g, '$1 $2')
      .replace(/ +\n/g, '\n')   // drop spaces immediately before newlines
      .replace(/\n +/g, '\n')   // drop spaces immediately after newlines
      .replace(/^[ \t]+|[ \t]+$/g, '');  // trim horizontal whitespace only — preserve \n
  }

  function appendText(el, transcript) {
    if (!transcript) return;
    const normalized = normalizeTranscript(transcript);
    if (!normalized) return;
    const isText = el.tagName === 'TEXTAREA' || el.tagName === 'INPUT';
    // Attaching symbols (no leading space before them): , . ! ? newlines etc.
    const startsAttach = /^[\n,\.!?;:'")\]}'…%\-—]/.test(normalized);
    if (isText) {
      const current = el.value || '';
      const sep = (!startsAttach && current && !current.endsWith(' ') && !current.endsWith('\n')) ? ' ' : '';
      setNativeValue(el, current + sep + normalized);
    } else {
      setNativeValue(el, (startsAttach ? '' : ' ') + normalized);
    }
  }

  function placeButton(btn, input, host) {
    const r = input.getBoundingClientRect();
    const yOff = Math.max(4, (r.height - 28) / 2);
    if (host === document.body) {
      // No transformed ancestor in the way → fixed positioning works.
      btn.style.position = 'fixed';
      btn.style.top = `${r.top + yOff}px`;
      btn.style.left = `${r.right - 34}px`;
    } else {
      // Dialog/modal hosts often have `transform` for entrance animation,
      // which breaks `position: fixed`. Use absolute positioning relative
      // to the host's own bounding box instead.
      const hr = host.getBoundingClientRect();
      btn.style.position = 'absolute';
      btn.style.top = `${(r.top - hr.top) + yOff}px`;
      btn.style.left = `${(r.right - hr.left) - 34}px`;
    }
  }

  // Find the closest modal/dialog ancestor so our button is a DOM descendant
  // of the dialog. Otherwise Radix-style onPointerDownOutside handlers swallow
  // clicks on the button. Falls back to document.body for non-modal inputs.
  function findHost(input) {
    return input.closest(
      '[role="dialog"], [role="alertdialog"], [aria-modal="true"]'
    ) || document.body;
  }

  function attachMic(input) {
    if (input.getAttribute(ATTR_ATTACHED) === '1') return;
    input.setAttribute(ATTR_ATTACHED, '1');

    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'pcs-mic-btn';
    btn.textContent = '🎤';
    btn.title = 'Dictate (Web Speech API)';
    btn.dataset.state = 'idle';

    const host = findHost(input);
    host.appendChild(btn);
    placeButton(btn, input, host);

    const reposition = () => placeButton(btn, input, host);
    window.addEventListener('scroll', reposition, true);
    window.addEventListener('resize', reposition);
    const ro = new ResizeObserver(reposition);
    ro.observe(input);
    if (host !== document.body) ro.observe(host);

    let recognition = null;
    let recording = false;

    function stop() {
      if (recognition) {
        try { recognition.stop(); } catch (_) {}
      }
    }

    function start() {
      try {
        recognition = new SR();
        recognition.lang = navigator.language || 'en-US';
        recognition.continuous = true;
        recognition.interimResults = false;
        recognition.maxAlternatives = 1;

        recognition.onstart = () => {
          recording = true;
          btn.dataset.state = 'recording';
          btn.textContent = '🎙️';
          btn.title = 'Click to stop dictation';
        };

        recognition.onresult = (event) => {
          let finalText = '';
          for (let i = event.resultIndex; i < event.results.length; i++) {
            const result = event.results[i];
            if (result.isFinal) finalText += result[0].transcript;
          }
          if (finalText.trim()) appendText(input, finalText.trim());
        };

        recognition.onerror = (event) => {
          recording = false;
          // 'no-speech' just means the mic timed out with no audio — not a real error.
          // Reset silently so the user can click again without seeing a warning.
          if (event.error === 'no-speech') {
            btn.dataset.state = 'idle';
            btn.textContent = '🎤';
            btn.title = 'Dictate (Web Speech API)';
            return;
          }
          console.warn('[Paperclip Speech] recognition error:', event.error, event);
          btn.dataset.state = 'error';
          btn.textContent = '⚠️';
          if (event.error === 'network') {
            btn.title = 'Web Speech API network error — Brave may need flag enabled. See README.';
          } else if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
            btn.title = 'Microphone permission denied. Allow mic for this site in Brave settings.';
          } else {
            btn.title = `Speech error: ${event.error}. Click to retry.`;
          }
          setTimeout(() => {
            if (!recording) {
              btn.dataset.state = 'idle';
              btn.textContent = '🎤';
              btn.title = 'Dictate (Web Speech API)';
            }
          }, 4000);
        };

        recognition.onend = () => {
          recording = false;
          if (btn.dataset.state !== 'error') {
            btn.dataset.state = 'idle';
            btn.textContent = '🎤';
            btn.title = 'Dictate (Web Speech API)';
          }
          recognition = null;
        };

        recognition.start();
      } catch (err) {
        console.error('[Paperclip Speech] failed to start:', err);
        btn.dataset.state = 'error';
        btn.textContent = '⚠️';
        btn.title = `Speech start failed: ${err.message}`;
      }
    }

    // Stop pointerdown from propagating so dialog-dismiss-on-outside handlers
    // never see it. preventDefault keeps focus on the input.
    const swallow = (e) => { e.stopPropagation(); };
    btn.addEventListener('pointerdown', swallow, true);
    btn.addEventListener('mousedown', (e) => { e.preventDefault(); e.stopPropagation(); }, true);
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      if (recording) stop(); else start();
    });

    const removalObserver = new MutationObserver(() => {
      if (!input.isConnected) {
        try { btn.remove(); } catch (_) {}
        window.removeEventListener('scroll', reposition, true);
        window.removeEventListener('resize', reposition);
        ro.disconnect();
        removalObserver.disconnect();
      }
    });
    removalObserver.observe(document.body, { childList: true, subtree: true });
  }

  function scan(root) {
    const candidates = (root || document).querySelectorAll(INPUT_SELECTORS);
    candidates.forEach((el) => {
      if (looksLikeMessageInput(el)) attachMic(el);
    });
  }

  function main() {
    scan(document);

    const mo = new MutationObserver((mutations) => {
      for (const m of mutations) {
        m.addedNodes.forEach((node) => {
          if (node.nodeType !== 1) return;
          if (node.matches && node.matches(INPUT_SELECTORS)) {
            if (looksLikeMessageInput(node)) attachMic(node);
          }
          if (node.querySelectorAll) scan(node);
        });
      }
    });
    mo.observe(document.body, { childList: true, subtree: true });
  }
})();
