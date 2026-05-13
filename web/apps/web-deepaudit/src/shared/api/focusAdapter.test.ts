import { describe, expect, it } from 'vitest';

import { mapApiPath } from './focusAdapter';

describe('mapApiPath', () => {
  it('maps scenarios requests to the DeepAudit backend prefix', () => {
    expect(mapApiPath('/scenarios?page=1&pageSize=200')).toBe(
      '/deepaudit/scenarios?page=1&pageSize=200',
    );
    expect(mapApiPath('/scenarios/abc')).toBe('/deepaudit/scenarios/abc');
    expect(mapApiPath('/scenarios/abc/copy')).toBe(
      '/deepaudit/scenarios/abc/copy',
    );
  });
});
