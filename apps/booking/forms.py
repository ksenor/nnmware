# -*- coding: utf-8 -*-

from django import forms
from django.conf import settings
from django.contrib.admin.widgets import AdminTimeWidget
from django.utils.translation import ugettext_lazy as _
from nnmware.apps.booking.models import Hotel, HotelOption, Room, PLACES_CHOICES, Booking
from nnmware.apps.booking.models import RequestAddHotel, PaymentMethod
from nnmware.apps.money.models import Bill
from nnmware.apps.userprofile.models import Profile
from nnmware.core.fields import ReCaptchaField
from nnmware.core.utils import convert_to_date


class CabinetInfoForm(forms.ModelForm):
    name = forms.CharField(widget=forms.TextInput(attrs={'size' : '25'}))
    description = forms.CharField(widget=forms.Textarea(attrs={'class' : 'wide','rows':'5'}),required=False)
    schema_transit = forms.CharField(widget=forms.Textarea(attrs={'class' : 'wide','rows':'5'}),required=False)

    class Meta:
        model = Hotel
        fields = ('name', 'description', 'schema_transit', 'option')
        widgets = {
            'typefood': forms.RadioSelect(attrs={'class' : 'uniform'}),
            }

class CabinetTermsForm(forms.ModelForm):
    booking_terms = forms.CharField(widget=forms.Textarea(attrs={'class' : 'wide','rows':'5'}),required=False)
    condition_cancellation = forms.CharField(widget=forms.Textarea(attrs={'class' : 'wide','rows':'5'}),required=False)
    paid_services = forms.CharField(widget=forms.Textarea(attrs={'class' : 'wide','rows':'5'}),required=False)
    time_on = forms.CharField(widget=AdminTimeWidget(),required=False)
    time_off = forms.CharField(widget=AdminTimeWidget(),required=False)

    class Meta:
        model = Hotel
        fields = ('booking_terms', 'payment_method','condition_cancellation',
            'paid_services','time_on','time_off')

class CabinetRoomForm(forms.ModelForm):
    name = forms.CharField(widget=forms.TextInput(attrs={'size' : '25'}))
    description = forms.CharField(required=False,widget=forms.Textarea(attrs={'class' : 'wide','rows':'5'}))

    class Meta:
        model = Room
        fields = ('name', 'description', 'option','typefood')
        widgets = {
            'typefood': forms.RadioSelect(attrs={'class' : 'uniform'}),
            }

class CabinetEditBillForm(forms.ModelForm):
    description = forms.CharField(widget=forms.Textarea(attrs={'class' : 'wide','rows':'5','cols':'40'}))

    class Meta:
        model = Bill
        fields = ('date_billed', 'status', 'description','amount','currency')

class RequestAddHotelForm(forms.ModelForm):
    city = forms.CharField(required=False, widget=forms.TextInput(attrs={'size' : '35'}))
    address = forms.CharField(required=False, widget=forms.TextInput(attrs={'size' : '35'}))
    name = forms.CharField(widget=forms.TextInput(attrs={'size' : '35'}))
    email = forms.CharField(required=False, widget=forms.TextInput(attrs={'size' : '35'}))
    phone = forms.CharField(required=False, widget=forms.TextInput(attrs={'size' : '35'}))
    fax = forms.CharField(required=False, widget=forms.TextInput(attrs={'size' : '35'}))
    contact_email = forms.CharField(required=False, widget=forms.TextInput(attrs={'size' : '35'}))
    website = forms.CharField(required=False, widget=forms.TextInput(attrs={'size' : '35'}))
    rooms_count = forms.CharField(required=False, widget=forms.TextInput(attrs={'size' : '35'}))

    class Meta:
        model = RequestAddHotel
        fields = ('city', 'address', 'name','email','phone','fax','contact_email',
                  'website','rooms_count','starcount')

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user')
        super(RequestAddHotelForm, self).__init__(*args, **kwargs)
        if not user.is_authenticated():
            self.fields['recaptcha'] = ReCaptchaField(error_messages = { 'required': _('This field is required'),
                                                                       'invalid' : _('Answer is wrong') })

class UserCabinetInfoForm(forms.ModelForm):
    password = forms.CharField(label=_(u'New Password'), max_length=30, required=False)

    class Meta:
        model = Profile
        fields = (
            'fullname', 'publicmail', 'password', 'subscribe')

    def __init__(self, *args, **kwargs):
        self.current_user = kwargs.pop('user')
        super(UserCabinetInfoForm, self).__init__(*args, **kwargs)

    def clean_password(self):
        password = self.cleaned_data["password"]
        if len(password.strip(' ')) > 0:
            if not self.current_user.check_password(password):
                self.current_user.set_password(password)
                self.current_user.save()
        return password

class BookingAddForm(forms.ModelForm):
    room_id = forms.CharField(max_length=30, required=False)
    settlement = forms.CharField(max_length=30, required=False)
    payment_method = forms.CharField(max_length=30, required=False)

    class Meta:
        model = Booking
        fields = (
            'from_date', 'to_date', 'first_name', 'middle_name','last_name', 'phone','email',
            'payment_method')

    def clean_payment_method(self):
        p_m = self.cleaned_data.get('payment_method')
        if p_m:
            payment_method = PaymentMethod.objects.get(pk=int(p_m))
            return payment_method
        raise forms.ValidationError(_("No valid payment method."))

class BookingStatusForm(forms.ModelForm):
    description = forms.CharField(widget=forms.Textarea(attrs={'class' : 'wide','rows':'5','cols':'40'}), required=False)

    class Meta:
        model = Booking
        fields = ('status','description')
