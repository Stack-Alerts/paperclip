import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { RecommendationCard, RecommendationCardData } from '@/components/backtest/ai-recommendations/RecommendationCard';
import { RecommendationsRow } from '@/components/backtest/ai-recommendations/RecommendationsRow';

function makeProps(overrides: Partial<RecommendationCardData> = {}): RecommendationCardData {
  return {
    id: 'r1',
    categoryId: 'risk',
    deltaLabel: '+2.3%',
    title: 'Widen the stop',
    description: 'Widen the stop past the −0.7% cluster to keep runners.',
    codeLines: ['side = long', 'risk = 0.25'],
    applied: false,
    onToggleApplied: jest.fn(),
    onApplyOnChart: jest.fn(),
    ...overrides,
  };
}

describe('RecommendationCard', () => {
  it('renders the card anatomy: category chip, delta, title, code, apply on chart, toggle', () => {
    render(<RecommendationCard {...makeProps()} />);
    expect(screen.getByTestId('rec-card-r1-category')).toHaveTextContent(/risk/i);
    expect(screen.getByTestId('rec-card-r1-delta')).toHaveTextContent('+2.3%');
    expect(screen.getByText('Widen the stop')).toBeInTheDocument();
    expect(screen.getByTestId('rec-card-r1-code')).toHaveTextContent('side = long');
    expect(screen.getByTestId('rec-card-r1-apply-on-chart')).toHaveTextContent(/apply on chart/i);
    expect(screen.getByTestId('rec-card-r1-toggle')).toBeInTheDocument();
  });

  it('marks data-applied=false by default', () => {
    render(<RecommendationCard {...makeProps()} />);
    expect(screen.getByTestId('rec-card-r1')).toHaveAttribute('data-applied', 'false');
  });

  it('marks data-applied=true in applied state', () => {
    render(<RecommendationCard {...makeProps({ applied: true })} />);
    expect(screen.getByTestId('rec-card-r1')).toHaveAttribute('data-applied', 'true');
  });

  it('invokes onToggleApplied with the new boolean', () => {
    const onToggleApplied = jest.fn();
    render(<RecommendationCard {...makeProps({ onToggleApplied })} />);
    fireEvent.click(screen.getByTestId('rec-card-r1-toggle'));
    expect(onToggleApplied).toHaveBeenCalledWith(true);
  });

  it('invokes onApplyOnChart from the footer link', () => {
    const onApplyOnChart = jest.fn();
    render(<RecommendationCard {...makeProps({ onApplyOnChart })} />);
    fireEvent.click(screen.getByTestId('rec-card-r1-apply-on-chart'));
    expect(onApplyOnChart).toHaveBeenCalledTimes(1);
  });
});

describe('RecommendationsRow', () => {
  it('renders one card per recommendation', () => {
    const recs: RecommendationCardData[] = [
      makeProps({ id: 'a', title: 'A' }),
      makeProps({ id: 'b', title: 'B', categoryId: 'entry' }),
      makeProps({ id: 'c', title: 'C', categoryId: 'exit' }),
    ];
    render(<RecommendationsRow recommendations={recs} />);
    expect(screen.getByTestId('rec-card-a')).toBeInTheDocument();
    expect(screen.getByTestId('rec-card-b')).toBeInTheDocument();
    expect(screen.getByTestId('rec-card-c')).toBeInTheDocument();
  });

  it('uses a CSS grid with auto-fit columns so it wraps below 1440 px', () => {
    const recs = [makeProps({ id: 'a' })];
    render(<RecommendationsRow recommendations={recs} />);
    const row = screen.getByTestId('recommendations-row');
    const style = row.getAttribute('style') ?? '';
    expect(style).toContain('grid-template-columns');
    expect(style).toMatch(/auto-fit/);
    expect(style).toMatch(/minmax/);
  });
});
