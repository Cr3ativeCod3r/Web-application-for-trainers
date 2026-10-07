from django.db import migrations

from core.html import sanitize_html


def sanitize_posts(apps, schema_editor):
    # Historical models do not run TrainerPost.save(), so sanitize explicitly.
    TrainerPost = apps.get_model('trainers', 'TrainerPost')
    for post in TrainerPost.objects.only('id', 'content').iterator():
        clean = sanitize_html(post.content)
        if clean != post.content:
            TrainerPost.objects.filter(pk=post.pk).update(content=clean)


class Migration(migrations.Migration):

    dependencies = [
        ('trainers', '0016_trainerprofile_tags_trainerprofileupdate_tags'),
    ]

    operations = [
        migrations.RunPython(sanitize_posts, migrations.RunPython.noop),
    ]
