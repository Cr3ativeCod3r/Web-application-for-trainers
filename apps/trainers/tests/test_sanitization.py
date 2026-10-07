import pytest

from apps.trainers.tests.factories import TrainerPostFactory
from core.html import sanitize_html


class TestSanitizeHtml:
    def test_strips_script_tags(self):
        assert '<script' not in sanitize_html('<p>Hi</p><script>alert(1)</script>')

    def test_strips_event_handlers(self):
        assert 'onerror' not in sanitize_html('<img src="x.png" onerror="alert(1)">')

    def test_strips_javascript_urls(self):
        assert 'javascript:' not in sanitize_html('<a href="javascript:alert(1)">x</a>')

    def test_blocks_data_urls_in_links(self):
        assert 'data:' not in sanitize_html('<a href="data:text/html,<script>alert(1)</script>">x</a>')

    def test_keeps_quill_formatting_and_pasted_images(self):
        html = (
            '<h2>Title</h2><p class="ql-align-center"><strong>bold</strong> <em>it</em></p>'
            '<img src="data:image/png;base64,AAAA">'
        )
        clean = sanitize_html(html)
        assert '<h2>Title</h2>' in clean
        assert 'class="ql-align-center"' in clean
        assert '<strong>bold</strong>' in clean
        assert 'src="data:image/png;base64,AAAA"' in clean

    def test_drops_non_quill_classes(self):
        assert 'evil' not in sanitize_html('<p class="evil ql-indent-1">x</p>')


@pytest.mark.django_db
def test_post_content_is_sanitized_on_save():
    post = TrainerPostFactory(content='<p>ok</p><script>alert(1)</script>')
    post.refresh_from_db()
    assert '<script' not in post.content
    assert '<p>ok</p>' in post.content


def test_post_form_rejects_oversized_content():
    from apps.trainers.forms import MAX_POST_CONTENT_BYTES, TrainerPostForm

    huge_image = '<p><img src="data:image/png;base64,' + 'A' * MAX_POST_CONTENT_BYTES + '"></p>'
    form = TrainerPostForm(data={'title': 'Post', 'content': huge_image})

    assert not form.is_valid()
    assert 'content' in form.errors


def test_post_form_accepts_regular_content():
    from apps.trainers.forms import TrainerPostForm

    form = TrainerPostForm(data={'title': 'Post', 'content': '<p>Trening siłowy</p>'})
    assert form.is_valid(), form.errors
