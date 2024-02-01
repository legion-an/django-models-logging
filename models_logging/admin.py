from functools import update_wrapper

from django.apps import apps
from django.contrib import admin
from django.contrib import messages
from django.contrib.admin.filters import RelatedFieldListFilter
from django.contrib.admin.utils import unquote
from django.contrib.admin.views.main import ChangeList
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.db import connection
from django.db import transaction
from django.db.models.sql import Query
from django.shortcuts import get_object_or_404, render, redirect
from django.template.response import TemplateResponse
from django.urls import re_path
from django.urls import reverse
from django.utils.encoding import force_str
from django.utils.html import format_html
from django.utils.translation import gettext as _

from .models import Change, Revision
from .settings import CAN_DELETE_CHANGES, CAN_CHANGE_CHANGES, CAN_DELETE_REVISION, REVERT_IS_ALLOWED, \
    CHANGES_REVISION_LIMIT, ADDED


class ChangeListWithFastCount(ChangeList):
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        self.query: Query = qs.query
        qs.count = self.fast_count
        return qs

    def fast_count(self):
        if not (self.query.group_by or self.query.where or self.query.distinct):
            cursor = connection.cursor()
            cursor.execute(
                "SELECT reltuples FROM pg_class WHERE relname = %s",
                [self.query.model._meta.db_table]
            )
            return int(cursor.fetchone()[0])
        return self.query.get_count(using=self.queryset.db)


class FastObjectsCountAdminModel(admin.ModelAdmin):
    show_full_result_count = False

    def get_changelist(self, request):
        return ChangeListWithFastCount


class HistoryAdmin(admin.ModelAdmin):
    object_history_template = "models_logging/object_history.html"
    history_latest_first = False
    # If inline_models_history is '__all__' it will display changes for all models listed in `inlines`
    inline_models_history = '__all__'

    def history_view(self, request, object_id, extra_context=None):
        """Renders the history view."""
        # Check if user has change permissions for model
        if not self.has_change_permission(request):
            raise PermissionDenied
        object_id = unquote(object_id)  # Underscores in primary key get quoted to "_5F"

        assert isinstance(self.inline_models_history, (tuple, list)) or self.inline_models_history == '__all__'

        # First check if the user can see this history.
        model = self.model
        obj = self.get_object(request, object_id)
        if obj is None:
            return self._get_obj_does_not_exist_redirect(
                request, model._meta, object_id
            )

        if not self.has_view_or_change_permission(request, obj):
            raise PermissionDenied

        # Compile the context.
        changes_admin = False
        if Change in admin.site._registry:
            changes_admin = True

        if self.inline_models_history == '__all__':
            self.inline_models_history = self.inlines

        context = {
            **self.admin_site.each_context(request),
            "changes": self.get_changes_queryset(obj),
            'changes_admin': changes_admin,
            "title": _("Change history: %s") % obj,
            "subtitle": None,
            "opts": model._meta,
            "object": obj,
        }
        context.update(extra_context or {})
        return TemplateResponse(
            request,
            self.object_history_template,
            context,
        )

    def get_changes_queryset(self, obj):
        qs = Change.get_changes_by_obj(
            obj,
            related_models=self.get_related_objects_for_changes()
        )
        if self.history_latest_first:
            qs = qs.order_by('-date_created')
        return qs

    def get_related_objects_for_changes(self):
        return [
            m for m in self.model._meta.related_objects
            if m.related_model in [i.model for i in self.inline_models_history]
        ]


class ContentTypeFilterForChange(RelatedFieldListFilter):
    def field_choices(self, field, request, model_admin):
        models_logging_config = apps.get_app_config('models_logging')
        items = ContentType.objects.get_for_models(*models_logging_config.registered_models)
        return [(item.pk, str(item)) for item in items.values()]


class ChangeAdmin(FastObjectsCountAdminModel):
    list_display = ['__str__', 'content_type', 'get_comment', 'get_link_admin_object', 'user']
    list_filter = [('content_type', ContentTypeFilterForChange), 'date_created', 'action']
    change_form_template = 'models_logging/change_form.html'
    revert_form_template = 'models_logging/revert_changes_confirmation.html'
    search_fields = ['=object_id', '=id', '=revision__id']
    raw_id_fields = ['revision']
    list_select_related = ('user', 'content_type')

    def get_comment(self, obj):
        return '%s: %s' % (obj.action, obj.object_repr)

    def get_link_admin_object(self, obj):
        try:
            if obj.object_id and obj.content_type.model_class() in admin.site._registry:
                return format_html(
                    '<a href="%s">%s</a>' % (
                        reverse(
                            'admin:%s_%s_change' % (obj.content_type.app_label, obj.content_type.model),
                            args=[obj.object_id]
                        ),
                        obj.object_repr
                    )
                )
        except AttributeError:
            return None

    def has_add_permission(self, request, *args, **kwargs):
        return

    def has_delete_permission(self, request, obj=None):
        return CAN_DELETE_CHANGES(request, obj) if callable(CAN_DELETE_CHANGES) else CAN_DELETE_CHANGES

    def revert_is_allowed(self, request, obj):
        return REVERT_IS_ALLOWED(request, obj) if callable(REVERT_IS_ALLOWED) else REVERT_IS_ALLOWED

    def get_readonly_fields(self, request, obj=None):
        fields = [f.name for f in obj._meta.fields if f.name != 'revision']
        if CAN_CHANGE_CHANGES(request, obj) if callable(CAN_CHANGE_CHANGES) else CAN_CHANGE_CHANGES:
            return fields
        return fields + ['revision']

    def revert_view(self, request, object_id, extra_context=None):
        obj = get_object_or_404(Change, id=object_id)
        if not self.revert_is_allowed(request, obj):
            raise PermissionDenied

        if request.method == 'POST':
            if obj.action == ADDED:
                # if model is registered in django admin try redirect to delete page
                if obj.content_type.model_class() in admin.site._registry:
                    return redirect(reverse('admin:%s_%s_delete' %
                                            (obj.content_type.app_label, obj.content_type.model), args=[obj.object_id]))
            try:
                obj.revert()
                messages.success(request, 'Changes of %s was reverted' % obj.object_repr)
                return redirect(reverse('admin:models_logging_change_changelist'))
            except Exception as err:
                messages.warning(request, 'Error: %s' % err)

        context = {
            'object': obj,
            'opts': self.model._meta,
            'object_name': obj.object_repr,
            'changed_data': obj.changed_data,
        }
        context.update(extra_context or {})
        return render(request, self.revert_form_template, context)

    def get_urls(self):
        def wrap(view):
            def wrapper(*args, **kwargs):
                return self.admin_site.admin_view(view)(*args, **kwargs)
            wrapper.model_admin = self
            return update_wrapper(wrapper, view)

        urls = super(ChangeAdmin, self).get_urls()
        urls.insert(0, re_path(r'^(.+)/revert/$', wrap(self.revert_view), name='revert_changes'),)
        return urls


class ChangeInline(admin.TabularInline):
    model = Change
    fields = ['__str__', 'content_type', 'object_id', 'object_repr', 'action']
    readonly_fields = fields
    extra = 0

    def get_queryset(self, request):
        return super(ChangeInline, self).get_queryset(request).select_related('content_type')

    def has_add_permission(self, request, *args, **kwargs):
        return False

    def has_delete_permission(self, request, obj=None):
        return CAN_DELETE_CHANGES(request, obj) if callable(CAN_DELETE_CHANGES) else CAN_DELETE_CHANGES


class RevisionAdmin(FastObjectsCountAdminModel):
    inlines = [ChangeInline]
    list_display = ['__str__', 'comment', 'changes']
    list_filter = ['date_created']
    change_form_template = 'models_logging/change_form.html'
    revert_form_template = 'models_logging/revert_revision_confirmation.html'
    readonly_fields = ['comment']
    search_fields = ['=id', '=changes__id']

    def get_queryset(self, request):
        return super(RevisionAdmin, self).get_queryset(request).prefetch_related('change_set')

    def has_delete_permission(self, request, obj=None):
        return CAN_DELETE_REVISION(request, obj) if callable(CAN_DELETE_REVISION) else CAN_DELETE_REVISION

    def has_add_permission(self, request, *args, **kwargs):
        return

    def revert_is_allowed(self, request, obj):
        return REVERT_IS_ALLOWED(request, obj) if callable(REVERT_IS_ALLOWED) else REVERT_IS_ALLOWED

    def changes(self, obj):
        count = obj.change_set.count()
        if count > CHANGES_REVISION_LIMIT:
            return 'Changes count - %s' % count
        return format_html(', '.join('<a href="%s">%s</a>' % (i.get_admin_url(), i.id) for i in
                                     [ch for ch in obj.change_set.all()]))

    def get_inline_formsets(self, request, formsets, inline_instances, obj=None):
        for formset in formsets:
            if formset.queryset.count() > CHANGES_REVISION_LIMIT:
                formset.queryset = formset.queryset[:CHANGES_REVISION_LIMIT]
        return super(RevisionAdmin, self).get_inline_formsets(request, formsets, inline_instances, obj)

    def get_urls(self):
        def wrap(view):
            def wrapper(*args, **kwargs):
                return self.admin_site.admin_view(view)(*args, **kwargs)
            wrapper.model_admin = self
            return update_wrapper(wrapper, view)

        urls = super(RevisionAdmin, self).get_urls()
        urls.insert(0, re_path(r'^(.+)/revert/$', wrap(self.revert_view), name='revert_revision'),)
        return urls

    def revert_view(self, request, object_id, extra_context=None):
        obj = get_object_or_404(Revision, id=object_id)
        if not self.revert_is_allowed(request, obj):
            raise PermissionDenied

        if request.method == 'POST':
            try:
                with transaction.atomic():
                    obj.revert()
                    messages.success(request, 'Changes of %s was reverted' % force_str(obj))
                    return redirect(reverse('admin:models_logging_revision_changelist'))
            except Exception as err:
                messages.warning(request, 'Error: %s' % err)

        context = {
            'object': obj,
            'opts': self.model._meta,
            'object_name': force_str(obj),
            'changes': obj.change_set.all()[:CHANGES_REVISION_LIMIT],
            'limit': CHANGES_REVISION_LIMIT,
            'changes_count': obj.change_set.count(),
        }
        context.update(extra_context or {})
        return render(request, self.revert_form_template, context)


admin.site.register(Change, ChangeAdmin)
admin.site.register(Revision, RevisionAdmin)
