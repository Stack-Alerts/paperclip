import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import {
  RecommendationDiff,
  RecommendationDiffParam,
} from '@/components/backtest/ai-recommendations/RecommendationDiff';

describe('RecommendationDiff', () => {
  it('is collapsed by default and expands on toggle, showing only changed params with red strikethrough old / green new', () => {
    const params: RecommendationDiffParam[] = [
      { key: 'adaptiveSL.enabled', before: 'false', after: 'true' },
      { key: 'maxBarsHeld', before: '5', after: '8' },
    ];

    render(<RecommendationDiff params={params} testIdPrefix="ai-recs-param-diff" />);

    expect(screen.getByTestId('ai-recs-param-diff')).toHaveAttribute('data-open', 'false');
    expect(screen.queryByTestId('ai-recs-param-diff-list')).not.toBeInTheDocument();
    expect(screen.queryByTestId('ai-recs-param-diff-row')).not.toBeInTheDocument();

    fireEvent.click(screen.getByTestId('ai-recs-param-diff-toggle'));
    expect(screen.getByTestId('ai-recs-param-diff')).toHaveAttribute('data-open', 'true');

    const rows = screen.getAllByTestId('ai-recs-param-diff-row');
    expect(rows).toHaveLength(2);

    const firstBefore = rows[0].querySelector(
      '[data-testid="ai-recs-param-diff-before"]',
    ) as HTMLElement;
    expect(firstBefore).toHaveTextContent('false');
    expect(firstBefore).toHaveStyle({
      color: 'var(--accent-red-on)',
      textDecoration: 'line-through',
    });
    const firstAfter = rows[0].querySelector(
      '[data-testid="ai-recs-param-diff-after"]',
    ) as HTMLElement;
    expect(firstAfter).toHaveTextContent('true');
    expect(firstAfter).toHaveStyle({ color: 'var(--accent-green-on)' });

    const allBefore = screen.getAllByTestId('ai-recs-param-diff-before');
    expect(allBefore[1]).toHaveTextContent('5');
    const allAfter = screen.getAllByTestId('ai-recs-param-diff-after');
    expect(allAfter[1]).toHaveTextContent('8');

    fireEvent.click(screen.getByTestId('ai-recs-param-diff-toggle'));
    expect(screen.getByTestId('ai-recs-param-diff')).toHaveAttribute('data-open', 'false');
  });

  it('renders the empty-state message when there are no changed params', () => {
    render(<RecommendationDiff params={[]} testIdPrefix="ai-recs-param-diff" />);

    fireEvent.click(screen.getByTestId('ai-recs-param-diff-toggle'));
    expect(screen.getByTestId('ai-recs-param-diff-none')).toHaveTextContent(
      /no numeric parameters changed/i,
    );
    expect(screen.queryByTestId('ai-recs-param-diff-list')).not.toBeInTheDocument();
  });
});