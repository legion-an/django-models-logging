from functools import update_wrapper

from django.core.urlresolvers import reverse
from django.core.exceptions import PermissionDenied
from django.core.serializers import deserialize
from django.contrib import admin
from django.contrib.admin.utils import unquote
from django.contrib.admin.filters import RelatedOnlyFieldListFilter
from django.contrib import messages
from django.conf.urls import url
from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404, render, redirect
from django.forms.models import model_to_dict
from django.utils.html import format_html
from django.utils.encoding import force_text

from models_logging.models import Changes, Revision, NoPrevChangesError
from models_logging.revisions import create_revision


REVERT_IS_ALLOWED = getattr(settings, 'LOGGING_REVERT_IS_ALLOWED', True)
CAN_DELETE_REVISION = getattr(settings, 'LOGGING_CAN_DELETE_REVISION', False)
CAN_DELETE_CHANGES = getattr(settings, 'LOGGING_CAN_DELETE_CHANGES', False)
CAN_CHANGE_CHANGES = getattr(settings, 'LOGGING_CAN_CHANGE_CHANGES', False)
CHANGES_REVISION_LIMIT = getattr(settings, 'LOGGING_CHANGES_REVISION_LIMIT', 100)


class HistoryAdmin(admin.ModelAdmin):
    object_history_template = "models_logging/object_history.html"
    history_latest_first = False
    inline_models_history = '__all__'

    def __init__(self, *args, **kwargs):
        super(HistoryAdmin, self).__init__(*args, **kwargs)
        self._rev = None
        self._user = None

    def _reversion_order_version_queryset(self, queryset):
        """Applies the correct ordering to the given version queryset."""
        if not self.history_latest_first:
            queryset = queryset.order_by("pk")
        return queryset

    def save_model(self, request, obj, form, change):
        self._user = request.user
        self._rev = Revision.objects.create(comment='Changes in admin')
        with create_revision(self._rev, self._user):
            super(HistoryAdmin, self).save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        with create_revision(self._rev, self._user):
            super(HistoryAdmin, self).save_related(request, form, formsets, change)

    def delete_model(self, request, obj):
        with create_revision(None, request.user):
            super(HistoryAdmin, self).delete_model(request, obj)

    def history_view(self, request, object_id, extra_context=None):
        """Renders the history view."""
        # Check if user has change permissions for model
        if not self.has_change_permission(request):
            raise PermissionDenied
        object_id = unquote(object_id)  # Underscores in primary key get quoted to "_5F"

        # Compile the context.
        changes_admin = False
        if Changes in admin.site._registry:
            changes_admin = True

        if self.inline_models_history == '__all__':
            self.inline_models_history = self.inlines
        related_objects = [m for m in self.model._meta.related_objects
                           if m.related_model in [i.model for i in self.inline_models_history]]
        context = {"changes": Changes.get_changes_by_obj(self.model, object_id, related_objects=related_objects),
                   'changes_admin': changes_admin}
        context.update(extra_context or {})
        return super(HistoryAdmin, self).history_view(request, object_id, context)


class ChangesAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'content_type', 'get_comment', 'get_link_admin_object']
    list_filter = [('content_type', RelatedOnlyFieldListFilter), 'date_created', 'action']
    change_form_template = 'models_logging/change_form.html'
    revert_form_template = 'models_logging/revert_changes_confirmation.html'
    search_fields = ['=object_id', '=id', '=revision__id']

    def get_comment(self, obj):
        return '%s: %s' % (obj.action, obj.object_repr)

    def get_link_admin_object(self, obj):
        if obj.object and obj.content_type.model_class() in admin.site._registry:
            return format_html('<a href="%s">%s</a>' % (
                reverse('admin:%s_%s_change' % (obj.content_type.app_label, obj.content_type.model),
                        args=[obj.object_id]
                ),
                obj.object)
            )

    def has_add_permission(self, request):
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
        obj = get_object_or_404(Changes, id=object_id)
        if not self.revert_is_allowed(request, obj):
            raise PermissionDenied

        revert_obj = next(deserialize('json', obj.serialized_data)).object

        if request.method == 'POST':
            if obj.action == 'Added':
                # if model is registered in django admin try redirect to delete page
                if obj.content_type.model_class() in admin.site._registry:
                    return redirect(reverse('admin:%s_%s_delete' %
                                            (obj.content_type.app_label, obj.content_type.model), args=[obj.object_id]))
            try:
                obj.revert()
                messages.success(request, 'Changes of %s was reverted' % obj.object_repr)
                return redirect(reverse('admin:models_logging_changes_changelist'))
            except Exception as err:
                messages.warning(request, 'Error: %s' % err)

        context = {
            'object': obj,
            'opts': self.model._meta,
            'object_name': obj.object_repr,
            'revert_obj': model_to_dict(revert_obj),
        }
        context.update(extra_context or {})
        return render(request, self.revert_form_template, context)

    def get_urls(self):
        def wrap(view):
            def wrapper(*args, **kwargs):
                return self.admin_site.admin_view(view)(*args, **kwargs)
            wrapper.model_admin = self
            return update_wrapper(wrapper, view)

        urls = super(ChangesAdmin, self).get_urls()
        urls.insert(0, url(r'^(.+)/revert/$', wrap(self.revert_view), name='revert_changes'),)
        return urls


class ChangesInline(admin.TabularInline):
    model = Changes
    fields = ['__str__', 'content_type', 'object_id', 'object_repr', 'action']
    readonly_fields = fields
    extra = 0

    def get_queryset(self, request):
        return super(ChangesInline, self).get_queryset(request).select_related('content_type')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return CAN_DELETE_CHANGES(request, obj) if callable(CAN_DELETE_CHANGES) else CAN_DELETE_CHANGES


class RevisionAdmin(admin.ModelAdmin):
    inlines = [ChangesInline]
    list_display = ['__str__', 'comment', 'changes']
    list_filter = ['date_created']
    change_form_template = 'models_logging/change_form.html'
    revert_form_template = 'models_logging/revert_revision_confirmation.html'
    readonly_fields = ['comment']
    search_fields = ['=id', '=changes__id']

    def get_queryset(self, request):
        return super(RevisionAdmin, self).get_queryset(request)

    def has_delete_permission(self, request, obj=None):
        return CAN_DELETE_REVISION(request, obj) if callable(CAN_DELETE_REVISION) else CAN_DELETE_REVISION

    def has_add_permission(self, request):
        return

    def revert_is_allowed(self, request, obj):
        return REVERT_IS_ALLOWED(request, obj) if callable(REVERT_IS_ALLOWED) else REVERT_IS_ALLOWED

    def changes(self, obj):
        count = obj.changes_set.count()
        if count > CHANGES_REVISION_LIMIT:
            return 'Changes count - %s' % count
        return format_html(', '.join('<a href="%s">%s</a>' % (i.get_admin_url(), i.id) for i in
                                     [ch for ch in obj.changes_set.all()]))

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
        urls.insert(0, url(r'^(.+)/revert/$', wrap(self.revert_view), name='revert_revision'),)
        return urls

    def revert_view(self, request, object_id, extra_context=None):
        obj = get_object_or_404(Revision, id=object_id)
        if not self.revert_is_allowed(request, obj):
            raise PermissionDenied

        if request.method == 'POST':
            try:
                with transaction.atomic():
                    rev = Revision.objects.create(comment='Revert of revision %s' % obj)
                    with create_revision(rev):
                        obj.revert()
                    messages.success(request, 'Changes of %s was reverted' % force_text(obj))
                    return redirect(reverse('admin:models_logging_revision_changelist'))
            except Exception as err:
                messages.warning(request, 'Error: %s' % err)

        context = {
            'object': obj,
            'opts': self.model._meta,
            'object_name': force_text(obj),
            'changes': obj.changes_set.all()[:CHANGES_REVISION_LIMIT],
            'limit': CHANGES_REVISION_LIMIT,
            'changes_count': obj.changes_set.count(),
        }
        context.update(extra_context or {})
        return render(request, self.revert_form_template, context)

admin.site.register(Changes, ChangesAdmin)
admin.site.register(Revision, RevisionAdmin)