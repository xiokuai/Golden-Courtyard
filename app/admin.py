from django.contrib import admin
from .models import Server, Channel, Membership, Message, User, DirectMessage

admin.site.register(User)
admin.site.register(Server)
admin.site.register(Channel)
admin.site.register(Membership)
admin.site.register(Message)
admin.site.register(DirectMessage)
