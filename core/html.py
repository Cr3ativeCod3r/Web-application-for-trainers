"""HTML sanitization for user-generated rich text (e.g. Quill editor output)."""
import nh3

# Exactly what the Quill toolbar used in templates/trainers/post_form.html can produce.
ALLOWED_TAGS = {
    'p', 'br', 'h1', 'h2', 'h3', 'strong', 'em', 'u', 's',
    'blockquote', 'pre', 'ol', 'ul', 'li', 'a', 'img', 'span',
}
ALLOWED_ATTRIBUTES = {
    '*': {'class'},
    'a': {'href', 'target'},
    'img': {'src', 'alt'},
    'pre': {'spellcheck'},
}
ALLOWED_URL_SCHEMES = {'http', 'https', 'mailto', 'data'}


def _filter_attribute(element: str, attribute: str, value: str) -> str | None:
    # Quill only uses its own "ql-*" classes; anything else is dropped.
    if attribute == 'class':
        classes = [c for c in value.split() if c.startswith('ql-')]
        return ' '.join(classes) or None
    # data: URIs are needed for images pasted into the editor, but never for links.
    if attribute == 'href' and value.strip().lower().startswith('data:'):
        return None
    if attribute == 'src' and value.strip().lower().startswith('data:') and not value.strip().lower().startswith('data:image/'):
        return None
    return value


def sanitize_html(value: str) -> str:
    """Strip every tag, attribute and URL scheme that is not explicitly allowed."""
    if not value:
        return value
    return nh3.clean(
        value,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        url_schemes=ALLOWED_URL_SCHEMES,
        attribute_filter=_filter_attribute,
        link_rel='noopener noreferrer nofollow',
    )
