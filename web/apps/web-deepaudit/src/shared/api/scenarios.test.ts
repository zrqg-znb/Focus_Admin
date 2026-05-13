import { beforeEach, describe, expect, it, vi } from 'vitest';

import {
  copyScenarioProfile,
  createScenarioProfile,
  deleteScenarioProfile,
  getScenarioProfiles,
  setDefaultScenarioProfile,
  updateScenarioProfile,
} from './scenarios';

const { getMock, postMock, putMock, deleteMock } = vi.hoisted(() => ({
  deleteMock: vi.fn(),
  getMock: vi.fn(),
  postMock: vi.fn(),
  putMock: vi.fn(),
}));

vi.mock('./serverClient', () => ({
  apiClient: {
    delete: deleteMock,
    get: getMock,
    post: postMock,
    put: putMock,
  },
}));

describe('scenarios api', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('uses the DeepAudit scenario prefix for list and mutation requests', async () => {
    getMock.mockResolvedValueOnce({ data: { items: [], total: 0 } });
    postMock.mockResolvedValue({ data: {} });
    putMock.mockResolvedValue({ data: {} });
    deleteMock.mockResolvedValue({});

    await getScenarioProfiles({ page: 1, pageSize: 200 });
    await createScenarioProfile({
      name: '测试场景',
      objective_type: 'audit',
      scenario_key: 'test-scenario',
    });
    await updateScenarioProfile('abc', { name: '更新后场景' });
    await copyScenarioProfile('abc', {});
    await deleteScenarioProfile('abc');
    await setDefaultScenarioProfile('abc');

    expect(getMock).toHaveBeenCalledWith('/deepaudit/scenarios', {
      params: { page: 1, pageSize: 200 },
    });
    expect(postMock).toHaveBeenNthCalledWith(
      1,
      '/deepaudit/scenarios',
      expect.objectContaining({
        scenario_key: 'test-scenario',
      }),
    );
    expect(putMock).toHaveBeenCalledWith('/deepaudit/scenarios/abc', {
      name: '更新后场景',
    });
    expect(postMock).toHaveBeenNthCalledWith(
      2,
      '/deepaudit/scenarios/abc/copy',
      {},
    );
    expect(deleteMock).toHaveBeenCalledWith('/deepaudit/scenarios/abc');
    expect(postMock).toHaveBeenNthCalledWith(
      3,
      '/deepaudit/scenarios/abc/set-default',
    );
  });
});
