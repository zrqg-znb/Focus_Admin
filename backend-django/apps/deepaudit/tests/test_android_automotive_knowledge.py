from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from django.test import SimpleTestCase

from apps.deepaudit.agent_engine.knowledge import (
    knowledge_loader,
    resolve_module_alias,
    security_knowledge_rag,
)
from apps.deepaudit.agent_task.agent_runner import (
    _normalize_agent_input,
    _normalize_finding_payload,
)
from apps.deepaudit.rag.splitter import CodeSplitter


class AndroidAutomotiveKnowledgeTestCase(SimpleTestCase):
    databases = {"default"}

    def test_builtin_android_automotive_documents_are_registered(self) -> None:
        document_ids = {item['id'] for item in security_knowledge_rag.list_documents()}

        for expected_id in {
            'android_component_security',
            'android_binder_system_service_security',
            'android_ipc_binder_security',
            'android_intent_pendingintent_security',
            'android_webview_jsbridge_security',
            'android_storage_log_privacy',
            'android_jni_native_boundary',
            'android_hmi_display_state',
            'android_crypto_network_security',
            'android_privapp_platform_security',
            'android_vehicle_diagnostics_security',
            'android_ota_update_security',
            'android_vehicle_hal_car_service_security',
            'java_runtime_reflection_security',
            'java_parser_serialization_security',
        }:
            self.assertIn(expected_id, document_ids)

        self.assertEqual(resolve_module_alias('android'), 'android_component_security')
        self.assertEqual(resolve_module_alias('binder'), 'android_ipc_binder_security')
        self.assertEqual(resolve_module_alias('system_service'), 'android_binder_system_service_security')
        self.assertEqual(resolve_module_alias('pending_intent'), 'android_intent_pendingintent_security')
        self.assertEqual(resolve_module_alias('webview'), 'android_webview_jsbridge_security')
        self.assertEqual(resolve_module_alias('jni'), 'android_jni_native_boundary')
        self.assertEqual(resolve_module_alias('vehicle_display'), 'android_hmi_display_state')
        self.assertEqual(resolve_module_alias('privapp'), 'android_privapp_platform_security')
        self.assertEqual(resolve_module_alias('selinux'), 'android_privapp_platform_security')
        self.assertEqual(resolve_module_alias('uds'), 'android_vehicle_diagnostics_security')
        self.assertEqual(resolve_module_alias('ota'), 'android_ota_update_security')
        self.assertEqual(resolve_module_alias('vhal'), 'android_vehicle_hal_car_service_security')
        self.assertEqual(resolve_module_alias('reflection'), 'java_runtime_reflection_security')
        self.assertEqual(resolve_module_alias('java_deserialization'), 'java_parser_serialization_security')

    def test_knowledge_loader_accepts_android_aliases(self) -> None:
        validation = knowledge_loader.validate_modules(
            ['android', 'binder', 'system_service', 'pending_intent', 'webview', 'jni', 'hmi', 'android_crypto', 'privapp', 'uds', 'ota', 'vhal', 'reflection', 'java_deserialization']
        )

        self.assertEqual(validation['invalid'], [])
        self.assertTrue({
            'android_component_security',
            'android_ipc_binder_security',
            'android_binder_system_service_security',
            'android_intent_pendingintent_security',
            'android_webview_jsbridge_security',
            'android_jni_native_boundary',
            'android_hmi_display_state',
            'android_crypto_network_security',
            'android_privapp_platform_security',
            'android_vehicle_diagnostics_security',
            'android_ota_update_security',
            'android_vehicle_hal_car_service_security',
            'java_runtime_reflection_security',
            'java_parser_serialization_security',
        }.issubset(set(validation['valid'])))

        prompt = knowledge_loader.build_system_prompt_with_modules(
            'Base prompt',
            ['android', 'binder', 'system_service', 'pending_intent', 'webview', 'hmi', 'privapp', 'uds', 'ota', 'vhal', 'reflection', 'java_deserialization'],
        )
        self.assertIn('Android 组件暴露与权限边界', prompt)
        self.assertIn('Android Binder/IPC 身份校验', prompt)
        self.assertIn('Android Binder/SystemService 深度身份边界', prompt)
        self.assertIn('Android Intent/DeepLink/PendingIntent 暴露链路', prompt)
        self.assertIn('Android WebView/JSBridge 安全', prompt)
        self.assertIn('车机座舱/HMI 显示状态安全', prompt)
        self.assertIn('Android 特权应用/平台权限/SELinux 边界', prompt)
        self.assertIn('车载诊断/UDS/DoIP/CAN 网关安全', prompt)
        self.assertIn('Android/车机 OTA 升级与包完整性安全', prompt)
        self.assertIn('Android Vehicle HAL/CarService 属性边界', prompt)
        self.assertIn('Java 反射/ClassLoader/运行时执行边界', prompt)
        self.assertIn('Java 解析器/反序列化/XML 安全边界', prompt)

    def test_splitter_adds_android_java_semantic_metadata(self) -> None:
        splitter = CodeSplitter(use_tree_sitter=False)
        chunks = splitter.split_file(
            (
                'package com.car.hmi;\n'
                'import android.app.Activity;\n'
                'import android.webkit.WebView;\n'
                'import android.os.Binder;\n'
                'import android.util.Log;\n'
                'class ClusterActivity extends Activity {\n'
                '  native void renderFrame(byte[] frame);\n'
                '  void onCreate() {\n'
                '    WebView webView = new WebView(this);\n'
                '    webView.getSettings().setJavaScriptEnabled(true);\n'
                '    webView.addJavascriptInterface(this, "car");\n'
                '    int uid = Binder.getCallingUid();\n'
                '    checkCallingPermission("com.car.PRIV");\n'
                '    PendingIntent.getActivity(this, 1, getIntent(), PendingIntent.FLAG_MUTABLE);\n'
                '    Log.d("cluster", "speed=" + speed);\n'
                '    CarPropertyManager mgr = null;\n'
                '    mgr.setProperty(Integer.class, VehiclePropertyIds.HVAC_POWER_ON, 0, 1);\n'
                '    UpdateEngine engine = null;\n'
                '    engine.applyPayload(url, 0, 0, headers);\n'
                '    Class.forName(getIntent().getStringExtra("clazz"));\n'
                '    new ObjectInputStream(stream).readObject();\n'
                '    DocumentBuilderFactory.newInstance().newDocumentBuilder().parse(stream);\n'
                '    renderFrame(frame);\n'
                '  }\n'
                '}\n'
            ),
            'app/src/main/java/com/car/hmi/ClusterActivity.java',
            language='java',
        )

        self.assertTrue(chunks)
        merged_metadata: dict[str, list[str]] = {}
        for chunk in chunks:
            for key, value in chunk.metadata.items():
                if isinstance(value, list):
                    merged_metadata.setdefault(key, []).extend(value)

        self.assertTrue(merged_metadata.get('android_components'))
        self.assertTrue(merged_metadata.get('android_webview_usage'))
        self.assertTrue(merged_metadata.get('android_ipc_calls'))
        self.assertTrue(merged_metadata.get('android_permission_identity_checks'))
        self.assertTrue(merged_metadata.get('android_pending_intent_usage'))
        self.assertTrue(merged_metadata.get('android_jni_usage'))
        self.assertTrue(merged_metadata.get('android_storage_privacy_usage'))
        self.assertTrue(merged_metadata.get('android_ota_update_usage'))
        self.assertTrue(merged_metadata.get('android_vehicle_hal_usage'))
        self.assertTrue(merged_metadata.get('java_runtime_reflection_usage'))
        self.assertTrue(merged_metadata.get('java_parser_serialization_usage'))
        self.assertIn('android_hmi_display', merged_metadata.get('module_layers', []))

    def test_splitter_adds_android_config_semantic_metadata(self) -> None:
        splitter = CodeSplitter(use_tree_sitter=False)
        chunks = splitter.split_file(
            (
                '<network-security-config>\n'
                '  <base-config cleartextTrafficPermitted="true">\n'
                '    <trust-anchors><certificates src="user"/></trust-anchors>\n'
                '  </base-config>\n'
                '</network-security-config>\n'
            ),
            'app/src/main/res/xml/network_security_config.xml',
        )

        self.assertTrue(chunks)
        metadata = chunks[0].metadata
        self.assertIn('android_config', metadata.get('module_layers', []))
        self.assertTrue(metadata.get('android_network_security_config'))

        sepolicy_chunks = splitter.split_file(
            'allow untrusted_app vehicle_device:chr_file rw_file_perms;\n',
            'device/oem/sepolicy/vendor/vehicle.te',
        )
        self.assertTrue(sepolicy_chunks)
        sepolicy_metadata = sepolicy_chunks[0].metadata
        self.assertIn('android_platform_security', sepolicy_metadata.get('module_layers', []))
        self.assertTrue(sepolicy_metadata.get('android_selinux_policy'))
        self.assertTrue(sepolicy_metadata.get('android_vehicle_config'))

    def test_splitter_adds_android_manifest_semantic_metadata(self) -> None:
        splitter = CodeSplitter(use_tree_sitter=False)
        chunks = splitter.split_file(
            (
                '<manifest xmlns:android="http://schemas.android.com/apk/res/android">\n'
                '  <uses-permission android:name="android.permission.BLUETOOTH_CONNECT"/>\n'
                '  <application>\n'
                '    <activity android:name=".DiagActivity" android:exported="true" android:permission="com.car.SIGNATURE">\n'
                '      <intent-filter>\n'
                '        <action android:name="com.car.DIAG"/>\n'
                '        <category android:name="android.intent.category.DEFAULT"/>\n'
                '      </intent-filter>\n'
                '    </activity>\n'
                '    <provider android:name=".DiagProvider" android:authorities="com.car.diag" android:exported="false"/>\n'
                '  </application>\n'
                '</manifest>\n'
            ),
            'app/src/main/AndroidManifest.xml',
        )

        self.assertTrue(chunks)
        metadata = chunks[0].metadata
        self.assertIn('android_manifest', metadata.get('module_layers', []))
        self.assertIn('activity', metadata.get('android_manifest_components', []))
        self.assertIn('true', metadata.get('android_manifest_exported', []))
        self.assertIn('com.car.SIGNATURE', metadata.get('android_manifest_permissions', []))
        self.assertIn('com.car.diag', metadata.get('android_provider_authorities', []))

    def test_android_finding_without_evidence_is_downgraded(self) -> None:
        normalized = _normalize_finding_payload(
            {
                'title': 'Exported diagnostic Activity',
                'vulnerability_type': 'android_component_exposure',
                'severity': 'high',
                'file_path': 'app/src/main/AndroidManifest.xml',
                'verdict': 'confirmed',
                'confidence': 0.92,
                'rule_references': ['android_component_security'],
            }
        )

        assert normalized is not None
        self.assertFalse(normalized['is_verified'])
        self.assertEqual(normalized['poc']['verdict'], 'uncertain')
        self.assertLessEqual(normalized['ai_confidence'], 0.65)

    def test_java_dynamic_parser_finding_without_evidence_is_downgraded(self) -> None:
        normalized = _normalize_finding_payload(
            {
                'title': 'ObjectInputStream reachable from diagnostic file import',
                'vulnerability_type': 'java_deserialization',
                'severity': 'critical',
                'file_path': 'app/src/main/java/com/car/diag/ImportService.java',
                'verdict': 'confirmed',
                'confidence': 0.9,
                'rule_references': ['java_parser_serialization_security'],
            }
        )

        assert normalized is not None
        self.assertFalse(normalized['is_verified'])
        self.assertEqual(normalized['poc']['verdict'], 'uncertain')
        self.assertLessEqual(normalized['ai_confidence'], 0.65)

    def test_android_finding_with_evidence_is_preserved(self) -> None:
        normalized = _normalize_finding_payload(
            {
                'title': 'Exported diagnostic Activity lacks caller validation',
                'vulnerability_type': 'android_component_exposure',
                'severity': 'high',
                'file_path': 'app/src/main/AndroidManifest.xml',
                'verdict': 'confirmed',
                'confidence': 0.88,
                'rule_references': ['android_component_security'],
                'evidence_chain': ['DiagActivity exported=true', 'onCreate reads Intent extra', 'no permission/caller check', 'diagnostic mode opened'],
                'context_assumptions': ['release build', 'third-party app can send explicit intent'],
                'false_positive_checks': ['No signature permission found', 'No package allowlist found'],
                'confidence_reason': 'Manifest exposure and entrypoint chain are both present.',
            }
        )

        assert normalized is not None
        self.assertTrue(normalized['is_verified'])
        self.assertEqual(normalized['poc']['verdict'], 'confirmed')
        self.assertEqual(normalized['ai_confidence'], 0.88)

    def test_android_project_injects_default_knowledge_modules(self) -> None:
        workspace = Path(tempfile.mkdtemp(prefix='focusaudit-android-project-'))
        try:
            (workspace / 'app' / 'src' / 'main' / 'java' / 'com' / 'car' / 'hmi').mkdir(parents=True)
            (workspace / 'app' / 'src' / 'main').mkdir(parents=True, exist_ok=True)
            (workspace / 'app' / 'src' / 'main' / 'AndroidManifest.xml').write_text(
                '<manifest><application /></manifest>\n',
                encoding='utf-8',
            )
            (workspace / 'app' / 'src' / 'main' / 'java' / 'com' / 'car' / 'hmi' / 'ClusterActivity.java').write_text(
                'class ClusterActivity {}\n',
                encoding='utf-8',
            )

            normalized = _normalize_agent_input(
                'task-android',
                {
                    'project_name': 'Android Cockpit',
                    'audit_scope': {},
                    'agent_config': {},
                },
                str(workspace),
            )

            modules = set(normalized['config']['scenario_profile']['knowledge_modules'])
            self.assertIn('android_component_security', modules)
            self.assertIn('android_hmi_display_state', modules)
            self.assertIn('android_privapp_platform_security', modules)
            self.assertIn('android_vehicle_diagnostics_security', modules)
            self.assertIn('android_ota_update_security', modules)
            self.assertIn('android_vehicle_hal_car_service_security', modules)
            self.assertIn('java_runtime_reflection_security', modules)
            self.assertIn('java_parser_serialization_security', modules)
            self.assertTrue(normalized['config']['scenario_profile']['android_automotive'])
        finally:
            shutil.rmtree(workspace, ignore_errors=True)
