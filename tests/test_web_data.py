"""The dashboard must format original report metrics, not recompute from rounded MAEs."""
import json
from pathlib import Path
import subprocess
import sys


def test_web_pack_preserves_report_metric_precision(tmp_path):
    root = Path(__file__).resolve().parents[1]
    output = tmp_path / 'replay.json'
    subprocess.run([sys.executable, str(root / 'scripts/build_web_data.py'), '--out', str(output)], check=True)
    web = json.loads(output.read_text())
    metrics = json.loads((root / 'reports/test_metrics.json').read_text())
    frozen = json.loads((root / 'reports/frozen_selection.json').read_text())
    for lead, row in metrics['runs']['primary']['leads'].items():
        assert web['metrics'][lead]['n'] == row['n_paired']
        for model, expected in row['models'].items():
            assert web['metrics'][lead]['models'][model]['mae'] == expected['mae']
            assert web['metrics'][lead]['models'][model]['skill'] == expected['skill_vs_persistence']
    val = frozen['primary']['val_metrics']['3']['expanding_window_paired']
    for model in ['full', 'water_only', 'intercept_only', 'persistence']:
        assert web['validation']['mae'][model] == val[model]['mae']
