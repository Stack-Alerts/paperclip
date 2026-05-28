'use client';

import React, { useState, useCallback, useEffect } from 'react';
import { useStatusSettings } from '@/contexts/StatusContext';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

export const StatusBarSettingsPanel: React.FC = () => {
  const { settings, update } = useStatusSettings();
  const [localSettings, setLocalSettings] = useState(settings);
  const [hasChanges, setHasChanges] = useState(false);

  useEffect(() => {
    setLocalSettings(settings);
    setHasChanges(false);
  }, [settings]);

  const handleChange = useCallback((key: keyof typeof settings, value: any) => {
    setLocalSettings(prev => ({ ...prev, [key]: value }));
    setHasChanges(true);
  }, []);

  const handleSave = useCallback(() => {
    update(localSettings);
    setHasChanges(false);
  }, [localSettings, update]);

  const handleReset = useCallback(() => {
    setLocalSettings(settings);
    setHasChanges(false);
  }, [settings]);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Status Bar Settings</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Ticker Mode */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <div>
              <Label className="block mb-1">Ticker Mode</Label>
              <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                Enable multi-message queue mode for status notices
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="ticker-mode"
              checked={localSettings.tickerMode}
              onChange={(e) => handleChange('tickerMode', e.target.checked)}
              className="rounded"
            />
            <Label htmlFor="ticker-mode" className="mb-0">
              {localSettings.tickerMode ? 'Enabled' : 'Disabled'}
            </Label>
          </div>
        </div>

        {/* Max Visible */}
        <div className="space-y-2">
          <Label htmlFor="max-visible">Maximum Visible Notices</Label>
          <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
            Number of notices to display (1-5). Extra notices collapse into "+N more"
          </p>
          <div className="flex items-center gap-4">
            <Input
              id="max-visible"
              type="number"
              min="1"
              max="5"
              value={localSettings.maxVisible}
              onChange={(e) => handleChange('maxVisible', Math.min(5, Math.max(1, parseInt(e.target.value) || 1)))}
              className="w-24"
            />
            <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>
              {localSettings.maxVisible === 1 ? '1 notice' : `${localSettings.maxVisible} notices`}
            </span>
          </div>
        </div>

        {/* Error Notice Behavior */}
        <div className="space-y-3">
          <Label>Error Notice Behavior</Label>
          <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
            Control how error notices are dismissed
          </p>
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <input
                type="radio"
                id="error-persist"
                name="error-behavior"
                checked={localSettings.errorPersist}
                onChange={() => handleChange('errorPersist', true)}
              />
              <Label htmlFor="error-persist" className="mb-0">
                Persist until dismissed
              </Label>
            </div>
            <div className="flex items-center gap-2">
              <input
                type="radio"
                id="error-duration"
                name="error-behavior"
                checked={!localSettings.errorPersist}
                onChange={() => handleChange('errorPersist', false)}
              />
              <Label htmlFor="error-duration" className="mb-0">
                Auto-dismiss after (seconds)
              </Label>
            </div>
          </div>
          {!localSettings.errorPersist && (
            <div className="flex items-center gap-4 ml-6">
              <Input
                type="number"
                min="5"
                max="300"
                value={localSettings.errorDuration}
                onChange={(e) => handleChange('errorDuration', Math.min(300, Math.max(5, parseInt(e.target.value) || 5)))}
                className="w-24"
              />
              <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                {localSettings.errorDuration}s
              </span>
            </div>
          )}
        </div>

        {/* Success Duration */}
        <div className="space-y-2">
          <Label htmlFor="success-ttl">Success Message Duration (milliseconds)</Label>
          <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
            How long success notices stay visible before auto-dismissing
          </p>
          <div className="flex items-center gap-4">
            <Input
              id="success-ttl"
              type="number"
              min="100"
              value={localSettings.successDuration}
              onChange={(e) => handleChange('successDuration', Math.max(100, parseInt(e.target.value) || 100))}
              className="w-32"
            />
            <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>
              {(localSettings.successDuration / 1000).toFixed(1)}s
            </span>
          </div>
        </div>

        {/* Warning Duration */}
        <div className="space-y-2">
          <Label htmlFor="warning-ttl">Warning Message Duration (milliseconds)</Label>
          <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
            How long warning notices stay visible before auto-dismissing
          </p>
          <div className="flex items-center gap-4">
            <Input
              id="warning-ttl"
              type="number"
              min="100"
              value={localSettings.warningDuration}
              onChange={(e) => handleChange('warningDuration', Math.max(100, parseInt(e.target.value) || 100))}
              className="w-32"
            />
            <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>
              {(localSettings.warningDuration / 1000).toFixed(1)}s
            </span>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex gap-2 justify-end pt-4 border-t" style={{ borderTopColor: 'var(--border-subtle)' }}>
          <Button
            variant="secondary"
            onClick={handleReset}
            disabled={!hasChanges}
          >
            Reset
          </Button>
          <Button
            onClick={handleSave}
            disabled={!hasChanges}
          >
            Save Settings
          </Button>
        </div>
      </CardContent>
    </Card>
  );
};

export default StatusBarSettingsPanel;
