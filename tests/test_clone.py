"""Clone 模块的单元测试（不依赖 LLM）。"""

from stemcell.modules.clone import PERSPECTIVES, CloneModule


def test_clone_basic():
    base = {"goal": "测试目标", "constraints": ["约束1"]}
    module = CloneModule()
    clones = module.run(base, perspectives=["conservative", "engineering"], count=2)
    assert len(clones) == 2
    assert clones[0]["perspective"] == "conservative"
    assert clones[1]["perspective"] == "engineering"
    assert clones[0]["base"] == base


def test_clone_count_more_than_perspectives():
    base = {"goal": "测试"}
    module = CloneModule()
    clones = module.run(base, perspectives=["conservative"], count=3)
    assert len(clones) == 3
    assert all(c["perspective"] == "conservative" for c in clones)


def test_clone_format_context():
    base = {
        "goal": "目标",
        "constraints": ["c1"],
        "key_facts": ["f1"],
        "preferences": ["p1"],
        "boundaries": ["b1"],
        "context_summary": "摘要",
    }
    clone = {
        "id": "clone_00",
        "perspective": "conservative",
        "perspective_label": "保守稳健",
        "perspective_prefix": "保守思考",
        "base": base,
    }
    text = CloneModule.format_clone_context(clone)
    assert "保守稳健" in text
    assert "目标" in text
    assert "c1" in text


def test_all_perspectives_have_required_keys():
    for meta in PERSPECTIVES.values():
        assert "label" in meta
        assert "prefix" in meta
