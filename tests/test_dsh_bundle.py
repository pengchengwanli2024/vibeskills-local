"""DeepSeek Harness bundle contract for this repository."""
import json
from pathlib import Path
import re
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
NODE = shutil.which('node')


def node_major():
    if NODE is None:
        return 0
    match = re.match(r'v(\d+)', subprocess.run([NODE, '--version'], capture_output=True, text=True).stdout)
    return int(match.group(1)) if match else 0


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads((ROOT / 'package.json').read_text(encoding='utf-8'))

    def test_versions_agree_across_hosts(self):
        others = {json.loads((ROOT / name).read_text(encoding='utf-8'))['version']
                  for name in ('plugin.json', '.codex-plugin/plugin.json')}
        self.assertEqual(others, {self.manifest['version']})

    def test_exports_files_patch_and_icon(self):
        for key, target in self.manifest['exports'].items():
            matches = list(ROOT.glob(target[2:])) if '*' in target else [ROOT / target]
            self.assertTrue(matches and all(path.is_file() for path in matches), key)
        for entry in self.manifest['files']:
            self.assertTrue(list(ROOT.glob(entry)), entry)
        patch = (ROOT / self.manifest['dsh']['bundle']['patch']).read_text(encoding='utf-8')
        self.assertIn('name: ' + self.manifest['name'] + '\n', patch)
        icon = ROOT / self.manifest['icon']
        self.assertEqual(icon.read_bytes()[:8], b'\x89PNG\r\n\x1a\n')
        self.assertLessEqual(icon.stat().st_size, 256 * 1024)
        self.assertNotIn('dependencies', self.manifest)
        self.assertNotIn('scripts', self.manifest)

    def test_adapter_adds_nothing_inside_the_runtime_source(self):
        # The managed-runtime resolver rejects unexpected files in skills/vibe.
        self.assertFalse((ROOT / 'skills' / 'vibe' / 'dsh').exists())
        self.assertFalse((ROOT / 'skills' / 'vibe' / 'package.json').exists())

    def test_locales(self):
        for locale in ('en', 'zh'):
            meta = json.loads((ROOT / 'locale' / (locale + '.json')).read_text(encoding='utf-8'))['meta']
            self.assertTrue(meta['title'])
            self.assertGreater(len(meta['description']), 40)


@unittest.skipUnless(node_major() >= 22, 'Node.js 22+ is required for the provider tests')
class ProviderTests(unittest.TestCase):
    def test_skill_is_listed_and_body_is_preserved(self):
        done = subprocess.run(
            [NODE, '--input-type=module', '-e',
             "import { createProvider } from './dsh/index.mjs';"
             "const p = await createProvider(); const list = await p.list();"
             "console.log(JSON.stringify({ list, skill: await p.get(list[0]) }))"],
            cwd=ROOT, capture_output=True, timeout=60)
        self.assertEqual(done.returncode, 0, done.stderr.decode(errors='replace'))
        result = json.loads(done.stdout.decode('utf-8'))
        self.assertEqual([item['name'] for item in result['list']], ['vibe'])
        self.assertIn('explicitly invokes', result['list'][0]['description'])
        source = (ROOT / 'skills' / 'vibe' / 'SKILL.md').read_text(encoding='utf-8')
        body = source.split('---\n', 2)[2]
        content = result['skill']['content']
        self.assertTrue(content.endswith(body))
        notes = content[:-len(body)]
        self.assertIn(str(ROOT / 'skills' / 'vibe'), notes)
        self.assertIn('pwsh', notes)
        self.assertNotIn('{{', notes)


if __name__ == '__main__':
    unittest.main()
