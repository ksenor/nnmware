# -*- coding: utf-8 -*-

"""
Base model library.
"""
from StringIO import StringIO
from datetime import datetime
import os
import Image
from django.contrib.contenttypes.generic import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import permalink, signals, Manager
from django.conf import settings
from django.core.urlresolvers import reverse
from django.core.files.base import ContentFile
from django.utils.translation import ugettext_lazy as _
from django.template.defaultfilters import slugify
from nnmware.core.abstract import MetaDate
from nnmware.core.managers import MetaLinkManager, JCommentManager, PublicJCommentManager, \
    FollowManager, MessageManager
from nnmware.core.imgutil import remove_thumbnails, remove_file
from nnmware.core.file import get_path_from_url
from nnmware.core.abstract import MetaLink, MetaFile
from nnmware.core.abstract import DOC_TYPE, DOC_FILE, MetaIP, STATUS_PUBLISHED, STATUS_CHOICES


class Tag(models.Model):
    """
    Model for Tags
    """
    name = models.CharField(_('Name'), max_length=40, unique=True, db_index=True)
    slug = models.SlugField(_("URL"), max_length=40, unique=True)
    follow = models.PositiveIntegerField(default=0, editable=False)


    class Meta:
        ordering = ('name',)
        verbose_name = _('Tag')
        verbose_name_plural = _('Tags')

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        super(Tag, self).save(*args, **kwargs)

    def lettercount(self):
        return Tag.objects.filter(name__startswith=self.name[0]).count()

    def __unicode__(self):
        return self.name

    def followers_count(self):
        ctype = ContentType.objects.get_for_model(self)
        return Follow.objects.filter(content_type=ctype,object_id=self.pk).count()

    def followers(self):
        ctype = ContentType.objects.get_for_model(self)
        users = Follow.objects.filter(content_type=ctype,object_id=self.pk).values_list('user',flat=True)
        return settings.AUTH_USER_MODEL.objects.filter(pk__in=users)

    @permalink
    def get_absolute_url(self):
        return "tag_detail", (), {'slug': self.slug}



class Doc(MetaLink, MetaFile):
    filetype = models.IntegerField(_("Doc type"), choices=DOC_TYPE, default=DOC_FILE)
    file = models.FileField(_("File"), upload_to="doc/%Y/%m/%d/", max_length=1024, blank=True)

    class Meta:
        ordering = ['ordering', ]
        verbose_name = _("Doc")
        verbose_name_plural = _("Docs")

    objects = MetaLinkManager()

    def save(self, *args, **kwargs):
        try:
            docs = Doc.objects.metalinks_for_object(self.content_object)
            if self.pk:
                docs = docs.exclude(pk=self.pk)
            if settings.DOC_MAX_PER_OBJECT > 1:
                if self.primary:
                    docs = docs.filter(primary=True)
                    docs.update(primary=False)
            else:
                docs.delete()
        except :
            pass
        fullpath = os.path.join(settings.MEDIA_ROOT, self.file.field.upload_to, self.file.path)
        self.size = os.path.getsize(fullpath)
        super(Doc, self).save(*args, **kwargs)

    @permalink
    def get_absolute_url(self):
        return os.path.join(settings.MEDIA_URL, self.file.url)

    def get_file_link(self):
        return os.path.join(settings.MEDIA_URL, self.file.url)

    def get_del_url(self):
        return reverse("doc_del", self.id)

    def get_edit_url(self):
        return reverse("doc_edit", self.id)


class Pic(MetaLink, MetaFile):
    pic = models.ImageField(verbose_name=_("Image"), max_length=1024, upload_to="pic/%Y/%m/%d/", blank=True)
    source = models.URLField(verbose_name=_("Source"), max_length=256, blank=True)

    objects = MetaLinkManager()

    class Meta:
        ordering = ['created_date', ]
        verbose_name = _("Pic")
        verbose_name_plural = _("Pics")

    def __unicode__(self):
        return _(u'Pic for %(type)s: %(obj)s') % {'type': unicode(self.content_type), 'obj': unicode(self.content_object)}

    def get_file_link(self):
        return os.path.join(settings.MEDIA_URL, self.pic.url)

    def save(self, *args, **kwargs):
        pics = Pic.objects.metalinks_for_object(self.content_object)
        if self.pk:
            pics = pics.exclude(pk=self.pk)
        if settings.PIC_MAX_PER_OBJECT > 1:
            if self.primary:
                pics = pics.filter(primary=True)
                pics.update(primary=False)
        else:
            pics.delete()
        try:
            remove_thumbnails(self.pic.path)
        except:
            pass
        fullpath = get_path_from_url(self.pic.url)
        self.size = os.path.getsize(fullpath)
        super(Pic, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        try:
            remove_thumbnails(self.pic.path)
            remove_file(self.pic.path)
        except:
            pass
        super(Pic, self).delete(*args, **kwargs)

    def create_thumbnail(self, size, quality=None):
        try:
            orig = self.pic.storage.open(self.pic.name, 'rb').read()
            image = Image.open(StringIO(orig))
        except IOError:
            return  # What should we do here?  Render a "sorry, didn't work" img?
        quality = quality or settings.PIC_THUMB_QUALITY
        (w, h) = image.size
        if w != size or h != size:
            if w > h:
                diff = (w - h) / 2
                image = image.crop((diff, 0, w - diff, h))
            else:
                diff = (h - w) / 2
                image = image.crop((0, diff, w, h - diff))
            if image.mode != "RGB":
                image = image.convert("RGB")
            image = image.resize((size, size), settings.PIC_RESIZE_METHOD)
            thumb = StringIO()
            image.save(thumb, settings.PIC_THUMB_FORMAT, quality=quality)
            thumb_file = ContentFile(thumb.getvalue())
        else:
            thumb_file = ContentFile(orig)
        thumb = self.pic.storage.save(self.pic_name(size), thumb_file)

    def get_del_url(self):
        return "pic_del", (), {'object_id': self.pk}
        #return reverse("pic_del", self.id)

    def get_edit_url(self):
        return reverse("pic_edit", self.pk)

    def get_view_url(self):
        return reverse("pic_view", self.pk)

    def get_editor_url(self):
        return reverse("pic_editor", self.pk)


class JComment(MetaLink, MetaIP, MetaDate):
    """
    A threaded comment which must be associated with an instance of
    ``django.contrib.auth.models.User``.  It is given its hierarchy by
    a nullable relationship back on itself named ``parent``.
    It also includes two Managers: ``objects``, which is the same as the normal
    ``objects`` Manager with a few added utility functions (see above), and
    ``public``, which has those same utility functions but limits the QuerySet to
    only those values which are designated as public (``is_public=True``).
    """
    # Hierarchy Field
    parent = models.ForeignKey('self', null=True, blank=True, default=None, related_name='children')
    # User Field
    user = models.ForeignKey(settings.AUTH_USER_MODEL)
    # Meat n' Potatoes
    comment = models.TextField(_('comment'))
    # Status Fields
    status = models.IntegerField(_("Status"), choices=STATUS_CHOICES, default=STATUS_PUBLISHED)

    objects = JCommentManager()
    public = PublicJCommentManager()

    def __unicode__(self):
        if len(self.comment) > 50:
            return self.comment[:50] + "..."
        return self.comment[:50]

    def save(self, **kwargs):
        self.updated_date = datetime.now()
        super(JComment, self).save(**kwargs)

    def get_base_data(self, show_dates=True):
        """
        Outputs a Python dictionary representing the most useful bits of
        information about this particular object instance.
        This is mostly useful for testing purposes, as the output from the
        serializer changes from run to run.  However, this may end up being
        useful for JSON and/or XML data exchange going forward and as the
        serializer system is changed.
        """
        to_return = {
            'content_object': self.content_object,
            'parent': self.parent,
            'user': self.user,
            'comment': self.comment,
            'status': self.status,
            'ip_address': self.ip_address,
            }
        if show_dates:
            to_return['created_date'] = self.created_date
            to_return['updated_date'] = self.updated_date
        return to_return

    class Meta:
        ordering = ('-created_date',)
        verbose_name = _("Threaded Comment")
        verbose_name_plural = _("Threaded Comments")
        get_latest_by = "created_date"


class Follow(models.Model):
    """
    Lets a user follow the activities of any specific actor
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL)

    content_type = models.ForeignKey(ContentType)
    object_id = models.CharField(max_length=255)
    actor = GenericForeignKey()

    objects = FollowManager()

    class Meta:
        unique_together = ('user', 'content_type', 'object_id')
        verbose_name = _("Follow")
        verbose_name_plural = _("Follows")

    def __unicode__(self):
        return u'%s -> %s' % (self.user, self.actor)

NOTICE_UNKNOWN = 0
NOTICE_SYSTEM = 1
NOTICE_VIDEO = 2
NOTICE_TAG = 3
NOTICE_ACCOUNT = 4
NOTICE_PROFILE = 5

NOTICE_CHOICES = (
    (NOTICE_UNKNOWN, _("Unknown")),
    (NOTICE_SYSTEM, _("System")),
    (NOTICE_VIDEO, _("Video")),
    (NOTICE_TAG, _("Tag")),
    (NOTICE_ACCOUNT, _("Account")),
    (NOTICE_PROFILE, _("Profile")),
    )


class Notice(MetaLink, MetaIP):
    """
    User notification model
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL)
    notice_type = models.IntegerField(_("Notice Type"), choices=NOTICE_CHOICES, default=NOTICE_UNKNOWN)
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='notice_sender')
    verb = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(default=datetime.now)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = _("Notice")
        verbose_name_plural = _("Notices")

class Message(MetaIP):
    """
    A private message from user to user
    """
    subject = models.CharField(_("Subject"), max_length=120, blank=True, null=True)
    body = models.TextField(_("Body"))
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='sent_messages', verbose_name=_("Sender"))
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='received_messages', null=True, blank=True, verbose_name=_("Recipient"))
    parent_msg = models.ForeignKey('self', related_name='next_messages', null=True, blank=True, verbose_name=_("Parent message"))
    sent_at = models.DateTimeField(_("sent at"), null=True, blank=True)
    read_at = models.DateTimeField(_("read at"), null=True, blank=True)
    replied_at = models.DateTimeField(_("replied at"), null=True, blank=True)
    sender_deleted_at = models.DateTimeField(_("Sender deleted at"), null=True, blank=True)
    recipient_deleted_at = models.DateTimeField(_("Recipient deleted at"), null=True, blank=True)
    objects = MessageManager()

    def new(self):
        """returns whether the recipient has read the message or not"""
        if self.read_at is not None:
            return False
        return True

    def replied(self):
        """returns whether the recipient has written a reply to this message"""
        if self.replied_at is not None:
            return True
        return False

    def __unicode__(self):
        if self.subject is not None:
            return self.subject
        if self.body is not None:
            return self.body[:40]
        return None

    def get_absolute_url(self):
        return 'messages_detail', [self.id]
    get_absolute_url = models.permalink(get_absolute_url)

    def save(self, **kwargs):
        if not self.id:
            self.sent_at = datetime.now()
        super(Message, self).save(**kwargs)

    class Meta:
        ordering = ['-sent_at']
        verbose_name = _("Message")
        verbose_name_plural = _("Messages")


ACTION_UNKNOWN = 0
ACTION_SYSTEM = 1
ACTION_ADDED = 2
ACTION_COMMENTED = 3
ACTION_FOLLOWED = 4
ACTION_LIKED = 5

ACTION_CHOICES = (
    (ACTION_UNKNOWN, _("Unknown")),
    (ACTION_SYSTEM, _("System")),
    (ACTION_ADDED, _("Added")),
    (ACTION_COMMENTED, _("Commented")),
    (ACTION_FOLLOWED, _("Followed")),
    (ACTION_LIKED, _("Liked")),
    )

class Action(MetaLink,MetaIP):
    """
    Model Activity of User
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='actions')
    action_type = models.IntegerField(_("Action Type"), choices=ACTION_CHOICES, default=ACTION_UNKNOWN)
    verb = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(default=datetime.now)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = _("Action")
        verbose_name_plural = _("Actions")

    @property
    def target_type(self):
        return ContentType.objects.get_for_model(self.content_object).model

    def __unicode__(self):
        return u'%s %s %s ago' % (self.user, self.verb, self.timesince())


    def timesince(self, now=None):
        """
        Shortcut for the ``django.utils.timesince.timesince`` function of the
        current timestamp.
        """
        from django.utils.timesince import timesince as timesince_
        return timesince_(self.timestamp, now)

    @models.permalink
    def get_absolute_url(self):
        return 'nnmware.core.views.detail', [self.pk]

def update_comment_count(sender, instance, **kwargs):
    what = instance.get_content_object()
    what.comments = JComment.public.all_for_object(what).count()
    what.updated_date = datetime.now()
    what.save()


def update_pic_count(sender, instance, **kwargs):
    what = instance.get_content_object()
    what.pics = Pic.objects.metalinks_for_object(what).count()
    what.save()


def update_doc_count(sender, instance, **kwargs):
    what = instance.get_content_object()
    what.docs = Doc.objects.metalinks_for_object(what).count()
    what.save()

signals.post_save.connect(update_comment_count, sender=JComment, dispatch_uid="nnmware_id")
signals.post_delete.connect(update_comment_count, sender=JComment, dispatch_uid="nnmware_id")
signals.post_save.connect(update_pic_count, sender=Pic, dispatch_uid="nnmware_id")
signals.post_delete.connect(update_pic_count, sender=Pic, dispatch_uid="nnmware_id")
signals.post_save.connect(update_doc_count, sender=Doc, dispatch_uid="nnmware_id")
signals.post_delete.connect(update_doc_count, sender=Doc, dispatch_uid="nnmware_id")

class VisitorHit(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('User'), blank=True, null=True)
    date = models.DateTimeField(verbose_name=_("Creation date"), default=datetime.now)
    session_key = models.CharField(max_length=40, verbose_name=_('Session key'))
    ip_address = models.CharField(max_length=20, verbose_name=_('IP'))
    hostname = models.CharField(max_length=100, verbose_name=_('Hostname'))
    user_agent = models.CharField(max_length=255, verbose_name=_('User-agent'))
    referrer = models.CharField(max_length=255, verbose_name=_('Referrer'))
    url = models.CharField(max_length=255, verbose_name=_('URL'))
    secure = models.BooleanField(_('Is secure'), default=False)

    class Meta:
        ordering = ['-date']
        verbose_name = _("Visitor hit")
        verbose_name_plural = _("Visitors hits")
