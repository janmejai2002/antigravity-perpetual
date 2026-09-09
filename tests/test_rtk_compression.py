"""
Tests for RtkCompressor token estimation and compression.
"""
from antigravity_perpetual.compression.rtk_proxy import RtkCompressor


def test_rtk_compression_native_regex():
    comp = RtkCompressor(rtk_path=None)  # Force native regex

    raw_noisy_output = """
    \x1b[31mError:\x1b[0m Failed test assertion
    index a1b2c3d..e4f5a6b 100644
    --- a/src/main.py
    +++ b/src/main.py
    @@ -10,4 +10,4 @@
    - def old(): pass
    + def new(): pass


    \x1b[32mPASSED\x1b[0m in 0.12s
    """

    res = comp.compress_command_output("git diff", raw_noisy_output)
    assert res.compressed_text is not None
    # ANSI escape codes must be stripped
    assert "\x1b[31m" not in res.compressed_text
    assert "\x1b[32m" not in res.compressed_text
    assert "index a1b2c3d" not in res.compressed_text
    assert res.compressed_tokens <= res.original_tokens
