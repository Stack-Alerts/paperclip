/* eslint-disable @typescript-eslint/no-explicit-any */
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { FixedIssuesList } from '@/components/strategy-builder/FixedIssuesList';
import { ValidationSeverity } from '@/lib/strategy-builder/types';

const makeEntry = (overrides: Partial<any> = {}) => ({
  key: overrides.key ?? 'TIMING_004-2025-12-01T00:00:00Z',
  appliedAt: overrides.appliedAt ?? '2025-12-01T00:00:00Z',
  undoSnapshot: overrides.undoSnapshot ?? ({} as any),
  issue: {
    rule_id: 'TIMING_004',
    rule_name: 'Timing window exceeds recheck delay',
    severity: ValidationSeverity.ERROR,
    category: '',
    message: 'Fixed: Timing window exceeds recheck delay',
    location: 'Block::1::Signal::asia_session',
    ...(overrides.issue ?? {}),
  },
});

describe('FixedIssuesList', () => {
  it('renders nothing when there are no entries', () => {
    const { container } = render(<FixedIssuesList entries={[]} onUndo={jest.fn()} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders the section header with the entry count', () => {
    render(<FixedIssuesList entries={[makeEntry(), makeEntry({ key: 'k2' })]} onUndo={jest.fn()} />);
    expect(screen.getByRole('heading', { name: /Fixed in this session/i })).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
  });

  it('renders one row per entry with rule name, id and location', () => {
    render(
      <FixedIssuesList
        entries={[
          makeEntry({ key: 'k1' }),
          makeEntry({
            key: 'k2',
            issue: {
              rule_id: 'EXIT_009',
              rule_name: 'Duplicate exit condition',
              severity: ValidationSeverity.WARNING,
              category: '',
              message: '',
              location: 'Block::2',
            },
          }),
        ]}
        onUndo={jest.fn()}
      />
    );
    expect(screen.getByText('Timing window exceeds recheck delay')).toBeInTheDocument();
    expect(screen.getByText('Duplicate exit condition')).toBeInTheDocument();
    expect(screen.getByText('TIMING_004')).toBeInTheDocument();
    expect(screen.getByText('EXIT_009')).toBeInTheDocument();
    expect(screen.getByText('Block::1::Signal::asia_session')).toBeInTheDocument();
    expect(screen.getByText('Block::2')).toBeInTheDocument();
  });

  it('calls onUndo with the entry key when the Undo button is clicked', () => {
    const onUndo = jest.fn();
    render(<FixedIssuesList entries={[makeEntry({ key: 'rehydrated-key-xyz' })]} onUndo={onUndo} />);
    fireEvent.click(screen.getByRole('button', { name: /Undo fix for/i }));
    expect(onUndo).toHaveBeenCalledWith('rehydrated-key-xyz');
  });

  it('toggles row visibility when Hide/Show is clicked', () => {
    render(<FixedIssuesList entries={[makeEntry()]} onUndo={jest.fn()} />);
    expect(screen.getByText('Timing window exceeds recheck delay')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /Hide/i }));
    expect(screen.queryByText('Timing window exceeds recheck delay')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /Show/i }));
    expect(screen.getByText('Timing window exceeds recheck delay')).toBeInTheDocument();
  });

  it('starts collapsed when defaultCollapsed is true', () => {
    render(<FixedIssuesList entries={[makeEntry()]} onUndo={jest.fn()} defaultCollapsed />);
    expect(screen.queryByText('Timing window exceeds recheck delay')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Show/i })).toBeInTheDocument();
  });
});
