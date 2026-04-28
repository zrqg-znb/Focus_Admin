import { act, type ComponentProps } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import FileSelectionDialog from './FileSelectionDialog';
import { api } from '@/shared/config/database';

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

vi.mock('@/shared/config/database', () => ({
  api: {
    browseProjectFiles: vi.fn(),
  },
}));

vi.mock('@/shared/hooks', () => ({
  useDebounce: (value: unknown) => value,
}));

vi.mock('@/components/ui/dialog', () => ({
  Dialog: ({ children }: { children?: any }) => <div>{children}</div>,
  DialogContent: ({ children }: { children?: any }) => <div>{children}</div>,
  DialogFooter: ({ children }: { children?: any }) => <div>{children}</div>,
  DialogHeader: ({ children }: { children?: any }) => <div>{children}</div>,
  DialogTitle: ({ children }: { children?: any }) => <div>{children}</div>,
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
});
