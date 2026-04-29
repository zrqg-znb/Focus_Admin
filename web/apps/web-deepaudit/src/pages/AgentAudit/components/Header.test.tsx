import { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { Header } from './Header';

(
  globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }
).IS_REACT_ACT_ENVIRONMENT = true;

describe('Header', () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    container = document.createElement('div');
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(() => {
    act(() => {
      root.unmount();
    });
    container.remove();
  });

  it('shows snapshot semantics and runtime workspace metadata', async () => {
    act(() => {
      root.render(
        <Header
          task={
            {
              cache_repo: '/tmp/focusaudit-cache',
              id: 'task-1',
              last_synced_at: 1710000000,
              name: 'Snapshot Audit',
              status: 'running',
              workspace_path: '/tmp/focusaudit-workspace',
              workspace_source: 'multi_repo_cache_copy',
            } as any
          }
          canCancel={false}
          canCreate={false}
          canExport={false}
          canInspectCheckpoints={false}
          isCancelling={false}
          isRunning={true}
          onCancel={vi.fn()}
          onCheckpoints={vi.fn()}
          onExport={vi.fn()}
          onNewAudit={vi.fn()}
        />,
      );
    });

    await act(async () => {
      await Promise.resolve();
    });

    expect(container.textContent).toContain('repository_* 只锁定任务规格');
    expect(container.textContent).toContain('workspace_source: multi_repo_cache_copy');
    expect(container.textContent).toContain('last_synced_at:');
    expect(container.textContent).toContain('workspace_path: /tmp/focusaudit-workspace');
    expect(container.textContent).toContain('cache_repo: /tmp/focusaudit-cache');
  });
});
