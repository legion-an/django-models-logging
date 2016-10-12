from django.contrib.contenttypes.models import ContentType
try:
    from django.contrib.contenttypes.fields import GenericForeignKey
except ImportError:  # Django < 1.9 pragma: no cover
    from django.contrib.contenttypes.generic import GenericForeignKey
from django.db import models
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import python_2_unicode_compatible
from django.core.serializers import deserialize
from django.core.urlresolvers import reverse

from models_logging.revisions import create_changes


class RevertError(Exception): pass


@python_2_unicode_compatible
class Revision(models.Model):
    """A group of related changes."""

    class Meta:
        verbose_name_plural = _('Revisions')
        verbose_name = _('Revision')
        ordering = ('-pk',)

    date_created = models.DateTimeField(_("date created"), db_index=True, auto_now_add=True,
                                        help_text=_("The date and time this revision was created."))
    comment = models.TextField(_("comment"), blank=True, null=True, help_text=_("A text comment on this revision."))

    def __str__(self):
        return 'Revision %s of <%s>' % (self.id, self.date_created.strftime('%Y-%m-%d %H:%M:%S.%f'))

    def get_absolute_url(self):
        return reverse('admin:models_logging_revision_change', args=[self.id])

    def revert(self):
        for i in self.changes_set.all():
            i.revert()


@python_2_unicode_compatible
class Changes(models.Model):
    class Meta:
        ordering = ("-pk",)
        verbose_name = _('Changes of object')
        verbose_name_plural = _('All changes')

    date_created = models.DateTimeField(_("Date created"), db_index=True, auto_now_add=True,
                                        help_text=_("The date and time this changes was."))
    user = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True, on_delete=models.SET_NULL,
                             verbose_name=_("User"), help_text=_("The user who created this changes."))
    comment = models.TextField(_("Comment"), help_text=_("A text comment on this changes."))
    object_id = models.CharField(max_length=191, help_text=_("Primary key of the model under version control."))
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE,
                                     help_text="Content type of the model under version control.")
    object = GenericForeignKey(ct_field="content_type", fk_field="object_id")
    db = models.CharField(max_length=191, help_text=_("The database the model under version control is stored in."))
    serialized_data = models.TextField(blank=True, null=True,
                                       help_text=_("The serialized form of this version of the model."))
    object_repr = models.TextField(help_text=_("A string representation of the object."))
    revision = models.ForeignKey(Revision, blank=True, null=True, verbose_name='to revision', on_delete=models.SET_NULL)
    action = models.CharField(_("Action"), help_text=_('added|changed|deleted'), max_length=7)

    def __str__(self):
        return "Changes %s of %s <%s>" % (self.id, self.object_repr, self.date_created.strftime('%Y-%m-%d %H:%M:%S.%f'))

    @staticmethod
    def get_changes_by_obj(model, obj_id):
        obj = model.objects.get(pk=obj_id)
        history_objects = {ContentType.objects.get_for_model(model).id: [obj_id]}
        for rel_model in model._meta.related_objects:
            if type(rel_model.field) == models.OneToOneField:
                try:
                    values = [getattr(obj, rel_model.get_accessor_name()).pk]
                except rel_model.related_model.DoesNotExist:
                    continue
            else:
                values = list(getattr(obj, rel_model.get_accessor_name()).all().values_list('pk', flat=True))
            key = ContentType.objects.get_for_model(rel_model.related_model).id
            history_objects.update({key: values})
        qobj = models.Q()
        for k, v in history_objects.items():
            qobj.add(models.Q(content_type_id=k, object_id__in=v), models.Q.OR)
        return Changes.objects.filter(qobj)

    def revert(self):
        if self.action == 'Added':
            self.object.delete()
        elif self.action == 'Deleted':
            obj = self.get_deleted_object()
            obj.save()
            create_changes(obj, 'default', 'Recover object', action='Added')
        else:
            self.object.save()

    def get_deleted_object(self):
        return next(deserialize('json', self.serialized_data)).object

    def get_absolute_url(self):
        return reverse('admin:models_logging_changes_change', args=[self.id])