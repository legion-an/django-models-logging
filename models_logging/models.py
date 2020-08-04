import json

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models, transaction
from django.utils.translation import ugettext_lazy as _
from six import python_2_unicode_compatible
from django.urls import reverse

from .settings import ADDED, CHANGED, DELETED, LOGGING_USER_MODEL


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

    ACTIONS = (
        (ADDED, _("Added")),
        (CHANGED, _("Changed")),
        (DELETED, _("Deleted"))
    )

    date_created = models.DateTimeField(_("Date created"), db_index=True, auto_now_add=True,
                                        help_text=_("The date and time this changes was."))
    user = models.ForeignKey(LOGGING_USER_MODEL, blank=True, null=True, on_delete=models.SET_NULL,
                             verbose_name=_("User"), help_text=_("The user who created this changes."))
    object_id = models.IntegerField(help_text=_("Primary key of the model under version control."))
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE,
                                     help_text="Content type of the model under version control.")
    object = GenericForeignKey(ct_field="content_type", fk_field="object_id")
    # TODO: db is not used yet
    db = models.CharField(max_length=191, help_text=_("The database the model under version control is stored in."))
    changed_data = models.TextField(blank=True, null=True, help_text=_("The old data of changed fields."))
    object_repr = models.TextField(help_text=_("A string representation of the object."))
    revision = models.ForeignKey(Revision, blank=True, null=True, verbose_name='to revision', on_delete=models.CASCADE)
    action = models.CharField(_("Action"), choices=ACTIONS, help_text=_('added|changed|deleted'), max_length=7)

    def __str__(self):
        return "Changes %s of %s <%s>" % (self.id, self.object_repr, self.date_created.strftime('%Y-%m-%d %H:%M:%S.%f'))

    @staticmethod
    def get_changes_by_obj(model, obj_id, related_objects='__all__'):
        """
        get changes of object by model and obj
        :param model: class of models.Model
        :param obj_id: pk
        :param related_objects: can be "__all__" or list of models, if __all__ take changes of related objects to model
        by default related_objects is OneToOne or ManyToOne relations, but
        expressions for ForeignKey and ManyToMany added if related_objects is some like this
         [m for m in self.model._meta.get_fields() if m.is_relation]
        :return: queryset of Changes
        """

        obj = model.objects.get(pk=obj_id)
        history_objects = [{'content_type_id': ContentType.objects.get_for_model(model).id, 'values': [obj_id]}]
        if related_objects == '__all__':
            related_objects = model._meta.related_objects
        for rel_model in related_objects:
            if isinstance(rel_model, models.OneToOneRel):
                try:
                    values = [getattr(obj, rel_model.get_accessor_name()).pk]
                except rel_model.related_model.DoesNotExist:
                    continue
            elif isinstance(rel_model, models.ManyToOneRel):
                values = getattr(obj, rel_model.get_accessor_name()).all().values_list('pk', flat=True)
            elif isinstance(rel_model, models.ForeignKey):
                values = [getattr(obj, rel_model.get_attname())]
            elif isinstance(rel_model, models.ManyToManyField):
                values = getattr(obj, rel_model.get_attname()).all().values_list('pk', flat=True)
            else:
                continue

            history_objects.append(
                {'content_type_id': ContentType.objects.get_for_model(rel_model.related_model).id,
                 'values': values}
            )
        qobj = models.Q()
        for v in history_objects:
            qobj.add(models.Q(content_type_id=v['content_type_id'], object_id__in=v['values']), models.Q.OR)
        return Change.objects.filter(qobj).select_related('user')

    def revert(self):
        with transaction.atomic():
            data = {data['field']: data['values'].get('old') for data in json.loads(self.changed_data)}
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

    def display_changed_data(self):
        return json.loads(self.changed_data)
