/**
 * Lightweight markdown renderer for AI response text.
 * Handles the subset the AI produces: headings, bold/italic, bullet lists,
 * numbered lists, inline code, and fenced code blocks.
 * Avoids an external dependency for a narrow rendering surface.
 */

import React from 'react';

type TokenKind =
  | { kind: 'h1'; text: string }
  | { kind: 'h2'; text: string }
  | { kind: 'h3'; text: string }
  | { kind: 'bullet'; text: string; depth: number }
  | { kind: 'ordered'; text: string; n: number; depth: number }
  | { kind: 'code-block'; lang: string; text: string }
  | { kind: 'blank' }
  | { kind: 'para'; text: string };

function tokenize(md: string): TokenKind[] {
  const lines = md.split('\n');
  const tokens: TokenKind[] = [];
  let i = 0;
  while (i < lines.length) {
    const raw = lines[i];
    const line = raw;

    // fenced code block
    const fenceMatch = /^(`{3,}|~{3,})(\w*)/.exec(line);
    if (fenceMatch) {
      const fence = fenceMatch[1];
      const lang = fenceMatch[2] ?? '';
      const codeLines: string[] = [];
      i++;
      while (i < lines.length && !lines[i].startsWith(fence)) {
        codeLines.push(lines[i]);
        i++;
      }
      tokens.push({ kind: 'code-block', lang, text: codeLines.join('\n') });
      i++; // skip closing fence
      continue;
    }

    // headings
    const h3 = /^### (.*)/.exec(line);
    if (h3) { tokens.push({ kind: 'h3', text: h3[1] }); i++; continue; }
    const h2 = /^## (.*)/.exec(line);
    if (h2) { tokens.push({ kind: 'h2', text: h2[1] }); i++; continue; }
    const h1 = /^# (.*)/.exec(line);
    if (h1) { tokens.push({ kind: 'h1', text: h1[1] }); i++; continue; }

    // blank
    if (line.trim() === '') { tokens.push({ kind: 'blank' }); i++; continue; }

    // unordered list (-, *, +)
    const bullet = /^(\s*)([-*+])\s+(.*)/.exec(line);
    if (bullet) {
      const depth = Math.floor(bullet[1].length / 2);
      tokens.push({ kind: 'bullet', depth, text: bullet[3] });
      i++;
      continue;
    }

    // ordered list
    const ordered = /^(\s*)(\d+)[.)]\s+(.*)/.exec(line);
    if (ordered) {
      const depth = Math.floor(ordered[1].length / 2);
      tokens.push({ kind: 'ordered', depth, n: parseInt(ordered[2], 10), text: ordered[3] });
      i++;
      continue;
    }

    // paragraph (merge consecutive non-blank lines)
    const paraLines: string[] = [line];
    i++;
    while (
      i < lines.length &&
      lines[i].trim() !== '' &&
      !/^(#{1,3} |`{3,}|~{3,}|\s*[-*+]\s|\s*\d+[.)]\s)/.test(lines[i])
    ) {
      paraLines.push(lines[i]);
      i++;
    }
    tokens.push({ kind: 'para', text: paraLines.join(' ') });
  }
  return tokens;
}

// Render inline markdown: **bold**, *italic*, `code`, and plain text.
function InlineText({ text }: { text: string }): React.ReactElement {
  const parts: React.ReactNode[] = [];
  const re = /(\*\*[\s\S]*?\*\*|\*[\s\S]*?\*|`[^`]+`)/g;
  let last = 0;
  let m: RegExpExecArray | null;
  let idx = 0;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) {
      parts.push(<React.Fragment key={idx++}>{text.slice(last, m.index)}</React.Fragment>);
    }
    const token = m[0];
    if (token.startsWith('**')) {
      parts.push(<strong key={idx++}>{token.slice(2, -2)}</strong>);
    } else if (token.startsWith('*')) {
      parts.push(<em key={idx++}>{token.slice(1, -1)}</em>);
    } else {
      parts.push(
        <code
          key={idx++}
          style={{
            fontFamily: 'var(--font-mono, monospace)',
            background: 'var(--bg-elevated)',
            border: '1px solid var(--border)',
            borderRadius: 3,
            padding: '0 3px',
            fontSize: '0.9em',
          }}
        >
          {token.slice(1, -1)}
        </code>,
      );
    }
    last = m.index + token.length;
  }
  if (last < text.length) {
    parts.push(<React.Fragment key={idx++}>{text.slice(last)}</React.Fragment>);
  }
  return <>{parts}</>;
}

export function MarkdownRenderer({ text }: { text: string }): React.ReactElement {
  const tokens = tokenize(text);
  const elements: React.ReactNode[] = [];
  let i = 0;

  while (i < tokens.length) {
    const t = tokens[i];

    if (t.kind === 'blank') { i++; continue; }

    if (t.kind === 'h1') {
      elements.push(
        <h1
          key={i}
          className="text-base font-bold mt-3 mb-1"
          style={{ color: 'var(--text-primary, var(--text-secondary))' }}
        >
          <InlineText text={t.text} />
        </h1>,
      );
      i++;
      continue;
    }

    if (t.kind === 'h2') {
      elements.push(
        <h2
          key={i}
          className="text-sm font-semibold mt-3 mb-1 uppercase tracking-wide"
          style={{ color: 'var(--text-secondary)', borderBottom: '1px solid var(--border)', paddingBottom: 2 }}
        >
          <InlineText text={t.text} />
        </h2>,
      );
      i++;
      continue;
    }

    if (t.kind === 'h3') {
      elements.push(
        <h3
          key={i}
          className="text-xs font-semibold mt-2 mb-0.5"
          style={{ color: 'var(--text-secondary)' }}
        >
          <InlineText text={t.text} />
        </h3>,
      );
      i++;
      continue;
    }

    if (t.kind === 'code-block') {
      elements.push(
        <pre
          key={i}
          className="text-[11px] rounded p-2 my-2 overflow-auto whitespace-pre-wrap break-words"
          style={{
            background: 'var(--bg-card)',
            color: 'var(--text-secondary)',
            border: '1px solid var(--border)',
            fontFamily: 'var(--font-mono, monospace)',
          }}
        >
          {t.text}
        </pre>,
      );
      i++;
      continue;
    }

    if (t.kind === 'para') {
      elements.push(
        <p key={i} className="text-xs leading-relaxed my-1" style={{ color: 'var(--text-secondary)' }}>
          <InlineText text={t.text} />
        </p>,
      );
      i++;
      continue;
    }

    // collect consecutive bullet items into a <ul>
    if (t.kind === 'bullet') {
      const items: Array<{ text: string; depth: number }> = [];
      while (i < tokens.length && tokens[i].kind === 'bullet') {
        const b = tokens[i] as { kind: 'bullet'; text: string; depth: number };
        items.push({ text: b.text, depth: b.depth });
        i++;
      }
      elements.push(
        <ul key={`ul-${i}`} className="my-1 flex flex-col gap-0.5" style={{ listStyle: 'none', padding: 0 }}>
          {items.map((item, j) => (
            <li
              key={j}
              className="text-xs flex items-start gap-1.5"
              style={{ paddingLeft: item.depth * 16, color: 'var(--text-secondary)' }}
            >
              <span aria-hidden="true" style={{ color: 'var(--text-muted)', lineHeight: '1.5' }}>•</span>
              <span><InlineText text={item.text} /></span>
            </li>
          ))}
        </ul>,
      );
      continue;
    }

    // collect consecutive ordered items into an <ol>
    if (t.kind === 'ordered') {
      const items: Array<{ text: string; n: number; depth: number }> = [];
      while (i < tokens.length && tokens[i].kind === 'ordered') {
        const o = tokens[i] as { kind: 'ordered'; text: string; n: number; depth: number };
        items.push({ text: o.text, n: o.n, depth: o.depth });
        i++;
      }
      elements.push(
        <ol key={`ol-${i}`} className="my-1 flex flex-col gap-0.5" style={{ listStyle: 'none', padding: 0 }}>
          {items.map((item, j) => (
            <li
              key={j}
              className="text-xs flex items-start gap-1.5"
              style={{ paddingLeft: item.depth * 16, color: 'var(--text-secondary)' }}
            >
              <span
                style={{
                  color: 'var(--accent-blue)',
                  fontWeight: 600,
                  minWidth: 16,
                  lineHeight: '1.5',
                  fontFamily: 'var(--font-mono, monospace)',
                  fontSize: '0.9em',
                }}
              >
                {item.n}.
              </span>
              <span><InlineText text={item.text} /></span>
            </li>
          ))}
        </ol>,
      );
      continue;
    }

    i++;
  }

  return <div className="flex flex-col">{elements}</div>;
}
