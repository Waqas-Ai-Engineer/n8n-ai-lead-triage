import json, pathlib, shutil, subprocess, textwrap
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
WF = json.loads((ROOT / "workflows" / "ai-lead-triage.json").read_text())


def test_structure_and_connections():
    names = {n["name"] for n in WF["nodes"]}
    assert len(names) == len(WF["nodes"]) == 11
    for src, conn in WF["connections"].items():
        assert src in names
        for branch in conn["main"]:
            for link in branch:
                assert link["node"] in names
    assert next(n for n in WF["nodes"] if n["type"].endswith("webhook"))["parameters"]["path"] == "lead-intake"


def test_no_hardcoded_secrets():
    blob = json.dumps(WF)
    assert "sk-" not in blob and "Bearer sk" not in blob
    assert "$env.OPENAI_API_KEY" in blob


def test_code_node_matches_source():
    code_node = next(n for n in WF["nodes"] if n["name"] == "Normalize & Score")
    assert code_node["parameters"]["jsCode"] == (ROOT / "scripts" / "triage_logic.js").read_text()


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
@pytest.mark.parametrize("fixture,tier", [("sample_lead.json", "HOT"), ("sample_spam.json", "SPAM")])
def test_scoring_logic(fixture, tier):
    payload = (ROOT / "examples" / fixture).read_text()
    js = textwrap.dedent(f"""
        const $input = {{ first: () => ({{ json: {{ body: {payload} }} }}) }};
        const run = () => {{ {(ROOT / 'scripts' / 'triage_logic.js').read_text()} }};
        console.log(JSON.stringify(run()[0].json));
    """)
    out = subprocess.run(["node", "-e", js], capture_output=True, text=True, check=True).stdout
    assert json.loads(out)["tier"] == tier
