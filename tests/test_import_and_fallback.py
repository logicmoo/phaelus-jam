
def test_import_and_fallback():
    import os
    os.environ["USE_LLM"] = "0"
    from phaelusjam.player import PlayerState
    from phaelusjam.composer import LLMComposer
    st = PlayerState()
    comp = LLMComposer(channel=0)
    evts = comp.suggest(st)
    assert isinstance(evts, list)
    assert len(evts) >= 1
