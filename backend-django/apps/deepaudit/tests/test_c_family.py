from __future__ import annotations

from pathlib import Path
import tempfile

from django.test import SimpleTestCase

from apps.deepaudit.c_family import (
    CandidateUnit,
    build_candidate_context,
    collect_candidate_units,
    score_candidate_chunk,
)


class CFamilyCandidateTuningTestCase(SimpleTestCase):
    def test_collect_candidate_units_deprioritizes_repeated_portable_layers(self) -> None:
        files = [
            {
                'path': 'kernel/tasks.c',
                'content': (
                    '#include "task.h"\n'
                    '#include "FreeRTOS.h"\n'
                    'BaseType_t xTaskCreateChecked(TaskHandle_t pxTask) {\n'
                    '    taskENTER_CRITICAL();\n'
                    '    void *pv = pvPortMalloc(128);\n'
                    '    memcpy(pv, pxTask, 64);\n'
                    '    xTaskNotifyFromISR(pxTask, 0, eNoAction, NULL);\n'
                    '    vPortFree(pv);\n'
                    '    taskEXIT_CRITICAL();\n'
                    '    return pdPASS;\n'
                    '}\n'
                ),
            },
            {
                'path': 'kernel/queue.c',
                'content': (
                    '#include "queue.h"\n'
                    'BaseType_t xQueueSendChecked(QueueHandle_t xQueue, const void *pvItem) {\n'
                    '    taskENTER_CRITICAL();\n'
                    '    memcpy(pxQueueStorage, pvItem, sizeof(QueueItem_t));\n'
                    '    xQueueSendFromISR(xQueue, pvItem, NULL);\n'
                    '    taskEXIT_CRITICAL();\n'
                    '    return pdPASS;\n'
                    '}\n'
                ),
            },
            {
                'path': 'kernel/stream_buffer.c',
                'content': (
                    '#include "stream_buffer.h"\n'
                    'size_t xStreamBufferSendChecked(StreamBufferHandle_t xBuffer, const void *pvData, size_t xLength) {\n'
                    '    taskENTER_CRITICAL_FROM_ISR();\n'
                    '    memcpy(pxStorage + xHead, pvData, xLength);\n'
                    '    taskEXIT_CRITICAL_FROM_ISR(0);\n'
                    '    return xLength;\n'
                    '}\n'
                ),
            },
        ]
        for index in range(6):
            files.append(
                {
                    'path': f'portable/GCC/ARM_CM{index}/port.c',
                    'content': (
                        '#include "portmacro.h"\n'
                        'void vPortEnterCritical(void) {\n'
                        '    taskENTER_CRITICAL();\n'
                        '    vPortValidateInterruptPriority();\n'
                        '}\n'
                    ),
                }
            )
        for item in files:
            item['lines'] = item['content'].count('\n') + 1

        candidates = collect_candidate_units(files, analysis_depth='basic')

        self.assertTrue(any(candidate.file_path == 'kernel/tasks.c' for candidate in candidates))
        self.assertTrue(any(candidate.file_path == 'kernel/queue.c' for candidate in candidates))
        portable_candidates = [candidate for candidate in candidates if candidate.file_path.startswith('portable/')]
        self.assertLessEqual(len(portable_candidates), 2)
        self.assertGreaterEqual(
            sum(1 for candidate in candidates[:5] if not candidate.file_path.startswith('portable/')),
            3,
        )

    def test_build_candidate_context_uses_include_dependencies_and_nearest_build_hints(self) -> None:
        with tempfile.TemporaryDirectory(prefix='focusaudit-c-family-context-') as temp_dir:
            workspace = Path(temp_dir)
            (workspace / 'kernel').mkdir(parents=True, exist_ok=True)
            (workspace / 'include').mkdir(parents=True, exist_ok=True)
            (workspace / 'CMakeLists.txt').write_text(
                'project(freertos-kernel)\nadd_library(kernel STATIC kernel/tasks.c)\n',
                encoding='utf-8',
            )
            (workspace / 'kernel' / 'tasks.c').write_text(
                '#include "task.h"\n#include "FreeRTOS.h"\nBaseType_t xTaskCreateChecked(TaskHandle_t pxTask) { return pdPASS; }\n',
                encoding='utf-8',
            )
            (workspace / 'include' / 'task.h').write_text(
                'typedef struct tskTaskControlBlock * TaskHandle_t;\nBaseType_t xTaskCreateChecked(TaskHandle_t pxTask);\n',
                encoding='utf-8',
            )
            (workspace / 'include' / 'FreeRTOS.h').write_text(
                '#define pdPASS 1\n',
                encoding='utf-8',
            )

            file_lookup = {
                'kernel/tasks.c': {'content': (workspace / 'kernel' / 'tasks.c').read_text(encoding='utf-8')},
                'include/task.h': {'content': (workspace / 'include' / 'task.h').read_text(encoding='utf-8')},
                'include/FreeRTOS.h': {'content': (workspace / 'include' / 'FreeRTOS.h').read_text(encoding='utf-8')},
            }
            candidate = CandidateUnit(
                file_path='kernel/tasks.c',
                language='c',
                content='BaseType_t xTaskCreateChecked(TaskHandle_t pxTask) { return pdPASS; }',
                line_start=3,
                line_end=3,
                chunk_type='function',
                name='xTaskCreateChecked',
            )

            context, sources = build_candidate_context(
                workspace,
                candidate,
                all_candidates=[candidate],
                file_lookup=file_lookup,
                analysis_depth='standard',
            )

            self.assertIn('TaskHandle_t', context)
            self.assertIn('project(freertos-kernel)', context)
            self.assertIn('include_dependency:include/task.h', sources)

    def test_score_candidate_chunk_ignores_comment_only_noise(self) -> None:
        noisy_candidate = CandidateUnit(
            file_path='portable/GCC/ARM_CM4/port.c',
            language='c',
            content=(
                '/* taskENTER_CRITICAL interrupt pvPortMalloc xQueueSendFromISR */\n'
                '// ISR taskENTER_CRITICAL_FROM_ISR memcpy malloc free\n'
                'void vPortStub(void) { return; }\n'
            ),
            line_start=1,
            line_end=3,
            chunk_type='function',
            name='vPortStub',
        )
        real_candidate = CandidateUnit(
            file_path='kernel/stream_buffer.c',
            language='c',
            content=(
                'size_t xStreamBufferSendChecked(StreamBufferHandle_t xBuffer, const void *pvData, size_t xLength) {\n'
                '    taskENTER_CRITICAL_FROM_ISR();\n'
                '    memcpy(pxStorage + xHead, pvData, xLength);\n'
                '    taskEXIT_CRITICAL_FROM_ISR(0);\n'
                '    return xLength;\n'
                '}\n'
            ),
            line_start=1,
            line_end=6,
            chunk_type='function',
            name='xStreamBufferSendChecked',
        )

        noisy_score, _ = score_candidate_chunk(noisy_candidate, file_path=noisy_candidate.file_path, selected_paths=set())
        real_score, _ = score_candidate_chunk(real_candidate, file_path=real_candidate.file_path, selected_paths=set())

        self.assertGreater(real_score, noisy_score + 20)
