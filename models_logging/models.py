from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models, transaction
from django.db.models.functions import Cast
from django.urls import reverse
from django.utils.module_loading import import_string
from django.utils.translation import gettext_lazy as _
from six import python_2_unicode_compatible

from .settings import ADDED, CHANGED, DELETED, LOGGING_USER_MODEL, JSON_ENCODER_PATH


def get_encoder(*args, **kwargs):
    encoder_cls = import_string(JSON_ENCODER_PATH)
    return encoder_cls(*args, **kwargs)


@python_2_unicode_compatible
class Revision(models.Model):
    """A group of related changes."""

    class Meta:
        verbose_name_plural = _('Revisions')
        verbose_name = _('Revision')
        ordering = ('-pk',)

    date_created = models.DateTimeField(_("date created"), db_index=True, auto_now_add=True,
                                        help_text=_("The date and time this revision was created."))
    comment = models.TextField(_("comment"), blank=True, help_text=_("A text comment on this revision."))

    def __str__(self):
        return 'Revision %s of <%s>' % (self.id, self.date_created.strftime('%Y-%m-%d %H:%M:%S.%f'))

    def get_admin_url(self):
        return reverse('admin:models_logging_revision_change', args=[self.id])

    def revert(self):
        for ch in self.change_set.all():
            ch.revert()


@python_2_unicode_compatible
class Change(models.Model):
    class Meta:
        ordering = ("-pk",)
        verbose_name = _('Changes of object')
        verbose_name_plural = _('All changes')
        index_together = ('content_type', 'object_id')

    ACTIONS = (
        (ADDED, _("Added")),
        (CHANGED, _("Changed")),
        (DELETED, _("Deleted"))
    )

    date_created = models.DateTimeField(_("Date created"), db_index=True, auto_now_add=True,
                                        help_text=_("The date and time this changes was."))
    user = models.ForeignKey(LOGGING_USER_MODEL, blank=True, null=True, on_delete=models.SET_NULL,
                             verbose_name=_("User"), help_text=_("The user who created this changes."))
    object_id = models.TextField(
        help_text=_("Primary key of the model under version control."),
    )
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE,
                                     help_text="Content type of the model under version control.")
    object = GenericForeignKey(ct_field="content_type", fk_field="object_id")
    # TODO: db is not used yet
    db = models.CharField(max_length=191, help_text=_("The database the model under version control is stored in."))

    changed_data = models.JSONField(blank=True, null=True, encoder=get_encoder)

    object_repr = models.TextField(help_text=_("A string representation of the object."))
    revision = models.ForeignKey(Revision, blank=True, null=True, verbose_name='to revision', on_delete=models.CASCADE)
    action = models.CharField(_("Action"), choices=ACTIONS, help_text=_('added|changed|deleted'), max_length=7)
    extras = models.JSONField(blank=True, default=dict, encoder=get_encoder, null=True)

    def __str__(self):
        return "Changes %s of %s <%s>" % (self.id, self.object_repr, self.date_created.strftime('%Y-%m-%d %H:%M:%S.%f'))

    @staticmethod
    def get_changes_by_obj(obj, related_models):
        """
        get changes of object by model and obj
        :param obj: instance of tracked Model
        :param related_models: list of related models
        :return: queryset of Changes
        """

        base_qs = Change.objects.select_related("user")
        changes_qs = base_qs.filter(content_type=ContentType.objects.get_for_model(obj.__class__), object_id=obj.pk)
        for rel_model in related_models:
            if isinstance(rel_model, models.OneToOneRel):
                try:
                    changes_qs = changes_qs.union(
                        base_qs.filter(
                            content_type=ContentType.objects.get_for_model(rel_model.related_model),
                            object_id=getattr(obj, rel_model.get_accessor_name()).pk
                        )
                    )
                except rel_model.related_model.DoesNotExist:
                    continue
            elif isinstance(rel_model, models.ManyToOneRel):
                rel_objects_qs = getattr(obj, rel_model.get_accessor_name()).annotate(
                    pk_str=Cast('pk', output_field=models.TextField())
                ).values('pk_str')
                changes_qs = changes_qs.union(
                    base_qs.filter(
                        content_type=ContentType.objects.get_for_model(rel_model.related_model),
                        object_id__in=rel_objects_qs
                    )
                )

        return changes_qs.order_by('date_created')

    def revert(self):
        with transaction.atomic():
            data = {field: values.get('old') for field, values in self.changed_data.items()}
            if self.action == ADDED:
                self.object.delete()
            elif self.action == CHANGED:
                for k, v in data.items():
                    setattr(self.object, k, v)
                self.object.save()
            else:
                obj = self.changes_model_class()(**data)
                obj.save()

    def changes_model_class(self):
        return self.content_type.model_class()

    def get_admin_url(self):
        return reverse('admin:models_logging_change_change', args=[self.id])

    @classmethod
    def user_field_model(cls):
        return cls._meta.get_field('user').related_model
