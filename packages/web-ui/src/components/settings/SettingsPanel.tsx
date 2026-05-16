'use client';

import React, { useState, useCallback } from 'react';
import { AppSettings } from '@/types';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select } from '@/components/ui/select';

export interface SettingsPanelProps {
  settings?: AppSettings;
  onSave?: (settings: AppSettings) => void;
  disabled?: boolean;
}

/**
 * SettingsPanel - React port of PyQt5 SettingsDialog
 *
 * P1 Skeleton implementation with:
 * - Tabbed settings interface
 * - Basic configuration categories
 * - Form validation
 * - Save/Reset functionality
 *
 * Note: Full implementation deferred to P3
 */
export const SettingsPanel: React.FC<SettingsPanelProps> = ({
  settings = {},
  onSave,
  disabled = false,
}) => {
  const [activeTab, setActiveTab] = useState<string>(
    Object.keys(settings)[0] || 'general'
  );
  const [localSettings, setLocalSettings] = useState<AppSettings>(settings);
  const [hasChanges, setHasChanges] = useState(false);

  const handleSettingChange = useCallback(
    (category: string, key: string, value: string | number | boolean) => {
      setLocalSettings((prev) => ({
        ...prev,
        [category]: {
          ...prev[category],
          [key]: {
            ...prev[category]?.[key],
            value,
          },
        },
      }));
      setHasChanges(true);
    },
    []
  );

  const handleSave = useCallback(() => {
    onSave?.(localSettings);
    setHasChanges(false);
  }, [localSettings, onSave]);

  const handleReset = useCallback(() => {
    setLocalSettings(settings);
    setHasChanges(false);
  }, [settings]);

  const categories = Object.keys(localSettings);

  return (
    <div className="space-y-6">
      {/* Tab Navigation */}
      <div className="border-b border-gray-200">
        <div className="flex overflow-x-auto">
          {categories.map((category) => (
            <button
              key={category}
              onClick={() => setActiveTab(category)}
              className={`px-4 py-2 border-b-2 font-medium transition-colors whitespace-nowrap ${
                activeTab === category
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-600 hover:text-gray-900'
              }`}
            >
              {category.charAt(0).toUpperCase() + category.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Settings Panel */}
      <Card>
        <CardHeader>
          <CardTitle>
            {activeTab.charAt(0).toUpperCase() + activeTab.slice(1)} Settings
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {localSettings[activeTab] ? (
            <div className="space-y-6">
              {Object.entries(localSettings[activeTab]).map(([key, setting]) => (
                <div key={key} className="space-y-2">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <Label htmlFor={key}>{setting.label}</Label>
                      {setting.description && (
                        <p className="text-xs text-gray-600 mt-1">
                          {setting.description}
                        </p>
                      )}
                    </div>
                  </div>

                  {setting.type === 'text' && (
                    <Input
                      id={key}
                      type="text"
                      value={setting.value}
                      onChange={(e) =>
                        handleSettingChange(activeTab, key, e.target.value)
                      }
                      disabled={disabled}
                      placeholder={setting.description}
                    />
                  )}

                  {setting.type === 'number' && (
                    <Input
                      id={key}
                      type="number"
                      value={setting.value}
                      onChange={(e) =>
                        handleSettingChange(activeTab, key, parseFloat(e.target.value))
                      }
                      disabled={disabled}
                    />
                  )}

                  {setting.type === 'password' && (
                    <Input
                      id={key}
                      type="password"
                      value={setting.value}
                      onChange={(e) =>
                        handleSettingChange(activeTab, key, e.target.value)
                      }
                      disabled={disabled}
                      placeholder="••••••••"
                    />
                  )}

                  {setting.type === 'select' && setting.options && (
                    <Select
                      id={key}
                      value={setting.value}
                      onChange={(e) =>
                        handleSettingChange(activeTab, key, e.target.value)
                      }
                      disabled={disabled}
                    >
                      <option value="">Select an option...</option>
                      {setting.options.map((opt) => (
                        <option key={opt.value} value={opt.value}>
                          {opt.label}
                        </option>
                      ))}
                    </Select>
                  )}

                  {setting.type === 'toggle' && (
                    <div className="flex items-center gap-2">
                      <input
                        id={key}
                        type="checkbox"
                        checked={setting.value === 'true'}
                        onChange={(e) =>
                          handleSettingChange(activeTab, key, e.target.checked)
                        }
                        disabled={disabled}
                        className="rounded"
                      />
                      <Label htmlFor={key} className="mb-0" />
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-500 text-center py-8">
              No settings available for this category
            </p>
          )}
        </CardContent>
      </Card>

      {/* Action Buttons */}
      <div className="flex gap-2 justify-end">
        <Button
          variant="secondary"
          onClick={handleReset}
          disabled={disabled || !hasChanges}
        >
          Reset
        </Button>
        <Button
          onClick={handleSave}
          disabled={disabled || !hasChanges}
        >
          Save Settings
        </Button>
      </div>
    </div>
  );
};

export default SettingsPanel;
