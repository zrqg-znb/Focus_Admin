export interface ParsedAIExplanationEntry {
  key: string;
  label: string;
  value: string;
}

export interface ParsedAIExplanation {
  extraEntries: ParsedAIExplanationEntry[];
  hasStructuredContent: boolean;
  how?: string;
  learnMore?: string;
  learnMoreHref?: string;
  rawText?: string;
  what?: string;
  why?: string;
}

const FIELD_LABELS: Record<string, string> = {
  analysis_depth: '分析深度',
  analysis_strategy: '分析策略',
  template_name: '模板',
};

function toDisplayText(value: unknown): string {
  if (value == null) {
    return '';
  }
  if (typeof value === 'string') {
    return value.trim();
  }
  if (typeof value === 'number' || typeof value === 'boolean') {
    return String(value);
  }
  if (Array.isArray(value)) {
    return value.map((item) => toDisplayText(item)).filter(Boolean).join(' / ');
  }
  if (typeof value === 'object') {
    try {
      return JSON.stringify(value, null, 2);
    } catch {
      return String(value);
    }
  }
  return String(value);
}

function toLink(value: unknown) {
  if (typeof value !== 'string') {
    return undefined;
  }
  const trimmed = value.trim();
  return /^https?:\/\//i.test(trimmed) ? trimmed : undefined;
}

export function parseAIExplanation(aiExplanation: unknown): null | ParsedAIExplanation {
  if (aiExplanation == null) {
    return null;
  }

  let parsedValue: unknown = aiExplanation;

  if (typeof aiExplanation === 'string') {
    const trimmed = aiExplanation.trim();
    if (!trimmed) {
      return null;
    }
    try {
      parsedValue = JSON.parse(trimmed);
    } catch {
      return {
        extraEntries: [],
        hasStructuredContent: false,
        rawText: trimmed,
      };
    }
  }

  if (typeof parsedValue !== 'object' || parsedValue === null) {
    const rawText = toDisplayText(parsedValue);
    return rawText
      ? {
          extraEntries: [],
          hasStructuredContent: false,
          rawText,
        }
      : null;
  }

  const root = parsedValue as Record<string, unknown>;
  const normalized =
    typeof root.xai === 'object' && root.xai !== null
      ? (root.xai as Record<string, unknown>)
      : root;

  const what = toDisplayText(normalized.what);
  const why = toDisplayText(normalized.why);
  const how = toDisplayText(normalized.how);
  const learnMore = toDisplayText(normalized.learn_more);
  const learnMoreHref = toLink(normalized.learn_more);

  const extraEntries = Object.entries(normalized)
    .filter(([key]) => !['how', 'learn_more', 'what', 'why'].includes(key))
    .map(([key, value]) => ({
      key,
      label: FIELD_LABELS[key] || key.replace(/_/g, ' '),
      value: toDisplayText(value),
    }))
    .filter((item) => item.value);

  const hasStructuredContent = Boolean(
    what || why || how || learnMore || extraEntries.length > 0,
  );

  if (!hasStructuredContent) {
    const rawText = toDisplayText(normalized);
    return rawText
      ? {
          extraEntries: [],
          hasStructuredContent: false,
          rawText,
        }
      : null;
  }

  return {
    extraEntries,
    hasStructuredContent,
    how: how || undefined,
    learnMore: learnMore || undefined,
    learnMoreHref,
    what: what || undefined,
    why: why || undefined,
  };
}
