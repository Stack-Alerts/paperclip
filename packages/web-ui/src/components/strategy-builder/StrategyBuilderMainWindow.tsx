'use client';

import React, { useState, useCallback } from 'react';
import { StrategyBuilder } from './StrategyBuilder';
import { NewStrategyDialog } from './NewStrategyDialog';
import { StrategyBrowserDialog } from './StrategyBrowserDialog';
import { BacktestConfigDialog } from './BacktestConfigDialog';
import { ValidationDialog } from './ValidationDialog';
import { DataUpdateModal } from './DataUpdateModal';
import { DataVerifyDialog } from './DataVerifyDialog';
import { SystemConfigWindow } from './SystemConfigWindow';
import { AlertDialog, QuestionDialog } from './AlertDialog';
import { AdminPinDialog } from './AdminPinDialog';
import { useStrategyStore } from '@/hooks/strategy-builder/useStrategyStore';

type DialogKey =
  | 'newStrategy'
  | 'strategyBrowser'
  | 'backtestConfig'
  | 'validation'
  | 'dataUpdate'
  | 'dataVerify'
  | 'systemConfig'
  | 'alert'
  | 'question'
  | 'adminPin'
  | null;

export interface StrategyBuilderMainWindowProps {
  strategyId?: string;
}

export const StrategyBuilderMainWindow: React.FC<StrategyBuilderMainWindowProps> = ({
  strategyId,
}) => {
  const { currentStrategy, saveStrategy, loadBlockLibrary } = useStrategyStore();
  const [activeDialog, setActiveDialog] = useState<DialogKey>(null);

  const open = useCallback((key: DialogKey) => setActiveDialog(key), []);
  const close = useCallback(() => setActiveDialog(null), []);

  const handleSave = useCallback(() => {
    saveStrategy().catch(console.error);
  }, [saveStrategy]);

  const handleRefreshBlocks = useCallback(() => {
    loadBlockLibrary().catch(console.error);
  }, [loadBlockLibrary]);

  return (
    <div className="flex flex-col h-full bg-zinc-950">
      {/* Menu Bar */}
      <div className="flex items-center gap-1 bg-zinc-900 border-b border-zinc-800 px-4 py-1.5 flex-shrink-0">
        <MenuDropdown
          label="File"
          items={[
            { label: 'New Strategy', onClick: () => open('newStrategy') },
            { label: 'Open Strategy…', onClick: () => open('strategyBrowser') },
            { label: 'Save', onClick: handleSave, shortcut: 'Ctrl+S' },
          ]}
        />
        <MenuDropdown
          label="Tools"
          items={[
            { label: 'Backtest…', onClick: () => open('backtestConfig') },
            { label: 'Validate…', onClick: () => open('validation') },
            { label: 'Update Data…', onClick: () => open('dataUpdate') },
            { label: 'Verify Data…', onClick: () => open('dataVerify') },
            { label: 'Refresh Blocks', onClick: handleRefreshBlocks },
            { label: '—', onClick: () => {} },
            { label: 'System Config…', onClick: () => open('systemConfig') },
          ]}
        />
        <MenuDropdown
          label="Help"
          items={[
            {
              label: 'About',
              onClick: () =>
                setActiveDialog('alert'),
            },
          ]}
        />
        {/* Strategy name display */}
        {currentStrategy && (
          <span className="ml-auto text-xs text-zinc-400 truncate max-w-xs">
            {currentStrategy.name}
          </span>
        )}
      </div>

      {/* Main Strategy Builder Content */}
      <div className="flex-1 overflow-hidden">
        <StrategyBuilder strategyId={strategyId} />
      </div>

      {/* Dialogs */}
      <NewStrategyDialog open={activeDialog === 'newStrategy'} onClose={close} />

      <StrategyBrowserDialog open={activeDialog === 'strategyBrowser'} onSelect={() => close()} onClose={close} />

      <BacktestConfigDialog
        open={activeDialog === 'backtestConfig'}
        onClose={close}
        
      />

      <ValidationDialog open={activeDialog === 'validation'} onClose={close} />

      <DataUpdateModal
        open={activeDialog === 'dataUpdate'}
        onUpdate={async () => {}}
        onSkip={close}
      />

      <DataVerifyDialog
        open={activeDialog === 'dataVerify'}
        onVerify={async () => ({})}
        onRepair={async () => {}}
        onClose={close}
      />

      <SystemConfigWindow
        open={activeDialog === 'systemConfig'}
        onSave={() => close()}
        onClose={close}
      />

      <AlertDialog
        open={activeDialog === 'alert'}
        title="BTC Trade Engine"
        heading="Strategy Builder"
        message="Institutional-grade algorithmic trading platform."
        icon="ℹ️"
        onClose={close}
      />

      <QuestionDialog
        open={activeDialog === 'question'}
        title="Confirm"
        heading="Are you sure?"
        message="This action cannot be undone."
        onResult={() => close()}
      />

      <AdminPinDialog
        open={activeDialog === 'adminPin'}
        onSuccess={() => {
          close();
          open('systemConfig');
        }}
        onCancel={close}
      />
    </div>
  );
};

interface MenuItem {
  label: string;
  shortcut?: string;
  onClick: () => void;
}

const MenuDropdown: React.FC<{ label: string; items: MenuItem[] }> = ({ label, items }) => {
  const [open, setOpen] = useState(false);

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
        className="px-3 py-1 text-sm text-zinc-300 hover:text-zinc-100 hover:bg-zinc-800 rounded transition-colors"
      >
        {label}
      </button>
      {open && (
        <div className="absolute top-full left-0 mt-0.5 bg-zinc-800 border border-zinc-700 rounded shadow-xl z-50 min-w-max">
          {items.map((item, i) =>
            item.label === '—' ? (
              <div key={i} className="border-t border-zinc-700 my-1" />
            ) : (
              <button
                key={i}
                onClick={() => {
                  setOpen(false);
                  item.onClick();
                }}
                className="flex items-center justify-between w-full px-4 py-1.5 text-sm text-zinc-200 hover:bg-zinc-700 transition-colors text-left gap-8"
              >
                <span>{item.label}</span>
                {item.shortcut && (
                  <span className="text-xs text-zinc-500">{item.shortcut}</span>
                )}
              </button>
            )
          )}
        </div>
      )}
    </div>
  );
};

export default StrategyBuilderMainWindow;
