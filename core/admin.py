
from django.conf import settings
from django.contrib import admin
from django.contrib.auth.models import Group
from django.forms.fields import ChoiceField
from django.forms.models import ModelForm, ModelChoiceField
from nnmware.core.models import JComment, Doc, Pic, Tag, Action, Follow, Notice, Message, VisitorHit
from django.utils.translation import ugettext_lazy as _


class JCommentAdmin(admin.ModelAdmin):
    fieldsets = (
        (_('nnmware'), {'fields': [('parent', 'content_type', 'object_id')]}),
        (_('Content'), {'fields': [('comment', 'user', 'status')]}),
        (_('Meta'), {'fields': [('created_date', 'updated_date',
                                 'ip')]}),
        )
    list_display = ('user', 'created_date', 'content_type',
                    'parent', '__unicode__')
    list_filter = ('created_date',)
    date_hierarchy = 'created_date'
    search_fields = ('comment', 'user__username')

admin.site.register(JComment, JCommentAdmin)


class TreeAdmin(admin.ModelAdmin):
    list_display = ('name', '_parents_repr', 'status', 'rootnode')
    list_display_links = ("name",)
    list_filter = ("name",)
    ordering = ['parent__id', 'name']
    prepopulated_fields = {'slug': ('name',)}
    actions = None
    search_fields = ("name", )
    fieldsets = (
        (_("Main"), {"fields": [("name", "slug"), ("parent",
                    "login_required",)]}),
        (_("Description"), {"classes": ("collapse",),
                "fields": [("description",),("ordering", "rootnode"), ]}),
        )


class MetaDataAdmin(admin.ModelAdmin):
    """
     Admin class for subclasses of the abstract ``Displayable`` model.
     """
    prepopulated_fields = {'slug': ('title',)}
    list_display = ("title", "status", "admin_link")
    list_display_links = ("title",)
    list_editable = ("status",)
    list_filter = ("status",)
    search_fields = ("title", "content",)
    date_hierarchy = "created_date"
    fieldsets = (
        (_("Main"), {"fields": [("title", "slug", "status", "user"), ]}),
        (_("Description"), {"fields": [("description", "created_date",
                    "allow_comments"), ]}),
        )

    def save_form(self, request, form, change):
        """
          Set the object's owner as the logged in user.
          """
        obj = form.save(commit=False)
        if obj.user is None:
            obj.user = request.user
        return super(MetaDataAdmin, self).save_form(request, form, change)

    def queryset(self, request):
        """
          Filter the change list by currently logged in user if not a
          superuser.
          """
        qs = super(MetaDataAdmin, self).queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(user__id=request.user.id)


class DocAdmin(admin.ModelAdmin):
    """
     Admin class for Doc.
     """
#    readonly_fields = ('file',)
    fieldsets = (
        (_('nnmware'), {'fields': [('user', 'content_type', 'object_id')]}),
        (_('Doc'), {'fields': [('file', 'created_date', 'ordering')]}),
        (_('Meta'), {'fields': [('description', 'filetype')]}),
        )
    list_display = ("description", "file", "created_date", "user",
            "locked", "size", "admin_link")


class PicAdmin(admin.ModelAdmin):
 #   readonly_fields = ('pic',)
    fieldsets = (
        (_('nnmware'), {'fields': [('user', 'content_type', 'object_id')]}),
        (_('Pic'), {'fields': [('pic', 'created_date')]}),
        (_('Meta'), {'fields': [('description', 'source')]}),
        )
    list_display = ('user', 'created_date', 'content_type',
                    'pic', '__unicode__')
    list_filter = ('created_date',)
    date_hierarchy = 'created_date'
    search_fields = ('description', 'user__username')

class VisitorHitAdmin(admin.ModelAdmin):
    readonly_fields = ('user','date','ip_address','session_key','user_agent','referrer',
        'url','secure','hostname')
    fieldsets = (
        (_('Visitor hit'), {'fields': [('user', 'date','secure'),
            ('ip_address', 'session_key'),
            ('user_agent', 'referrer'),
            ('url','hostname'),
        ]}),
        )
    list_display = ('user', 'date', 'ip_address',
                    'user_agent','url','secure')
    list_filter = ('date','user')
    search_fields = ('user__username', 'user_agent')
    ordering = ('-date','user','ip_address')

class TagAdmin(admin.ModelAdmin):
    fieldsets = ((_('nnmware'), {'fields': [('name','slug')]}),)
    list_display = ('name','slug')

class ActionAdmin(admin.ModelAdmin):
    date_hierarchy = 'timestamp'
    list_display = ('user', 'verb', 'content_object','timestamp','ip','user_agent')
    list_filter = ('timestamp',)

class UnitAdmin(admin.ModelAdmin):
    list_display = ('name', )
    list_filter = ('name',)

class ColorAdmin(admin.ModelAdmin):
    list_display = ('name', )
    list_filter = ('name',)

class FollowAdmin(admin.ModelAdmin):
    list_display = ('__unicode__', 'user', 'actor')
    list_editable = ('user',)
    list_filter = ('user',)

class NoticeAdmin(admin.ModelAdmin):
    list_display = ('user', 'timestamp', 'verb', 'sender','ip','user_agent')
    list_filter = ('user',)

class MessageAdmin(admin.ModelAdmin):
    fieldsets = (
        (_('Main'), {
            'fields': (
                'sender',
                ('recipient', ),
                ),
            }),
        (_("Message"), {"classes": ("grp-collapse grp-closed",), "fields": [('subject',),('body',),
            ('parent_msg',)]}),
        (_("Date/Time"), {"classes": ("grp-collapse grp-closed",), "fields": [('sent_at', 'read_at', 'replied_at'),
            ('sender_deleted_at', 'recipient_deleted_at'),('ip','user_agent')]}),
        )
    list_display = ('__unicode__', 'sender', 'ip','recipient', 'sent_at', 'read_at')
    list_filter = ('sent_at', 'sender', 'recipient')
    search_fields = ('subject', 'body')

    def save_model(self, request, obj, form, change):
        """
        Saves the message for the recipient and looks in the form instance
        for other possible recipients. Prevents duplication by excludin the
        original recipient from the list of optional recipients.

        When changing an existing message and choosing optional recipients,
        the message is effectively resent to those users.
        """
        obj.save()

        if form.cleaned_data['group'] == 'all':
            # send to all users
            recipients = settings.AUTH_USER_MODEL.objects.exclude(pk=obj.recipient.pk)
        else:
            # send to a group of users
            recipients = []
            group = form.cleaned_data['group']
            if group:
                group = Group.objects.get(pk=group)
                recipients.extend(
                    list(group.user_set.exclude(pk=obj.recipient.pk)))
            # create messages for all found recipients
        for user in recipients:
            obj.pk = None
            obj.recipient = user
            obj.save()

admin.site.register(Message, MessageAdmin)
admin.site.register(Doc, DocAdmin)
admin.site.register(Pic, PicAdmin)
admin.site.register(Tag, TagAdmin)
admin.site.register(Action, ActionAdmin)
admin.site.register(Follow, FollowAdmin)
admin.site.register(Notice, NoticeAdmin)
admin.site.register(VisitorHit, VisitorHitAdmin)
