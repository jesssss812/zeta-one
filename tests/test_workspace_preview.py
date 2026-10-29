"""The public workspace only browses prepared deterministic engine records."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_preview_records_have_real_deterministic_provenance():
    state = json.loads((ROOT / "site/workspace/data.json").read_text())
    assert state["mode"] == "preview"
    assert state["recorded"]["synthetic"] is True
    assert state["recorded"]["simulated"] is True
    assert state["recorded"]["live_models"] is False
    assert len(state["payments"]) >= 3
    assert {p["recipe_id"] for p in state["payments"]} == {r["id"] for r in state["recipes"]}
    for payment in state["payments"]:
        assert payment["record"]["decision"] == payment["summary"]["decision"]
        assert payment["case_file"] is None
        assert payment["provenance"]


def test_preview_adapter_copies_records_and_refuses_review_actions():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is unavailable")
    script = r'''
import assert from 'node:assert/strict';
import fs from 'node:fs';
const source = JSON.parse(fs.readFileSync('site/workspace/data.json', 'utf8'));
let fetches = 0;
globalThis.fetch = async url => {
  assert.ok(String(url).endsWith('/data.json'));
  fetches++;
  return {ok:true, json: async () => structuredClone(source)};
};
const code = fs.readFileSync('site/workspace/preview.js', 'utf8').replace("new URL('./data.json', import.meta.url)", "'https://preview.invalid/data.json'");
const {createPreview} = await import(`data:text/javascript;base64,${Buffer.from(code).toString('base64')}`);
const adapter = await createPreview();
let state = await adapter.state();
assert.equal(state.payments.length, 3);
state.payments.length = 0;
assert.equal((await adapter.state()).payments.length, 3);
state = await adapter.act('add', {recipe_id:source.recipes[0].id});
assert.equal(state.payments.length, 4);
assert.notEqual(state.payments[0].id, source.payments[0].id);
assert.deepEqual(state.payments[0].record, source.payments[0].record);
assert.match(state.payments[0].provenance, /no new assessment/);
state = await adapter.act('random');
assert.equal(state.payments.length, 5);
assert.ok(source.payments.some(item => JSON.stringify(item.record) === JSON.stringify(state.payments[0].record)));
for (const action of ['assemble', 'outcome', 'resolve', 'repeat']) {
  await assert.rejects(adapter.act(action, {id:state.payments[0].id}), /local workspace/);
}
await assert.rejects(adapter.act('add', {recipe_id:'missing'}), /No prepared record/);
state = await adapter.act('reset');
assert.equal(state.payments.length, 3);
assert.equal(fetches, 1);
'''
    subprocess.run([node, "--input-type=module", "-e", script], cwd=ROOT, check=True)
