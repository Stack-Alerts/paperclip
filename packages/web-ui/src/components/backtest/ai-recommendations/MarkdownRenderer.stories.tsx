/**
 * Storybook entries for MarkdownRenderer (BTCAAAAA-38568 / Sprint B7).
 * Covers: headings, bold/italic, bullet list, ordered list, code block, mixed.
 */

import { MarkdownRenderer } from './MarkdownRenderer';

const meta = {
  title: 'AI Recommendations / MarkdownRenderer',
  component: MarkdownRenderer,
};
export default meta;

const HEADINGS_MD = `# Heading 1
## Heading 2
### Heading 3
Plain paragraph after headings.`;

const INLINE_MD = `This has **bold text**, *italic text*, and \`inline code\` all in one paragraph.`;

const BULLETS_MD = `- First bullet item
- Second bullet item
  - Nested item
- Third bullet item`;

const ORDERED_MD = `1. First step: enable RSI filter
2. Second step: adjust stop loss
3. Third step: backtest the result`;

const CODE_BLOCK_MD = `Here is an example configuration:

\`\`\`python
stopLoss = 0.030
rsiPeriod = 14
cooldown = 4
\`\`\`

Apply these values and re-run.`;

const MIXED_MD = `## Summary

The analysis found **3 high-confidence opportunities**:

1. Tighten stop loss on RSI < 30 entries
2. Extend take profit by 1.5× on confirmed breakouts
3. Filter low-volume signals in the 4h window

### Recommended Parameters

\`\`\`
stopLoss: 0.030
takeProfit: 0.063
volumeFilter: 0.7
\`\`\`

These changes are projected to improve *win rate* by **+4%** and reduce max drawdown by 0.03.`;

const WRAPPER_STYLE: React.CSSProperties = {
  maxWidth: 640,
  padding: 16,
  background: 'var(--bg-elevated)',
  border: '1px solid var(--border)',
  borderRadius: 8,
};

export function Headings() {
  return <div style={WRAPPER_STYLE}><MarkdownRenderer text={HEADINGS_MD} /></div>;
}

export function InlineFormatting() {
  return <div style={WRAPPER_STYLE}><MarkdownRenderer text={INLINE_MD} /></div>;
}

export function BulletList() {
  return <div style={WRAPPER_STYLE}><MarkdownRenderer text={BULLETS_MD} /></div>;
}

export function OrderedList() {
  return <div style={WRAPPER_STYLE}><MarkdownRenderer text={ORDERED_MD} /></div>;
}

export function CodeBlock() {
  return <div style={WRAPPER_STYLE}><MarkdownRenderer text={CODE_BLOCK_MD} /></div>;
}

export function MixedContent() {
  return <div style={WRAPPER_STYLE}><MarkdownRenderer text={MIXED_MD} /></div>;
}
