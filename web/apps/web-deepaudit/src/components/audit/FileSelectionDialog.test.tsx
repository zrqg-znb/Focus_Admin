import { act, type ComponentProps } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import FileSelectionDialog from './FileSelectionDialog';
import { api } from '@/shared/config/database';

const toast = vi.hoisted(() => ({
  error: vi.fn(),
  warning: vi.fn(),
}));
const debounceState = vi.hoisted(() => ({
  value: undefined as unknown,
}));

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

vi.mock('@/shared/config/database', () => ({
  api: {
    browseProjectFiles: vi.fn(),
  },
}));

vi.mock('@/shared/hooks', () => ({
  useDebounce: (value: unknown) =>
    debounceState.value === undefined ? value : debounceState.value,
}));

vi.mock('@/components/ui/dialog', () => ({
  Dialog: ({ children }: { children?: any }) => <div>{children}</div>,
  DialogContent: ({ children }: { children?: any }) => <div>{children}</div>,
  DialogFooter: ({ children }: { children?: any }) => <div>{children}</div>,
  DialogHeader: ({ children }: { children?: any }) => <div>{children}</div>,
  DialogTitle: ({ children }: { children?: any }) => <div>{children}</div>,
}));

vi.mock('sonner', () => ({
  toast,
}));

const browseProjectFiles = vi.mocked(api.browseProjectFiles);

type FileSelectionDialogProps = ComponentProps<typeof FileSelectionDialog>;

const baseProps: FileSelectionDialogProps = {
  branch: 'release/main',
  excludePatterns: [],
  group: 'platform',
  manifestXml: 'default.xml',
  onConfirm: vi.fn(),
  onOpenChange: vi.fn(),
  open: true,
  projectId: 'project-1',
  repositoryType: 'multi',
} as const;

async function flushEffects() {
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
  });
}

describe('FileSelectionDialog', () => {
  let container: HTMLDivElement;
  let root: Root;

  const findButtonByText = (text: string) =>
    Array.from(container.querySelectorAll('button')).find((button) =>
      button.textContent?.includes(text),
    );

  beforeEach(() => {
    container = document.createElement('div');
    document.body.appendChild(container);
    root = createRoot(container);
    const initialResponse = {
      has_more: true,
      items: [
        {
          kind: 'file',
          path: 'README.md',
          size: 12,
        },
      ],
      keyword: '',
      last_synced_at: 1710000000,
      limit: 200,
      offset: 0,
      path: '',
      repository_signature: 'repo-signature-a',
      repository_spec: {
        branch_name: 'release/main',
        group: 'platform',
        manifest_xml: 'default.xml',
        repository_type: 'multi',
        repository_url: 'https://example.com/manifest.git',
      },
      total: 1,
    } as any;
    const loadMoreResponse = {
      ...initialResponse,
      has_more: false,
      items: [
        {
          kind: 'file',
          path: 'src/app.py',
          size: 24,
        },
      ],
      total: 2,
    } as any;

    browseProjectFiles.mockReset();
    debounceState.value = undefined;
    toast.error.mockReset();
    toast.warning.mockReset();
    browseProjectFiles.mockResolvedValueOnce(initialResponse);
    browseProjectFiles.mockResolvedValueOnce(loadMoreResponse);
    browseProjectFiles.mockResolvedValue(initialResponse);
  });

  afterEach(() => {
    act(() => {
      root.unmount();
    });
    container.remove();
    vi.clearAllMocks();
  });

  it('auto refreshes once per multi-repo session and keeps later browsing on cache', async () => {
    const renderDialog = (overrides: Partial<FileSelectionDialogProps> = {}) => {
      act(() => {
        root.render(<FileSelectionDialog {...baseProps} {...overrides} />);
      });
    };

    renderDialog();
    await flushEffects();

    expect(browseProjectFiles).toHaveBeenCalledTimes(1);
    expect(browseProjectFiles).toHaveBeenLastCalledWith(
      'project-1',
      expect.objectContaining({
        refresh: true,
        branch_name: 'release/main',
        manifest_xml: 'default.xml',
        group: 'platform',
        repository_type: 'multi',
      }),
    );

    const loadMoreButton = findButtonByText('加载更多');
    expect(loadMoreButton).toBeTruthy();

    act(() => {
      loadMoreButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });
    await flushEffects();

    expect(browseProjectFiles).toHaveBeenCalledTimes(2);
    expect(browseProjectFiles).toHaveBeenLastCalledWith(
      'project-1',
      expect.objectContaining({
        refresh: false,
        offset: 1,
      }),
    );

    const refreshButton = findButtonByText('刷新代码树');
    expect(refreshButton).toBeTruthy();

    act(() => {
      refreshButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });
    await flushEffects();

    expect(browseProjectFiles).toHaveBeenCalledTimes(3);
    expect(browseProjectFiles).toHaveBeenLastCalledWith(
      'project-1',
      expect.objectContaining({
        refresh: true,
        offset: 0,
      }),
    );

    renderDialog({ branch: 'release/hotfix' });
    await flushEffects();

    expect(browseProjectFiles).toHaveBeenCalledTimes(4);
    expect(browseProjectFiles).toHaveBeenLastCalledWith(
      'project-1',
      expect.objectContaining({
        refresh: true,
        branch_name: 'release/hotfix',
        manifest_xml: 'default.xml',
        group: 'platform',
      }),
    );
  });

  it('navigates nested directories with exact path values', async () => {
    browseProjectFiles.mockReset();
    browseProjectFiles
      .mockResolvedValueOnce({
        has_more: false,
        items: [{ kind: 'directory', path: 'a', size: 0 }],
        keyword: '',
        last_synced_at: 1710000000,
        limit: 200,
        offset: 0,
        path: '',
        repository_signature: 'repo-signature-a',
        repository_spec: {
          branch_name: 'release/main',
          group: 'platform',
          manifest_xml: 'default.xml',
          repository_type: 'multi',
          repository_url: 'https://example.com/manifest.git',
        },
        total: 1,
      } as any)
      .mockResolvedValueOnce({
        has_more: false,
        items: [{ kind: 'directory', path: 'a/b', size: 0 }],
        keyword: '',
        last_synced_at: 1710000000,
        limit: 200,
        offset: 0,
        path: 'a',
        repository_signature: 'repo-signature-a',
        repository_spec: {
          branch_name: 'release/main',
          group: 'platform',
          manifest_xml: 'default.xml',
          repository_type: 'multi',
          repository_url: 'https://example.com/manifest.git',
        },
        total: 1,
      } as any)
      .mockResolvedValueOnce({
        has_more: false,
        items: [{ kind: 'directory', path: 'a/b/c', size: 0 }],
        keyword: '',
        last_synced_at: 1710000000,
        limit: 200,
        offset: 0,
        path: 'a/b',
        repository_signature: 'repo-signature-a',
        repository_spec: {
          branch_name: 'release/main',
          group: 'platform',
          manifest_xml: 'default.xml',
          repository_type: 'multi',
          repository_url: 'https://example.com/manifest.git',
        },
        total: 1,
      } as any);

    act(() => {
      root.render(<FileSelectionDialog {...baseProps} />);
    });
    await flushEffects();

    let enterButtons = Array.from(container.querySelectorAll('button')).filter((button) =>
      button.textContent?.includes('进入'),
    );
    expect(enterButtons).toHaveLength(1);

    act(() => {
      enterButtons[0]?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });
    await flushEffects();

    act(() => {
      const nextButtons = Array.from(container.querySelectorAll('button')).filter((button) =>
        button.textContent?.includes('进入'),
      );
      nextButtons[0]?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });
    await flushEffects();

    expect(browseProjectFiles).toHaveBeenNthCalledWith(
      1,
      'project-1',
      expect.objectContaining({ path: '', keyword: '' }),
    );
    expect(browseProjectFiles).toHaveBeenNthCalledWith(
      2,
      'project-1',
      expect.objectContaining({ path: 'a', keyword: '' }),
    );
    expect(browseProjectFiles).toHaveBeenNthCalledWith(
      3,
      'project-1',
      expect.objectContaining({ path: 'a/b', keyword: '' }),
    );
  });

  it('clears stale search keyword when entering a directory', async () => {
    debounceState.value = 'diag';
    browseProjectFiles.mockReset();
    browseProjectFiles
      .mockResolvedValueOnce({
        has_more: false,
        items: [{ kind: 'directory', path: 'a/b', size: 0 }],
        keyword: 'diag',
        last_synced_at: 1710000000,
        limit: 200,
        offset: 0,
        path: '',
        repository_signature: 'repo-signature-a',
        repository_spec: {
          branch_name: 'release/main',
          group: 'platform',
          manifest_xml: 'default.xml',
          repository_type: 'multi',
          repository_url: 'https://example.com/manifest.git',
        },
        total: 1,
      } as any)
      .mockResolvedValueOnce({
        has_more: false,
        items: [{ kind: 'file', path: 'a/b/file.txt', size: 4 }],
        keyword: '',
        last_synced_at: 1710000000,
        limit: 200,
        offset: 0,
        path: 'a/b',
        repository_signature: 'repo-signature-a',
        repository_spec: {
          branch_name: 'release/main',
          group: 'platform',
          manifest_xml: 'default.xml',
          repository_type: 'multi',
          repository_url: 'https://example.com/manifest.git',
        },
        total: 1,
      } as any);

    act(() => {
      root.render(<FileSelectionDialog {...baseProps} />);
    });
    await flushEffects();

    const enterButton = Array.from(container.querySelectorAll('button')).find((button) =>
      button.textContent?.includes('进入'),
    );
    act(() => {
      enterButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });
    await flushEffects();

    expect(browseProjectFiles).toHaveBeenLastCalledWith(
      'project-1',
      expect.objectContaining({ path: 'a/b', keyword: '' }),
    );
  });

  it('ignores stale request failures after switching directories quickly', async () => {
    let rejectFirst: ((reason?: unknown) => void) | undefined;
    let resolveSecond: ((value: unknown) => void) | undefined;
    const firstPromise = new Promise((_, reject) => {
      rejectFirst = reject;
    });
    const secondPromise = new Promise((resolve) => {
      resolveSecond = resolve;
    });

    browseProjectFiles.mockReset();
    browseProjectFiles
      .mockResolvedValueOnce({
        has_more: false,
        items: [{ kind: 'directory', path: 'a', size: 0 }],
        keyword: '',
        last_synced_at: 1710000000,
        limit: 200,
        offset: 0,
        path: '',
        repository_signature: 'repo-signature-a',
        repository_spec: {
          branch_name: 'release/main',
          group: 'platform',
          manifest_xml: 'default.xml',
          repository_type: 'multi',
          repository_url: 'https://example.com/manifest.git',
        },
        total: 1,
      } as any)
      .mockImplementationOnce(() => firstPromise as Promise<any>)
      .mockImplementationOnce(() => secondPromise as Promise<any>);

    act(() => {
      root.render(<FileSelectionDialog {...baseProps} />);
    });
    await flushEffects();

    const rootButton = Array.from(container.querySelectorAll('button')).find((button) =>
      button.textContent?.includes('进入'),
    );
    act(() => {
      rootButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });
    await flushEffects();

    act(() => {
      const backButton = Array.from(container.querySelectorAll('button')).find((button) =>
        button.textContent?.includes('返回上级'),
      );
      backButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });

    await act(async () => {
      rejectFirst?.(new Error('目标目录不存在'));
      resolveSecond?.({
        has_more: false,
        items: [{ kind: 'directory', path: 'a', size: 0 }],
        keyword: '',
        last_synced_at: 1710000000,
        limit: 200,
        offset: 0,
        path: '',
        repository_signature: 'repo-signature-a',
        repository_spec: {
          branch_name: 'release/main',
          group: 'platform',
          manifest_xml: 'default.xml',
          repository_type: 'multi',
          repository_url: 'https://example.com/manifest.git',
        },
        total: 1,
      });
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(toast.error).not.toHaveBeenCalled();
    expect(browseProjectFiles).toHaveBeenLastCalledWith(
      'project-1',
      expect.objectContaining({ path: '', keyword: '' }),
    );
  });

  it('shows unreadable symlinks but excludes them from selection', async () => {
    const onConfirm = vi.fn();
    browseProjectFiles.mockReset();
    browseProjectFiles.mockResolvedValue({
      has_more: false,
      items: [
        {
          kind: 'file',
          path: 'hwrdc',
          size: 12,
          selectable: true,
        },
        {
          kind: 'file',
          path: 'hwrdc-missing-link',
          size: 0,
          selectable: false,
          unavailable_reason: '符号链接目标不存在或不可访问',
        },
      ],
      keyword: '',
      last_synced_at: 1710000000,
      limit: 200,
      offset: 0,
      path: '',
      repository_signature: 'repo-signature-a',
      repository_spec: {
        branch_name: 'release/main',
        group: 'platform',
        manifest_xml: 'default.xml',
        repository_type: 'multi',
        repository_url: 'https://example.com/manifest.git',
      },
      total: 2,
    } as any);

    act(() => {
      root.render(<FileSelectionDialog {...baseProps} onConfirm={onConfirm} />);
    });
    await flushEffects();

    expect(container.textContent).toContain('hwrdc-missing-link');
    expect(container.textContent).toContain('符号链接目标不存在或不可访问');

    const selectVisibleButton = findButtonByText('选择当前页可见项');
    act(() => {
      selectVisibleButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });
    await flushEffects();

    const confirmButton = findButtonByText('确认选择');
    act(() => {
      confirmButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });

    expect(onConfirm).toHaveBeenCalledWith(
      expect.objectContaining({ selectedFiles: ['hwrdc'] }),
    );
  });
});
