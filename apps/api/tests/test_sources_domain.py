from __future__ import annotations

from app.modules.sources.chunking import chunk_text
from app.modules.sources.classify import classify_source
from app.modules.sources.dedup import canonicalize_url, dedupe_candidates, dedupe_key
from app.modules.sources.extraction import extract_text
from app.modules.sources.ranking import (
    freshness_score,
    rank_candidates,
    relevance_score,
)
from app.modules.sources.schemas import SourceCandidate


class TestClassify:
    def test_arxiv_is_academic(self):
        st, auth = classify_source("https://arxiv.org/abs/2010.11929")
        assert st.value == "ACADEMIC_PAPER"
        assert auth >= 0.9

    def test_standards_body(self):
        st, _ = classify_source("https://www.rfc-editor.org/rfc/rfc9110")
        assert st.value == "STANDARDS_BODY"

    def test_government_tld(self):
        st, _ = classify_source("https://www.cdc.gov/measles/index.html")
        assert st.value == "GOVERNMENT"

    def test_university_material(self):
        st, _ = classify_source("https://ocw.mit.edu/courses/18-06/")
        assert st.value == "UNIVERSITY_MATERIAL"

    def test_wikipedia_is_reference_not_authority(self):
        st, auth = classify_source("https://en.wikipedia.org/wiki/Spectral_graph_theory")
        assert st.value == "REFERENCE_WORK"
        assert auth < 0.8

    def test_official_docs(self):
        st, auth = classify_source("https://docs.python.org/3/library/asyncio.html")
        assert st.value == "OFFICIAL_DOCUMENTATION"
        assert auth >= 0.9

    def test_reddit_is_forum(self):
        st, auth = classify_source("https://reddit.com/r/math/comments/abc/eigenvalues/")
        assert st.value == "FORUM"
        assert auth <= 0.25

    def test_random_blog_is_weak(self):
        _, auth = classify_source("https://some-random-site.net/post/123")
        assert auth < 0.6


class TestDedup:
    def test_doi_beats_url(self):
        assert dedupe_key("10.1000/x", None, None) == "doi:10.1000/x"

    def test_canonical_url_strips_tracking(self):
        a = "https://Example.com/page/?utm_source=x&id=1"
        b = "https://example.com/page?id=1"
        assert canonicalize_url(a) == canonicalize_url(b)

    def test_dedupe_keeps_first_per_key(self):
        c1 = SourceCandidate(title="A", url="https://example.com/p?utm_source=t")
        c2 = SourceCandidate(title="B", url="https://example.com/p")
        unique, dropped = dedupe_candidates([c1, c2])
        assert len(unique) == 1
        assert dropped == 1
        assert unique[0].title == "A"  # first occurrence wins

    def test_doi_dedup_across_urls(self):
        paper_mirror_1 = SourceCandidate(
            title="Attention", url="https://arxiv.org/abs/1706.03762", arxiv_id="1706.03762"
        )
        paper_mirror_2 = SourceCandidate(
            title="Attention (v2)", url="https://arxiv.org/abs/1706.03762v5", arxiv_id="1706.03762"
        )
        unique, dropped = dedupe_candidates([paper_mirror_1, paper_mirror_2])
        assert len(unique) == 1
        assert dropped == 1


class TestRanking:
    def test_authority_dominates_with_default_policy(self):
        query = "transformer architecture"
        academic = SourceCandidate(title="Attention is all you need: transformer architecture",
                                   url="https://arxiv.org/abs/x", authority=0.95)
        forum = SourceCandidate(title="transformer architecture help pls",
                                url="https://reddit.com/r/x", authority=0.25)
        ranked = rank_candidates([forum, academic], query)
        assert ranked[0][0] is academic

    def test_freshness_matters_for_cs_policy(self):
        from datetime import date, timedelta

        from app.modules.sources.ranking import POLICIES

        policy = POLICIES["computer science"]
        fresh = SourceCandidate(title="React docs guide", url="https://react.dev/learn",
                                published=date.today() - timedelta(days=30))
        stale = SourceCandidate(title="React docs guide", url="https://old-docs.example/react",
                                published=date.today() - timedelta(days=3650))
        fresh_ranked, fresh_factors = rank_candidates([fresh], "react docs", policy)[0]
        stale_ranked, stale_factors = rank_candidates([stale], "react docs", policy)[0]
        assert fresh_factors["total"] > stale_factors["total"]

    def test_math_policy_downweights_freshness(self):
        from app.modules.sources.ranking import POLICIES

        math_policy = POLICIES["mathematics"]
        assert math_policy.w_freshness < 0.05

    def test_relevance_lexical_overlap(self):
        candidate = SourceCandidate(title="Spectral graph theory lecture notes",
                                    url="https://x/y", snippet="eigenvalues of graph Laplacians")
        score = relevance_score(candidate, "spectral graph theory eigenvalues")
        assert score > 0.5

    def test_factor_breakdown_logged_for_every_candidate(self):
        candidate = SourceCandidate(title="t", url="https://x.y/a")
        ranked = rank_candidates([candidate], "query topic")
        factors = ranked[0][1]
        for key in ("authority", "relevance", "freshness", "primary", "total", "policy"):
            assert key in factors


class TestFreshness:
    def test_none_is_neutral(self):
        assert freshness_score(None) == 0.5

    def test_recent_beats_old(self):
        from datetime import date, timedelta
        recent = freshness_score(date.today() - timedelta(days=30))
        old = freshness_score(date.today() - timedelta(days=3000))
        assert recent > old


class TestChunking:
    def test_empty_text(self):
        assert chunk_text("") == []

    def test_long_text_produces_multiple_chunks(self):
        text = "\n\n".join(f"Paragraph {i} " + "word " * 80 for i in range(40))
        chunks = chunk_text(text)
        assert len(chunks) > 1
        assert all(len(c) <= 4000 for c in chunks)

    def test_no_chunk_below_min_length(self):
        chunks = chunk_text("tiny")
        assert chunks == []


class TestExtraction:
    def test_strips_script_and_style(self):
        html = "<html><head><style>body{}</style><script>var x=1;</script></head>" \
               "<body><p>Real content lives here.</p></body></html>"
        text = extract_text(html)
        assert "Real content lives here." in text
        assert "var x" not in text
        assert "body{}" not in text

    def test_prefers_article_root(self):
        html = '<body><nav>Menu items everywhere</nav>' \
               '<article><p>The actual article body with plenty of words to satisfy length checks.</p></article></body>'
        text = extract_text(html)
        assert "actual article body" in text
