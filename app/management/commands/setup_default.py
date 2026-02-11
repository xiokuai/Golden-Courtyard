from django.core.management.base import BaseCommand
from app.models import User, Server, Channel, Membership


class Command(BaseCommand):
    help = '创建系统默认服务器、Bot 用户，并设置 wuli 和 Bot 为所有者'

    def handle(self, *args, **options):
        # 1. 创建 Bot 用户
        bot, created = User.objects.get_or_create(
            username='Bot',
            defaults={'is_active': True},
        )
        if created:
            bot.set_unusable_password()
            bot.save()
            self.stdout.write(self.style.SUCCESS('创建 Bot 用户'))
        else:
            self.stdout.write('Bot 用户已存在')

        # 2. 确保 wuli 存在
        try:
            wuli = User.objects.get(username='wuli')
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR('用户 wuli 不存在，请先注册'))
            return

        # 3. 创建系统服务器
        server, created = Server.objects.get_or_create(
            is_system=True,
            defaults={'name': 'Default', 'owner': bot},
        )
        if created:
            self.stdout.write(self.style.SUCCESS('创建 Default 系统服务器'))
        else:
            self.stdout.write('系统服务器已存在')

        # 4. 创建 Default 频道
        channel, _ = Channel.objects.get_or_create(
            server=server, name='Default',
        )

        # 5. 设置 Bot 和 wuli 为 owner
        Membership.objects.update_or_create(
            user=bot, server=server,
            defaults={'role': 'owner'},
        )
        Membership.objects.update_or_create(
            user=wuli, server=server,
            defaults={'role': 'owner'},
        )
        self.stdout.write(self.style.SUCCESS('Bot 和 wuli 已设为 owner'))

        # 6. 将所有现有用户加入系统服务器
        users = User.objects.exclude(
            id__in=Membership.objects.filter(server=server).values_list('user_id', flat=True)
        )
        for u in users:
            Membership.objects.create(user=u, server=server, role='member')
        if users.exists():
            self.stdout.write(self.style.SUCCESS(f'已将 {users.count()} 个用户加入系统服务器'))

        self.stdout.write(self.style.SUCCESS('完成'))
