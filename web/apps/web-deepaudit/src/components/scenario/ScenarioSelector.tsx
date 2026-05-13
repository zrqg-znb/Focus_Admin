import { useEffect, useMemo, useState } from 'react';
import { Loader2, Sparkles } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  BUILTIN_SCENARIO_FALLBACKS,
  getScenarioProfiles,
  type ScenarioProfile,
} from '@/shared/api/scenarios';

const PUBLIC_SYSTEM_SCENARIO_ORDER = ['general', 'concurrency', 'api_chain'];

const AUTO_SCENARIO_OPTION = {
  scenario_key: 'auto',
  name: '自动推断',
  description:
    '不绑定特定场景，保持现有默认行为；C/C++ / embedded 项目会继续沿用兼容预设。',
  objective_label: '自动',
};

function getObjectiveLabel(value: ScenarioProfile['objective_type']) {
  return value === 'inventory' ? '代码梳理' : '漏洞审计';
}

function mergePublicScenarios(items: ScenarioProfile[]) {
  const byKey = new Map<string, ScenarioProfile>();

  for (const fallback of BUILTIN_SCENARIO_FALLBACKS) {
    byKey.set(fallback.scenario_key, fallback);
  }

  for (const item of items) {
    if (!item.is_active) {
      continue;
    }
    if (item.is_system && !PUBLIC_SYSTEM_SCENARIO_ORDER.includes(item.scenario_key)) {
      continue;
    }
    byKey.set(item.scenario_key, item);
  }

  return Array.from(byKey.values()).sort((left, right) => {
    const leftIndex = PUBLIC_SYSTEM_SCENARIO_ORDER.indexOf(left.scenario_key);
    const rightIndex = PUBLIC_SYSTEM_SCENARIO_ORDER.indexOf(right.scenario_key);
    if (leftIndex >= 0 && rightIndex >= 0) {
      return leftIndex - rightIndex;
    }
    if (leftIndex >= 0) {
      return -1;
    }
    if (rightIndex >= 0) {
      return 1;
    }
    if (left.is_default !== right.is_default) {
      return left.is_default ? -1 : 1;
    }
    return left.name.localeCompare(right.name, 'zh-CN');
  });
}

interface ScenarioSelectorProps {
  className?: string;
  disabled?: boolean;
  showAutoOption?: boolean;
  showCFamilyHint?: boolean;
  value: string;
  onChange: (scenarioKey: string) => void;
}

export function ScenarioSelector({
  className = '',
  disabled = false,
  showAutoOption = true,
  showCFamilyHint = false,
  value,
  onChange,
}: ScenarioSelectorProps) {
  const [scenarios, setScenarios] = useState<ScenarioProfile[]>(BUILTIN_SCENARIO_FALLBACKS);
  const [loading, setLoading] = useState(true);
  const [usingFallbacks, setUsingFallbacks] = useState(false);

  useEffect(() => {
    let alive = true;

    const loadScenarios = async () => {
      try {
        setLoading(true);
        const response = await getScenarioProfiles({
          is_active: true,
          page: 1,
          pageSize: 100,
        });
        if (!alive) {
          return;
        }
        setScenarios(mergePublicScenarios(response.items));
        setUsingFallbacks(false);
      } catch (error) {
        if (!alive) {
          return;
        }
        setScenarios(mergePublicScenarios(BUILTIN_SCENARIO_FALLBACKS));
        setUsingFallbacks(true);
      } finally {
        if (alive) {
          setLoading(false);
        }
      }
    };

    void loadScenarios();
    return () => {
      alive = false;
    };
  }, []);

  const selectedScenario = useMemo(() => {
    if (value === 'auto') {
      return AUTO_SCENARIO_OPTION;
    }
    return scenarios.find((item) => item.scenario_key === value) || AUTO_SCENARIO_OPTION;
  }, [scenarios, value]);

  return (
    <div className={`border-border space-y-3 rounded border bg-muted/40 p-3 ${className}`.trim()}>
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-muted-foreground font-mono text-xs font-bold uppercase">
            场景
          </p>
          <p className="text-foreground mt-1 text-sm font-medium">
            选择一个场景，统一联动 Prompt、规则、知识注入与工具聚焦
          </p>
        </div>
        <Badge className="cyber-badge-muted font-mono text-xs">
          {selectedScenario.name}
        </Badge>
      </div>

      {loading ? (
        <div className="flex items-center gap-2 rounded-md border border-dashed px-3 py-4 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          加载场景中...
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          {showAutoOption && (
            <Button
              aria-pressed={value === 'auto'}
              className={`h-auto flex-col items-start justify-start gap-2 whitespace-normal rounded-md px-3 py-3 text-left ${
                value === 'auto'
                  ? 'border-primary/50 bg-primary/10 text-foreground'
                  : 'border-border bg-background/70 text-foreground hover:bg-muted/70'
              }`}
              disabled={disabled}
              onClick={() => onChange('auto')}
              type="button"
              variant="outline"
            >
              <div className="flex w-full items-center justify-between gap-2">
                <span className="text-sm font-semibold">{AUTO_SCENARIO_OPTION.name}</span>
                <Badge className="cyber-badge-muted text-[11px]">
                  {AUTO_SCENARIO_OPTION.objective_label}
                </Badge>
              </div>
              <span className="text-muted-foreground text-xs leading-5">
                {AUTO_SCENARIO_OPTION.description}
              </span>
            </Button>
          )}

          {scenarios.map((scenario) => {
            const active = value === scenario.scenario_key;
            return (
              <Button
                aria-pressed={active}
                className={`h-auto flex-col items-start justify-start gap-2 whitespace-normal rounded-md px-3 py-3 text-left ${
                  active
                    ? 'border-primary/50 bg-primary/10 text-foreground'
                    : 'border-border bg-background/70 text-foreground hover:bg-muted/70'
                }`}
                disabled={disabled}
                key={scenario.id || scenario.scenario_key}
                onClick={() => onChange(scenario.scenario_key)}
                type="button"
                variant="outline"
              >
                <div className="flex w-full items-center justify-between gap-2">
                  <span className="text-sm font-semibold">{scenario.name}</span>
                  <div className="flex items-center gap-1">
                    <Badge className="cyber-badge-muted text-[11px]">
                      {getObjectiveLabel(scenario.objective_type)}
                    </Badge>
                    {!scenario.is_system && (
                      <Badge className="cyber-badge-success text-[11px]">
                        自定义
                      </Badge>
                    )}
                  </div>
                </div>
                <span className="text-muted-foreground text-xs leading-5">
                  {scenario.description || '未填写场景描述'}
                </span>
              </Button>
            );
          })}
        </div>
      )}

      {usingFallbacks && (
        <div className="flex items-start gap-2 rounded-md border border-dashed border-amber-500/30 bg-amber-500/5 px-3 py-2 text-xs text-amber-700 dark:text-amber-300">
          <Sparkles className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          场景列表加载失败，当前使用内置预设兜底；自定义场景请稍后刷新后重试。
        </div>
      )}

      {showCFamilyHint && value === 'auto' && (
        <p className="text-muted-foreground font-mono text-xs leading-5">
          当前项目属于 C/C++ / embedded 范围，自动推断会继续保留兼容预设；如需明确控制，请改选具体场景。
        </p>
      )}
    </div>
  );
}

export default ScenarioSelector;
